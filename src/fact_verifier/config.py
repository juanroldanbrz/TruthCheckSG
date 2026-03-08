from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    brave_api_key: str
    openai_keys: str = ""  # comma-separated list of OpenAI API keys for round-robin rotation
    openai_small_model: str = ""
    brightdata_api_key: str = ""
    max_sources: int = 10
    request_timeout: int = 90
    singstat_timeout: int = 20
    singstat_user_agent: str = "Mozilla/5.0 (compatible; TruthCheckSG/1.0; +https://tablebuilder.singstat.gov.sg)"
    singstat_max_sources: int = 2
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db: str = "fact_verifier"
    langfuse_secret_key: str = ""
    langfuse_public_key: str = ""
    langfuse_host: str = "http://localhost:3000"
    openai_model: str = "gpt-5-mini-2025-08-07"
    max_output_tokens: int = 5000

    model_config = {"env_file": ".env", "extra": "ignore"}

settings = Settings()
