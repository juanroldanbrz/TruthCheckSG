from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    brave_api_key: str
    openai_api_key: str
    brightdata_api_key: str = ""
    max_sources: int = 10
    request_timeout: int = 90
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db: str = "fact_verifier"

    model_config = {"env_file": ".env"}

settings = Settings()
