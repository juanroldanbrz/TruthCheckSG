import asyncio
import json
import uuid
from pathlib import Path

from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sse_starlette.sse import EventSourceResponse

from config import settings
from services.ocr import extract_text_from_image
from services.pipeline import run_pipeline

app = FastAPI(title="Fact Verifier SG")
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

# In-memory task store: task_id -> asyncio.Queue
_task_queues: dict[str, asyncio.Queue] = {}


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
    return templates.TemplateResponse("index.html", {"request": request, "i18n": I18N})


@app.post("/verify")
async def verify(
    request: Request,
    text: str = Form(default=""),
    language: str = Form(default="en"),
    image: UploadFile = File(default=None),
):
    claim = text.strip()

    if image and image.filename:
        image_bytes = await image.read()
        extracted = await extract_text_from_image(image_bytes, image.content_type)
        if not extracted:
            return JSONResponse({"error": "error_no_text"}, status_code=422)
        claim = extracted

    if not claim:
        return JSONResponse({"error": "error_empty"}, status_code=422)

    task_id = str(uuid.uuid4())
    queue: asyncio.Queue = asyncio.Queue()
    _task_queues[task_id] = queue

    async def background():
        async for event in run_pipeline(claim, language):
            await queue.put(event)
        await queue.put(None)  # sentinel

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

    return EventSourceResponse(event_generator())
