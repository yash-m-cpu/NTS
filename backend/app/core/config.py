
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DEBUG: bool = False
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5433/nts_db"
    REDIS_URL: str = "redis://localhost:6379/0"
    
    JWT_ACCESS_SECRET: str = "secret"
    JWT_REFRESH_PEPPER: str = "pepper"
    JWT_EXPIRATION_MINUTES: int = 15
    
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173"]

    S3_BUCKET_NAME: str = "nts-uploads"
    AWS_ACCESS_KEY_ID: str = "minioadmin"
    AWS_SECRET_ACCESS_KEY: str = "minioadmin"
    AWS_ENDPOINT_URL: str = "http://localhost:9000"
    AWS_REGION_NAME: str = "us-east-1"
    
    CV_FRAME_SAMPLE_RATE: int = 2
    HUMAN_DIR: str = "/human"

    # LLM settings — HuggingFace Inference API
    LLM_PROVIDER: str = "huggingface"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "mistralai/Mistral-7B-Instruct-v0.3"
    LLM_TIMEOUT: int = 120
    LLM_MAX_OUTPUT_TOKENS: int = 3000
    REPORT_PROMPT_VERSION: str = "1.0"

    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
