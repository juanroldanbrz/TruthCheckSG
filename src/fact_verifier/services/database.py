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


async def save_verification(
    claim: str,
    language: str,
    result: dict,
    image_bytes: bytes | None = None,
    image_content_type: str | None = None,
) -> str:
    share_id = str(uuid.uuid4())
    doc = {
        "share_id": share_id,
        "claim": claim,
        "language": language,
        "result": result,
        "created_at": datetime.now(UTC),
    }
    if image_bytes:
        doc["image_bytes"] = image_bytes
        doc["image_content_type"] = image_content_type
    await _get_collection().insert_one(doc)
    return share_id


async def get_verification(share_id: str) -> dict | None:
    return await _get_collection().find_one({"share_id": share_id}, {"_id": 0})


async def get_verification_image(share_id: str) -> tuple[bytes, str] | None:
    doc = await _get_collection().find_one(
        {"share_id": share_id, "image_bytes": {"$exists": True}},
        {"image_bytes": 1, "image_content_type": 1},
    )
    if not doc:
        return None
    return bytes(doc["image_bytes"]), doc["image_content_type"]