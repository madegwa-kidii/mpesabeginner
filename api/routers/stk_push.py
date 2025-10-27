from fastapi import APIRouter, HTTPException, Request
from api.routers.websocket import broadcast_payment_status
import httpx
from api.models.stk_schemas import (
    STKPushRequest,
    STKPushResponse,
    STKPushCallback,
    SuccessResponse,
)
from api.services.auth_service import  AuthService
from api.core.config import settings
from api.core.utils import generate_password, get_timestamp, format_phone_number

router = APIRouter()


@router.post("/initiate", response_model=STKPushResponse)
async def initiate_stk_push(request: STKPushRequest):
    """
    Initiate STK Push (Lipa na M-Pesa Online)
    Sends payment prompt to customer's phone
    """
    try:
        # Get access token
        access_token = await AuthService.get_access_token()

        # Generate timestamp and password
        timestamp = get_timestamp()
        password = generate_password(
            settings.BUSINESS_SHORT_CODE,
            settings.PASSKEY,
            timestamp
        )

        # Format phone number
        phone_number = format_phone_number(request.phone_number)

        # Prepare request payload
        payload = {
            "BusinessShortCode": settings.BUSINESS_SHORT_CODE,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": request.amount,
            "PartyA": phone_number,
            "PartyB": settings.BUSINESS_SHORT_CODE,
            "PhoneNumber": phone_number,
            "CallBackURL": settings.STK_CALLBACK_URL,
            "AccountReference": request.account_reference,
            "TransactionDesc": request.transaction_desc
        }

        # Make API request
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.stk_push_url,
                json=payload,
                headers=headers,
                timeout=30.0
            )

            if response.status_code != 200:
                error_data = response.json() if response.text else {}
                raise HTTPException(
                    status_code=response.status_code,
                    detail={
                        "error_code": error_data.get("errorCode", "UNKNOWN"),
                        "error_message": error_data.get("errorMessage", response.text)
                    }
                )

            data = response.json()

            return STKPushResponse(
                merchant_request_id=data["MerchantRequestID"],
                checkout_request_id=data["CheckoutRequestID"],
                response_code=data["ResponseCode"],
                response_description=data["ResponseDescription"],
                customer_message=data["CustomerMessage"]
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error initiating STK push: {str(e)}"
        )


@router.post("/callback", response_model=SuccessResponse)
async def stk_push_callback(request: Request):
    """
    Callback endpoint for STK Push results
    M-Pesa sends transaction results here
    """
    try:
        # Get the callback data
        body = await request.json()

        # Extract callback details
        stk_callback = body.get("Body", {}).get("stkCallback", {})

        callback_data = STKPushCallback(
            merchant_request_id=stk_callback.get("MerchantRequestID"),
            checkout_request_id=stk_callback.get("CheckoutRequestID"),
            result_code=stk_callback.get("ResultCode"),
            result_desc=stk_callback.get("ResultDesc"),
            callback_metadata=stk_callback.get("CallbackMetadata")
        )

        # ✅ Broadcast the result to the frontend
        await broadcast_payment_status(callback_data.model_dump())

        # Process the callback based on result code
        if callback_data.result_code == 0:
            # Successful transaction
            # Here you would typically:
            # 1. Update your database
            # 2. Send confirmation to user
            # 3. Trigger any business logic

            print(f"✓ STK Push successful: {callback_data.checkout_request_id}")

            # Extract transaction details if available
            if callback_data.callback_metadata:
                items = callback_data.callback_metadata.get("Item", [])
                transaction_details = {item["Name"]: item.get("Value") for item in items}
                print(f"Transaction details: {transaction_details}")
        else:
            # Failed transaction
            print(f"✗ STK Push failed: {callback_data.result_desc}")

        # Return success response to M-Pesa
        return SuccessResponse(
            message="Callback received successfully",
            data=callback_data.model_dump()
        )

    except Exception as e:
        # Log error but return success to M-Pesa to avoid retries
        print(f"Error processing STK callback: {str(e)}")
        return SuccessResponse(
            message="Callback received",
            data={"error": str(e)}
        )

