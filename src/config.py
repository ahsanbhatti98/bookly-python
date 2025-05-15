from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET: str
    JWT_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


Config = Settings()
