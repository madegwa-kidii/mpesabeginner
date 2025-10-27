from fastapi import APIRouter, HTTPException, Request
from api.routers.websocket import broadcast_payment_status
import httpx
from api.models.b2c_schemas import (
    B2CPaymentRequest,
    B2CPaymentResponse,
    B2CCallback,
    SuccessResponse,
)
from api.services.auth_service import AuthService
from api.core.config import settings
from api.core.utils import format_phone_number
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
import base64

router = APIRouter()


def encrypt_initiator_password(password: str) -> str:
    """

    Args:
        password: Plain text initiator password

    Returns:
        Base64 encoded encrypted password
    """
    try:

        # Example implementation (uncomment when you have the certificate):
        with open('certificates/ProductionCertificate.cer', 'rb') as cert_file:
            cert_data = cert_file.read()
            public_key = RSA.importKey(cert_data)
            cipher = PKCS1_v1_5.new(public_key)
            encrypted = cipher.encrypt(password.encode())
            return base64.b64encode(encrypted).decode()



    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error encrypting password: {str(e)}"
        )


@router.post("/payment", response_model=B2CPaymentResponse)
async def initiate_b2c_payment(request: B2CPaymentRequest):
    """
    Initiate B2C Payment (Business to Customer)

    This endpoint sends money from your business to a customer's M-Pesa account.
    Use cases:
    - Salary payments
    - Cashback/refunds
    - Promotional payments
    - Winnings/prizes
    - Loan disbursements

    CommandID options:
    - SalaryPayment: Supports both registered and unregistered customers
    - BusinessPayment: Normal business payment (registered customers only)
    - PromotionPayment: Promotional payment with congratulatory message (registered only)
    """
    try:
        # Get access token
        access_token = await AuthService.get_access_token()

        # Format phone number
        phone_number = format_phone_number(request.phone_number)

        # Encrypt initiator password
        security_credential = encrypt_initiator_password(settings.INITIATOR_PASSWORD)

        # Prepare request payload
        payload = {
            "OriginatorConversationID": request.originator_conversation_id,
            "InitiatorName": settings.INITIATOR_NAME,
            "SecurityCredential": security_credential,
            "CommandID": request.command_id,
            "Amount": request.amount,
            "PartyA": settings.BUSINESS_SHORT_CODE,
            "PartyB": phone_number,
            "Remarks": request.remarks,
            "QueueTimeOutURL": settings.B2C_TIMEOUT_URL,
            "ResultURL": settings.B2C_RESULT_URL,
            "Occasion": request.occasion or ""
        }

        # Make API request
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.BASE_URL}/mpesa/b2c/v3/paymentrequest",
                json=payload,
                headers=headers,
                timeout=settings.API_TIMEOUT
            )

            if response.status_code != 200:
                error_data = response.json() if response.text else {}
                raise HTTPException(
                    status_code=response.status_code,
                    detail={
                        "error": "B2C payment request failed",
                        "error_code": error_data.get("errorCode", "UNKNOWN"),
                        "error_message": error_data.get("errorMessage", response.text),
                        "request_id": error_data.get("requestId")
                    }
                )

            data = response.json()

            return B2CPaymentResponse(
                conversation_id=data.get("ConversationID"),
                originator_conversation_id=data.get("OriginatorConversationID"),
                response_code=data.get("ResponseCode"),
                response_description=data.get("ResponseDescription")
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error initiating B2C payment: {str(e)}"
        )


@router.post("/result", response_model=SuccessResponse)
async def b2c_result_callback(request: Request):
    """
    Result callback endpoint for B2C payments.
    M-Pesa sends transaction results here after processing.
    """
    try:
        # Get the callback data
        body = await request.json()

        # Extract result details
        result = body.get("Result", {})

        callback_data = B2CCallback(
            conversation_id=result.get("ConversationID"),
            originator_conversation_id=result.get("OriginatorConversationID"),
            transaction_id=result.get("TransactionID"),
            result_code=result.get("ResultCode"),
            result_desc=result.get("ResultDesc"),
            result_type=result.get("ResultType"),
            result_parameters=result.get("ResultParameters"),
            reference_data=result.get("ReferenceData")
        )

        # Broadcast the result to frontend via WebSocket
        await broadcast_payment_status({
            "type": "b2c_result",
            "data": callback_data.model_dump()
        })

        # Process based on result code
        if callback_data.result_code == 0:
            # Successful transaction
            print(f"✓ B2C Payment successful: {callback_data.transaction_id}")

            # Extract transaction details
            if callback_data.result_parameters:
                items = callback_data.result_parameters.get("ResultParameter", [])
                transaction_details = {item["Key"]: item.get("Value") for item in items}

                print(f"Transaction Details:")
                print(f"  - Amount: {transaction_details.get('TransactionAmount')}")
                print(f"  - Receipt: {transaction_details.get('TransactionReceipt')}")
                print(f"  - Recipient: {transaction_details.get('ReceiverPartyPublicName')}")
                print(f"  - Completed: {transaction_details.get('TransactionCompletedDateTime')}")
                print(f"  - Working Account Balance: {transaction_details.get('B2CWorkingAccountAvailableFunds')}")

                # Here you would typically:
                # 1. Update your database with transaction details
                # 2. Send confirmation notification to customer
                # 3. Update accounting records
                # 4. Trigger any post-payment business logic

        else:
            # Failed transaction
            print(f"✗ B2C Payment failed: {callback_data.result_desc}")
            print(f"  Result Code: {callback_data.result_code}")

            # Handle specific error codes
            if callback_data.result_code == 2001:
                print("  Error: Invalid initiator information")

            # Log to database or monitoring system

        # Return success to M-Pesa
        return SuccessResponse(
            message="Result callback received successfully",
            data=callback_data.model_dump()
        )

    except Exception as e:
        # Log error but return success to M-Pesa to avoid retries
        print(f"Error processing B2C result callback: {str(e)}")
        return SuccessResponse(
            message="Callback received",
            data={"error": str(e)}
        )


@router.post("/timeout", response_model=SuccessResponse)
async def b2c_timeout_callback(request: Request):
    """
    Timeout callback endpoint for B2C payments.
    M-Pesa sends notification here if payment request times out in queue.
    """
    try:
        # Get the callback data
        body = await request.json()

        print(f"⚠ B2C Payment timeout received")
        print(f"Timeout data: {body}")

        # Broadcast timeout to frontend
        await broadcast_payment_status({
            "type": "b2c_timeout",
            "data": body
        })

        # Handle timeout scenario
        # 1. Update database status
        # 2. Notify user
        # 3. Consider retry logic

        return SuccessResponse(
            message="Timeout callback received successfully",
            data=body
        )

    except Exception as e:
        print(f"Error processing B2C timeout callback: {str(e)}")
        return SuccessResponse(
            message="Callback received",
            data={"error": str(e)}
        )
