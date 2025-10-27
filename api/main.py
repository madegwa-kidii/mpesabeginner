from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.security_middleware import payment_security_middleware


app = FastAPI(
    title="M-Pesa Integration API",
    description="FastAPI integration for Safaricom M-Pesa APIs",
    version="1.0.0",
)


# ✅ Add security middleware using decorator
app.middleware("http")(payment_security_middleware)

# ✅ Allow CORS for both HTTP & WebSocket
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # you can restrict this to your frontend domain later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "message": "M-Pesa Integration API",
        "version": "1.0.0",
        "endpoints": {
            "stk_push": "/api/v1/stk-push",
            "b2c": "/api/v1/b2c",
            "b2b": "/api/v1/b2b",
            "websocket": "/ws/payments"
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
