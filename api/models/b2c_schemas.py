from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
from datetime import datetime
import uuid


# ==================== B2C Schemas ====================

class B2CPaymentRequest(BaseModel):
    """Request model for B2C payment initiation"""

    phone_number: str = Field(
        ...,
        description="Customer phone number (format: 254XXXXXXXXX or 07XXXXXXXX)",
        example="254708374149"
    )

    amount: int = Field(
        ...,
        gt=0,
        description="Amount to send to customer",
        example=1000
    )

    command_id: Literal["SalaryPayment", "BusinessPayment", "PromotionPayment"] = Field(
        default="BusinessPayment",
        description="""
        Transaction type:
        - SalaryPayment: Supports registered and unregistered customers
        - BusinessPayment: Normal payment (registered customers only)
        - PromotionPayment: Promotional payment with congratulatory message (registered only)
        """
    )

    remarks: str = Field(
        default="Payment",
        max_length=100,
        description="Additional information for the transaction",
        example="Salary payment for January 2024"
    )

    occasion: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Additional information for the transaction",
        example="Monthly Salary"
    )

    originator_conversation_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for the request"
    )

    @field_validator('phone_number')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Validate phone number format"""
        # Remove any spaces or special characters
        v = v.strip().replace(" ", "").replace("-", "").replace("+", "")

        # Convert 07XXXXXXXX to 254XXXXXXXXX
        if v.startswith("0"):
            v = "254" + v[1:]

        # Ensure it starts with 254
        if not v.startswith("254"):
            raise ValueError("Phone number must start with 254 or 0")

        # Validate length (254 + 9 digits = 12 total)
        if len(v) != 12:
            raise ValueError("Invalid phone number length")

        return v

    class Config:
        json_schema_extra = {
            "example": {
                "phone_number": "254708374149",
                "amount": 1000,
                "command_id": "BusinessPayment",
                "remarks": "Payment for services rendered",
                "occasion": "Service Payment"
            }
        }


class B2CPaymentResponse(BaseModel):
    """Response model for B2C payment initiation"""

    conversation_id: str = Field(
        ...,
        description="Unique identifier from M-Pesa for the transaction request"
    )

    originator_conversation_id: str = Field(
        ...,
        description="Unique identifier from the API request"
    )

    response_code: str = Field(
        ...,
        description="Response code (0 means successful submission)"
    )

    response_description: str = Field(
        ...,
        description="Response description message"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "conversation_id": "AG_20191219_00005797af5d7d75f652",
                "originator_conversation_id": "16740-34861180-1",
                "response_code": "0",
                "response_description": "Accept the service request successfully."
            }
        }


class B2CCallback(BaseModel):
    """Model for B2C payment result callback"""

    conversation_id: Optional[str] = Field(
        None,
        description="M-Pesa unique identifier for the transaction"
    )

    originator_conversation_id: Optional[str] = Field(
        None,
        description="Original unique identifier from the request"
    )

    transaction_id: Optional[str] = Field(
        None,
        description="M-Pesa transaction ID (e.g., NLJ41HAY6Q)"
    )

    result_code: int = Field(
        ...,
        description="Result code (0 = success, other = failure)"
    )

    result_desc: str = Field(
        ...,
        description="Result description message"
    )

    result_type: int = Field(
        default=0,
        description="Result type indicator"
    )

    result_parameters: Optional[dict] = Field(
        None,
        description="Additional transaction details for successful transactions"
    )

    reference_data: Optional[dict] = Field(
        None,
        description="Reference data from the transaction"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "conversation_id": "AG_20191219_00004e48cf7e3533f581",
                "originator_conversation_id": "10571-7910404-1",
                "transaction_id": "NLJ41HAY6Q",
                "result_code": 0,
                "result_desc": "The service request is processed successfully.",
                "result_type": 0,
                "result_parameters": {
                    "ResultParameter": [
                        {"Key": "TransactionAmount", "Value": 10},
                        {"Key": "TransactionReceipt", "Value": "NLJ41HAY6Q"},
                        {"Key": "B2CRecipientIsRegisteredCustomer", "Value": "Y"}
                    ]
                }
            }
        }


class B2CTransactionDetails(BaseModel):
    """Parsed transaction details from successful B2C payment"""

    transaction_amount: Optional[float] = None
    transaction_receipt: Optional[str] = None
    recipient_is_registered: Optional[str] = None
    recipient_name: Optional[str] = None
    completed_datetime: Optional[str] = None
    working_account_balance: Optional[float] = None
    utility_account_balance: Optional[float] = None
    charges_paid_balance: Optional[float] = None

    @classmethod
    def from_result_parameters(cls, result_parameters: dict):
        """Parse result parameters into structured format"""
        if not result_parameters:
            return cls()

        items = result_parameters.get("ResultParameter", [])
        data = {item["Key"]: item.get("Value") for item in items}

        return cls(
            transaction_amount=data.get("TransactionAmount"),
            transaction_receipt=data.get("TransactionReceipt"),
            recipient_is_registered=data.get("B2CRecipientIsRegisteredCustomer"),
            recipient_name=data.get("ReceiverPartyPublicName"),
            completed_datetime=data.get("TransactionCompletedDateTime"),
            working_account_balance=data.get("B2CWorkingAccountAvailableFunds"),
            utility_account_balance=data.get("B2CUtilityAccountAvailableFunds"),
            charges_paid_balance=data.get("B2CChargesPaidAccountAvailableFunds")
        )


# ==================== General Schemas ====================

class SuccessResponse(BaseModel):
    """Generic success response"""
    message: str
    data: Optional[dict] = None
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Operation completed successfully",
                "data": {"key": "value"},
                "timestamp": "2024-01-15T10:30:00"
            }
        }


class ErrorResponse(BaseModel):
    """Generic error response"""
    error: str
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    request_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        json_schema_extra = {
            "example": {
                "error": "Payment failed",
                "error_code": "401.002.01",
                "error_message": "Invalid Access Token",
                "request_id": "16813-15-1",
                "timestamp": "2024-01-15T10:30:00"
            }
        }