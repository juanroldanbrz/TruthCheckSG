import uuid
from datetime import datetime, UTC

from motor.motor_asyncio import AsyncIOMotorClient

from fact_verifier.config import settings

_client: AsyncIOMotorClient | None = None


def _get_collection():
    return _client[settings.mongodb_db]["verifications"]


async def connect():
    global _client
    _client = AsyncIOMotorClient(settings.mongodb_url)


async def disconnect():
    global _client
    if _client:
        _client.close()
        _client = None


async def save_verification(claim: str, language: str, result: dict) -> str:
    share_id = str(uuid.uuid4())
    await _get_collection().insert_one({
        "share_id": share_id,
        "claim": claim,
        "language": language,
        "result": result,
        "created_at": datetime.now(UTC),
    })
    return share_id


async def get_verification(share_id: str) -> dict | None:
    return await _get_collection().find_one({"share_id": share_id}, {"_id": 0})