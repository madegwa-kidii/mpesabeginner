from fastapi import FastAPI



@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting M-Pesa Integration API...")
    yield
    print("Shutting down M-Pesa Integration API...")

app = FastAPI(
    title="M-Pesa Integration API",
    description="FastAPI integration for Safaricom M-Pesa APIs",
    version="1.0.0",
    lifespan=lifespan
)

# ✅ Ad

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
