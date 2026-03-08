import asyncio
import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

logger = logging.getLogger(__name__)

from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
try:
    from sse_starlette.sse import EventSourceResponse
except Exception:
    from starlette.responses import StreamingResponse

    class EventSourceResponse(StreamingResponse):
        def __init__(self, content, **kwargs):
            async def event_stream():
                async for event in content:
                    yield f"event: {event['event']}\ndata: {event['data']}\n\n"

            super().__init__(event_stream(), media_type="text/event-stream", **kwargs)

from fact_verifier.config import settings
from fact_verifier.services.database import connect, disconnect, save_verification, get_verification, get_verification_image
from fact_verifier.services.ocr import analyze_image
from fact_verifier.services.pipeline import run_pipeline
from fact_verifier.services.verifier import describe_image

# In-memory task store: task_id -> asyncio.Queue
_task_queues: dict[str, asyncio.Queue] = {}
_task_timestamps: dict[str, float] = {}
QUEUE_TTL = 120  # seconds


async def _cleanup_stale_queues():
    while True:
        await asyncio.sleep(30)
        now = time.monotonic()
        stale = [tid for tid, ts in _task_timestamps.items() if now - ts > QUEUE_TTL]
        for tid in stale:
            _task_queues.pop(tid, None)
            _task_timestamps.pop(tid, None)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect()
    asyncio.create_task(_cleanup_stale_queues())
    yield
    await disconnect()


app = FastAPI(title="Fact Verifier SG", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def _load_i18n() -> dict:
    i18n = {}
    for lang in ("en", "zh", "ms", "ta"):
        path = Path(__file__).parent / "i18n" / f"{lang}.json"
        if path.exists():
            i18n[lang] = json.loads(path.read_text(encoding="utf-8"))
    return i18n


I18N = _load_i18n()


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request, "index.html", {"i18n": I18N})


@app.post("/verify")
async def verify(
    request: Request,
    text: str = Form(default=""),
    language: str = Form(default="en"),
    image: UploadFile = File(default=None),
):
    claim = text.strip()
    raw_image_bytes: bytes | None = None
    raw_image_content_type: str | None = None
    pipeline_image_bytes: bytes | None = None
    pipeline_image_content_type: str | None = None

    if image and image.filename:
        ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp"}
        if image.content_type not in ALLOWED_IMAGE_TYPES:
            return JSONResponse({"error": "error_no_text"}, status_code=422)
        image_bytes = await image.read()
        raw_image_bytes = image_bytes
        raw_image_content_type = image.content_type
        pipeline_image_bytes = image_bytes
        pipeline_image_content_type = image.content_type

        analysis = await analyze_image(image_bytes, image.content_type)
        if not analysis:
            return JSONResponse({"error": "error_no_text"}, status_code=422)

        image_context = f"Image text: {analysis.ocr_text}\nImage intent: {analysis.intent}"

        if claim:
            claim = f"{claim}\n\n{image_context}"
        else:
            claim = image_context

    if not claim:
        return JSONResponse({"error": "error_empty"}, status_code=422)

    task_id = str(uuid.uuid4())
    queue: asyncio.Queue = asyncio.Queue()
    _task_queues[task_id] = queue
    _task_timestamps[task_id] = time.monotonic()

    is_image_only = raw_image_bytes is not None and not text.strip()

    async def background():
        try:
            image_description = None
            if is_image_only:
                try:
                    image_description = await describe_image(raw_image_bytes, raw_image_content_type)
                except Exception:
                    pass

            async for event in run_pipeline(
                claim,
                language,
                image_bytes=pipeline_image_bytes,
                image_content_type=pipeline_image_content_type,
            ):
                if event.get("type") == "result":
                    share_id = await save_verification(
                        claim, language, event["data"],
                        image_bytes=raw_image_bytes,
                        image_content_type=raw_image_content_type,
                    )
                    event["share_id"] = share_id
                    event["has_image"] = raw_image_bytes is not None
                    event["claim"] = claim
                    if image_description:
                        event["image_description"] = image_description
                await queue.put(event)
        except Exception:
            logger.exception("Pipeline background task failed")
            await queue.put({"type": "error", "message": "error_generic"})
        finally:
            await queue.put(None)  # sentinel always sent

    asyncio.create_task(background())
    return JSONResponse({"task_id": task_id})


@app.get("/stream/{task_id}")
async def stream(task_id: str):
    queue = _task_queues.get(task_id)
    if not queue:
        return JSONResponse({"error": "not found"}, status_code=404)

    async def event_generator():
        try:
            while True:
                event = await asyncio.wait_for(queue.get(), timeout=settings.request_timeout)
                if event is None:
                    break
                yield {"event": event["type"], "data": json.dumps(event)}
        except asyncio.TimeoutError:
            yield {"event": "error", "data": json.dumps({"message": "error_generic"})}
        finally:
            _task_queues.pop(task_id, None)
            _task_timestamps.pop(task_id, None)

    return EventSourceResponse(event_generator())


@app.get("/share/{share_id}", response_class=HTMLResponse)
async def share(request: Request, share_id: str):
    doc = await get_verification(share_id)
    if not doc:
        return JSONResponse({"error": "not found"}, status_code=404)
    shared_image_url = f"/share/{share_id}/image" if doc.get("image_bytes") else None
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "i18n": I18N,
            "shared_result": doc["result"],
            "shared_claim": doc["claim"],
            "shared_image_url": shared_image_url,
        },
    )


@app.get("/share/{share_id}/image")
async def share_image(share_id: str):
    result = await get_verification_image(share_id)
    if not result:
        return JSONResponse({"error": "not found"}, status_code=404)
    image_bytes, content_type = result
    return Response(content=image_bytes, media_type=content_type)
