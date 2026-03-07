import threading
import time

import httpx
import pytest
import uvicorn

BASE_URL = "http://127.0.0.1:8765"


@pytest.fixture(scope="session", autouse=True)
def live_server():
    from fact_verifier.main import app

    config = uvicorn.Config(app, host="127.0.0.1", port=8765, log_level="error")
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            httpx.get(BASE_URL, timeout=1)
            break
        except Exception:
            time.sleep(0.2)

    yield BASE_URL

    server.should_exit = True
    thread.join(timeout=5)
