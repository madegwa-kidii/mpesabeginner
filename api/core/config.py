from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # M-Pesa API Credentials
    CONSUMER_KEY: str
    CONSUMER_SECRET: str

    # Business Configuration
    BUSINESS_SHORT_CODE: int
    PASSKEY: str
    INITIATOR_NAME: str
    INITIATOR_PASSWORD: str

    # API URLs
    BASE_URL: str

    # Callback URLs
    CALLBACK_BASE_URL: str
    STK_CALLBACK_URL: str
    B2C_RESULT_URL: str
    B2C_TIMEOUT_URL: str
    B2B_RESULT_URL: str
    B2B_TIMEOUT_URL: str

    # Security
    SECURITY_CREDENTIAL: str

    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    RELOAD: bool = True

    # Database
    DATABASE_URL: str | None = None

    # Redis
    REDIS_URL: str | None = None

    # Logging
    LOG_LEVEL: str = "INFO"

    # API timeouts (in seconds)
    API_TIMEOUT: int = 30

    # Dynamic URLs (computed)
    @property
    def oauth_url(self) -> str:
        """Safaricom OAuth endpoint"""
        return f"{self.BASE_URL}/oauth/v1/generate?grant_type=client_credentials"

    @property
    def stk_push_url(self) -> str:
        """Lipa na M-Pesa STK Push endpoint"""
        return f"{self.BASE_URL}/mpesa/stkpush/v1/processrequest"

    @property
    def stk_query_url(self) -> str:
        """STK Push Query endpoint"""
        return f"{self.BASE_URL}/mpesa/stkpushquery/v1/query"

    # Pydantic Settings Config
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
