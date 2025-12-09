from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    b2_application_key_id: str
    b2_application_key: str
    b2_bucket_id: str
    b2_bucket_name: str

    class Config:
        env_file = ".env"

settings = Settings()

