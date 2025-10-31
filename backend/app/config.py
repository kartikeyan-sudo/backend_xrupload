from pydantic import BaseSettings


class Settings(BaseSettings):
    CLOUDINARY_CLOUD_NAME: str | None = None
    CLOUDINARY_API_KEY: str | None = None
    CLOUDINARY_API_SECRET: str | None = None
    MAX_UPLOAD_MB: int = 200
    ALLOWED_EXT: tuple = ("mp4", "mov", "avi", "mkv")

    class Config:
        env_file = ".env"


settings = Settings()
