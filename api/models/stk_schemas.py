from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List
from datetime import datetime


class STKPushRequest(BaseModel):
    """Request model for initiating STK Push"""
    phone_number: str = Field(
        ...,
        description="Customer's phone number in format 254XXXXXXXXX or 0XXXXXXXXX",
        examples=["254712345678", "0712345678"]
    )
    amount: int = Field(
        ...,
        gt=0,
        description="Amount to charge (whole numbers only)",
        examples=[100, 1000]
    )
    account_reference: str = Field(
        ...,
        max_length=12,
        description="Account reference (alphanumeric, max 12 characters)",
        examples=["INV001", "ORDER123"]
    )
    transaction_desc: str = Field(
        ...,
        max_length=13,
        description="Transaction description (max 13 characters)",
        examples=["Payment", "Order Payment"]
    )

    @field_validator('account_reference')
    @classmethod
    def validate_account_reference(cls, v: str) -> str:
        if not v.isalnum():
            raise ValueError('Account reference must be alphanumeric')
        return v

    @field_validator('phone_number')
    @classmethod
    def validate_phone_number(cls, v: str) -> str:
        # Remove spaces and special characters
        cleaned = ''.join(filter(str.isdigit, v))

        if len(cleaned) < 9 or len(cleaned) > 12:
            raise ValueError('Invalid phone number length')

        return v

    class Config:
        json_schema_extra = {
            "example": {
                "phone_number": "254712345678",
                "amount": 100,
                "account_reference": "INV001",
                "transaction_desc": "Payment"
            }
        }


class STKPushResponse(BaseModel):
    """Response model for STK Push initiation"""
    merchant_request_id: str = Field(
        ...,
        description="Global unique identifier for the payment request"
    )
    checkout_request_id: str = Field(
        ...,
        description="Global unique identifier for the checkout transaction"
    )
    response_code: str = Field(
        ...,
        description="Status code (0 = success, others = error)"
    )
    response_description: str = Field(
        ...,
        description="Response status message"
    )
    customer_message: str = Field(
        ...,
        description="Message to display to customer"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "merchant_request_id": "29115-34620561-1",
                "checkout_request_id": "ws_CO_191220191020363925",
                "response_code": "0",
                "response_description": "Success. Request accepted for processing",
                "customer_message": "Success. Request accepted for processing"
            }
        }


class CallbackMetadataItem(BaseModel):
    """Individual item in callback metadata"""
    Name: str
    Value: Optional[Any] = None


class CallbackMetadata(BaseModel):
    """Metadata returned in successful callback"""
    Item: List[CallbackMetadataItem]


class STKCallback(BaseModel):
    """STK callback data structure"""
    MerchantRequestID: str
    CheckoutRequestID: str
    ResultCode: int
    ResultDesc: str
    CallbackMetadata: Optional[CallbackMetadata] = None


class STKPushCallback(BaseModel):
    """Complete callback model for STK Push results"""
    merchant_request_id: str = Field(
        ...,
        description="Global unique identifier for the payment request"
    )
    checkout_request_id: str = Field(
        ...,
        description="Global unique identifier for the checkout transaction"
    )
    result_code: int = Field(
        ...,
        description="Result code (0 = success, others = failure)"
    )
    result_desc: str = Field(
        ...,
        description="Result description message"
    )
    callback_metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Transaction metadata (only for successful transactions)"
    )

    @property
    def is_successful(self) -> bool:
        """Check if transaction was successful"""
        return self.result_code == 0

    @property
    def amount(self) -> Optional[float]:
        """Extract amount from metadata"""
        if not self.callback_metadata:
            return None
        items = self.callback_metadata.get('Item', [])
        for item in items:
            if item.get('Name') == 'Amount':
                return float(item.get('Value', 0))
        return None

    @property
    def mpesa_receipt_number(self) -> Optional[str]:
        """Extract M-Pesa receipt number from metadata"""
        if not self.callback_metadata:
            return None
        items = self.callback_metadata.get('Item', [])
        for item in items:
            if item.get('Name') == 'MpesaReceiptNumber':
                return str(item.get('Value'))
        return None

    @property
    def transaction_date(self) -> Optional[str]:
        """Extract transaction date from metadata"""
        if not self.callback_metadata:
            return None
        items = self.callback_metadata.get('Item', [])
        for item in items:
            if item.get('Name') == 'TransactionDate':
                return str(item.get('Value'))
        return None

    @property
    def phone_number(self) -> Optional[str]:
        """Extract phone number from metadata"""
        if not self.callback_metadata:
            return None
        items = self.callback_metadata.get('Item', [])
        for item in items:
            if item.get('Name') == 'PhoneNumber':
                return str(item.get('Value'))
        return None

    class Config:
        json_schema_extra = {
            "example": {
                "merchant_request_id": "29115-34620561-1",
                "checkout_request_id": "ws_CO_191220191020363925",
                "result_code": 0,
                "result_desc": "The service request is processed successfully.",
                "callback_metadata": {
                    "Item": [
                        {"Name": "Amount", "Value": 1.00},
                        {"Name": "MpesaReceiptNumber", "Value": "NLJ7RT61SV"},
                        {"Name": "TransactionDate", "Value": 20191219102115},
                        {"Name": "PhoneNumber", "Value": 254708374149}
                    ]
                }
            }
        }


class STKQueryRequest(BaseModel):
    """Request model for querying STK Push status"""
    checkout_request_id: str = Field(
        ...,
        description="The checkout request ID from initial STK push"
    )


class STKQueryResponse(BaseModel):
    """Response model for STK Push query"""
    merchant_request_id: str
    checkout_request_id: str
    response_code: str
    response_description: str
    result_code: Optional[str] = None
    result_desc: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "merchant_request_id": "29115-34620561-1",
                "checkout_request_id": "ws_CO_191220191020363925",
                "response_code": "0",
                "response_description": "The service request has been accepted successfully",
                "result_code": "0",
                "result_desc": "The service request is processed successfully."
            }
        }


class SuccessResponse(BaseModel):
    """Generic success response"""
    message: str = Field(
        ...,
        description="Success message"
    )
    data: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional response data"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Response timestamp"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Operation completed successfully",
                "data": {"id": "123", "status": "completed"},
                "timestamp": "2024-01-20T10:30:00"
            }
        }


class ErrorResponse(BaseModel):
    """Generic error response"""
    error: str = Field(
        ...,
        description="Error message"
    )
    error_code: Optional[str] = Field(
        None,
        description="Error code if available"
    )
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional error details"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Error timestamp"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "error": "Invalid request parameters",
                "error_code": "VALIDATION_ERROR",
                "details": {"field": "phone_number", "issue": "Invalid format"},
                "timestamp": "2024-01-20T10:30:00"
            }
        }


class TransactionStatus(BaseModel):
    """Model for tracking transaction status"""
    checkout_request_id: str
    merchant_request_id: str
    status: str = Field(
        ...,
        description="Transaction status: pending, completed, failed, cancelled"
    )
    amount: Optional[float] = None
    phone_number: Optional[str] = None
    mpesa_receipt_number: Optional[str] = None
    transaction_date: Optional[str] = None
    result_code: Optional[int] = None
    result_description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        json_schema_extra = {
            "example": {
                "checkout_request_id": "ws_CO_191220191020363925",
                "merchant_request_id": "29115-34620561-1",
                "status": "completed",
                "amount": 100.0,
                "phone_number": "254712345678",
                "mpesa_receipt_number": "NLJ7RT61SV",
                "transaction_date": "20191219102115",
                "result_code": 0,
                "result_description": "The service request is processed successfully.",
                "created_at": "2024-01-20T10:30:00",
                "updated_at": "2024-01-20T10:31:00"
            }
        }



