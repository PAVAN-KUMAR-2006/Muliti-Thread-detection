from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")
    database_url: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_minutes: int = 15
    refresh_days: int = 7
    reset_minutes: int = 30
    cors_origins: str = "http://localhost:5173"
    frontend_url: str = "http://localhost:5173"
    model_dir: str = "../ml/models"
    upload_dir: str = "../uploads"


settings = Settings()
if len(settings.jwt_secret) < 32:
    raise RuntimeError("JWT_SECRET must be set to a random value of at least 32 characters.")
