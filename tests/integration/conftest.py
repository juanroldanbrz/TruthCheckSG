import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def app_client():
    from fact_verifier.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
