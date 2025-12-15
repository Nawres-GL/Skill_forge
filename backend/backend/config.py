from pydantic_settings import BaseSettings
from typing import Optional, List

class Settings(BaseSettings):
    # MongoDB
    MONGO_URI: str
    DATABASE_NAME: str = "skillforge"
    
    # JWT Authentication
    SECRET_KEY: str = "your_jwt_secret"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:4200", "http://localhost:3000"]

    # SMTP Config
    SMTP_SERVER: str
    SMTP_PORT: int
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    SMTP_SENDER: str

    # RapidAPI Config
    rapidapi_key: Optional[str] = None
    rapidapi_host: Optional[str] = "jsearch.p.rapidapi.com"
    rapidapi_url: Optional[str] = "https://jsearch.p.rapidapi.com"

    # Public base URL for serving static uploads
    BASE_URL: str = "http://localhost:8000"

    class Config:
        env_file = ".env"

settings = Settings()
