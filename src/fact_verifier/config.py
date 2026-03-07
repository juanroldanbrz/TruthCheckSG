from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    brave_api_key: str
    openai_api_key: str
    # Optional: bias search toward a domain (e.g. "gov.sg"). Runs an extra search with site:domain and merges those results first.
    search_prefer_site: str = ""
    # Optional: Brave Goggles URL or inline rules to boost/demote domains (e.g. "$boost=5,site=gov.sg"). Must be registered at search.brave.com/goggles/create for API use.
    brave_goggles: str = ""
    brightdata_api_key: str = ""
    max_sources: int = 10
    request_timeout: int = 90
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db: str = "fact_verifier"
    langfuse_secret_key: str = ""
    langfuse_public_key: str = ""
    langfuse_host: str = "http://localhost:3000"

    model_config = {"env_file": ".env"}

settings = Settings()
