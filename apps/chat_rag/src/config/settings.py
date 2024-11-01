from pydantic_settings import BaseSettings
from pydantic import validator

class Settings(BaseSettings):
    OPENAI_API_KEY: str
    COLLECTION_NAME: str = "chat-history"
    PERSIST_DIRECTORY: str = "src/data/chroma"
    MODEL_NAME: str = "gpt-4o"
    TEMPERATURE: float = 1.0

    @validator('OPENAI_API_KEY')
    def validate_api_key(cls, v):
        if not v:
            raise ValueError('OPENAI_API_KEY is required')
        return v

    class Config:
        env_file = ".env"