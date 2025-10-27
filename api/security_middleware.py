# security_middleware.py
from fastapi import Request, HTTPException
from datetime import datetime, timezone, timedelta
import logging

REGISTERED_MERCHANTS = {
    "merchant_123": {"domains": ["https://shop.example.com"]},
    "merchant_456": {"domains": ["https://store.test.io"]},
}

# # For local development only
# REGISTERED_MERCHANTS = {
#     "merchant_dev": {"domains": [
#         "http://localhost:3000",      # ✅ Local dev
#         "http://127.0.0.1:3000",      # ✅ Local dev
#         "https://shop.example.com"    # ✅ Production
#     ]},
# }

# Define endpoints that REQUIRE security checks (initiated by your frontend)
PROTECTED_ENDPOINTS = [
    "/api/v1/stk-push/initiate",
    "/api/v1/b2c/payment",
    "/api/v1/b2b/payment",
]


ALLOWED_TIME_SKEW = timedelta(minutes=2)

logger = logging.getLogger("payment_security")
logging.basicConfig(level=logging.INFO)


async def payment_security_middleware(request: Request, call_next):
    # Skip middleware for non-payment endpoints
    if not request.url.path.startswith("/api/v1/"):
        return await call_next(request)

    # 3️⃣ Apply security checks only for protected endpoints
    if request.url.path not in PROTECTED_ENDPOINTS:
        # For any other endpoint not explicitly protected, allow through
        return await call_next(request)

    merchant_key = request.headers.get("x-merchant-key")
    timestamp = request.headers.get("x-request-timestamp")

    # 1️⃣ Ensure required headers exist
    if not (merchant_key and timestamp):
        raise HTTPException(
            status_code=400,
            detail="Missing required headers: Origin, X-Merchant-ID, X-Request-Timestamp"
        )

    # 2️⃣ Verify merchant exists
    merchant = REGISTERED_MERCHANTS.get(merchant_key)
    if not merchant:
        raise HTTPException(status_code=403, detail="Invalid merchant ID")



    # 4️⃣ Timestamp check (anti-replay)
    try:
        req_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid timestamp format (use ISO 8601)")

    now = datetime.now(timezone.utc)
    if abs(now - req_time) > ALLOWED_TIME_SKEW:
        raise HTTPException(status_code=400, detail="Request timestamp too old or in the future")

    # 5️⃣ Log the request
    logger.info(f"[{merchant_key}] {request.method} {request.url.path} ")

    # ✅ Proceed
    response = await call_next(request)
    return response