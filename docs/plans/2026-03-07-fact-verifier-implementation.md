# Fact Verifier Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Singapore-focused fact-checking web app where users submit text or screenshots and receive a structured verdict with ranked sources, powered by Brave Search + ChatGPT, with a FastAPI + Jinja2 frontend in 4 languages.

**Architecture:** User submits claim (text or image) via a single-page Jinja2 UI → FastAPI spawns an async background task → browser connects to SSE stream for step-by-step progress → pipeline: OCR (if image) → Brave Search (10 results) → parallel URL fetch + trafilatura markdown → ChatGPT verdict → SSE result event.

**Tech Stack:** Python 3.11+, FastAPI, Jinja2, uvicorn, openai SDK, httpx (async HTTP), trafilatura, python-dotenv, python-multipart (file uploads)

---

## Task 0: Project Scaffold

**Files:**
- Create: `requirements.txt`
- Create: `config.py`
- Create: `.env.example`
- Create: `main.py`
- Create: `services/__init__.py`
- Create: `static/.gitkeep`
- Create: `templates/.gitkeep`
- Create: `i18n/.gitkeep`

**Step 1: Create requirements.txt**

```
fastapi==0.115.5
uvicorn[standard]==0.32.1
jinja2==3.1.4
python-multipart==0.0.18
python-dotenv==1.0.1
openai==1.57.0
httpx==0.27.2
trafilatura==2.0.0
sse-starlette==2.1.3
```

**Step 2: Create config.py**

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    brave_api_key: str
    openai_api_key: str
    max_sources: int = 10
    request_timeout: int = 90

    model_config = {"env_file": ".env"}

settings = Settings()
```

Note: add `pydantic-settings==2.6.1` to requirements.txt.

**Step 3: Create .env.example**

```
BRAVE_API_KEY=your_brave_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
```

**Step 4: Create main.py skeleton**

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Fact Verifier SG")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
```

**Step 5: Create service directories and run install**

```bash
mkdir -p services static templates i18n tests
touch services/__init__.py
cp .env.example .env
pip install -r requirements.txt
```

**Step 6: Verify install**

```bash
python -c "import fastapi, openai, trafilatura, sse_starlette; print('OK')"
```
Expected: `OK`

**Step 7: Commit**

```bash
git add requirements.txt config.py .env.example main.py services/__init__.py
git commit -m "feat: scaffold project structure and dependencies"
```

---

## Task 1: i18n Strings

**Files:**
- Create: `i18n/en.json`
- Create: `i18n/zh.json`
- Create: `i18n/ms.json`
- Create: `i18n/ta.json`

**Step 1: Create en.json**

```json
{
  "app_title": "Singapore Fact Checker",
  "app_subtitle": "Submit a claim or screenshot to verify its accuracy",
  "input_placeholder": "Type or paste a claim here...",
  "upload_label": "Or upload a screenshot",
  "submit_button": "Check Fact",
  "checking_message": "This may take 20-30 seconds, please wait.",
  "step_1": "Searching sources...",
  "step_2": "Reading articles...",
  "step_3": "Analysing facts...",
  "verdict_verified": "VERIFIED",
  "verdict_false": "FALSE",
  "verdict_unverified": "UNVERIFIED",
  "sources_title": "Sources checked",
  "tier_government": "Government",
  "tier_news": "News",
  "tier_other": "Other",
  "stance_supports": "Supports",
  "stance_contradicts": "Contradicts",
  "stance_neutral": "Neutral",
  "reset_button": "Check another fact",
  "error_empty": "Please enter a claim or upload an image.",
  "error_generic": "Something went wrong. Please try again.",
  "error_no_text": "Could not extract text from image. Please try again.",
  "limited_sources": "Limited sources found."
}
```

**Step 2: Create zh.json**

```json
{
  "app_title": "新加坡事实核查",
  "app_subtitle": "提交声明或截图以核实其准确性",
  "input_placeholder": "在此输入或粘贴声明...",
  "upload_label": "或上传截图",
  "submit_button": "核查事实",
  "checking_message": "这可能需要20-30秒，请稍候。",
  "step_1": "正在搜索来源...",
  "step_2": "正在阅读文章...",
  "step_3": "正在分析事实...",
  "verdict_verified": "已核实",
  "verdict_false": "错误",
  "verdict_unverified": "无法核实",
  "sources_title": "已核查来源",
  "tier_government": "政府",
  "tier_news": "新闻",
  "tier_other": "其他",
  "stance_supports": "支持",
  "stance_contradicts": "反驳",
  "stance_neutral": "中立",
  "reset_button": "核查另一个事实",
  "error_empty": "请输入声明或上传图片。",
  "error_generic": "出现错误，请重试。",
  "error_no_text": "无法从图片中提取文字，请重试。",
  "limited_sources": "找到的来源有限。"
}
```

**Step 3: Create ms.json**

```json
{
  "app_title": "Pemeriksa Fakta Singapura",
  "app_subtitle": "Hantar dakwaan atau tangkapan skrin untuk mengesahkan ketepatannya",
  "input_placeholder": "Taip atau tampal dakwaan di sini...",
  "upload_label": "Atau muat naik tangkapan skrin",
  "submit_button": "Semak Fakta",
  "checking_message": "Ini mungkin mengambil masa 20-30 saat, sila tunggu.",
  "step_1": "Mencari sumber...",
  "step_2": "Membaca artikel...",
  "step_3": "Menganalisis fakta...",
  "verdict_verified": "DISAHKAN",
  "verdict_false": "PALSU",
  "verdict_unverified": "TIDAK DAPAT DISAHKAN",
  "sources_title": "Sumber yang disemak",
  "tier_government": "Kerajaan",
  "tier_news": "Berita",
  "tier_other": "Lain-lain",
  "stance_supports": "Menyokong",
  "stance_contradicts": "Bercanggah",
  "stance_neutral": "Neutral",
  "reset_button": "Semak fakta lain",
  "error_empty": "Sila masukkan dakwaan atau muat naik gambar.",
  "error_generic": "Ralat berlaku. Sila cuba lagi.",
  "error_no_text": "Tidak dapat mengekstrak teks dari gambar. Sila cuba lagi.",
  "limited_sources": "Sumber yang ditemui adalah terhad."
}
```

**Step 4: Create ta.json**

```json
{
  "app_title": "சிங்கப்பூர் உண்மை சரிபார்ப்பு",
  "app_subtitle": "துல்லியத்தை சரிபார்க்க ஒரு கூற்று அல்லது திரைப்பிடிப்பை சமர்ப்பிக்கவும்",
  "input_placeholder": "இங்கே கூற்றை தட்டச்சு செய்யவும் அல்லது ஒட்டவும்...",
  "upload_label": "அல்லது திரைப்பிடிப்பை பதிவேற்றவும்",
  "submit_button": "உண்மையை சரிபார்",
  "checking_message": "இது 20-30 வினாடிகள் ஆகலாம், தயவுசெய்து காத்திருங்கள்.",
  "step_1": "ஆதாரங்களை தேடுகிறது...",
  "step_2": "கட்டுரைகளை படிக்கிறது...",
  "step_3": "உண்மைகளை பகுப்பாய்வு செய்கிறது...",
  "verdict_verified": "சரிபார்க்கப்பட்டது",
  "verdict_false": "தவறானது",
  "verdict_unverified": "சரிபார்க்க முடியவில்லை",
  "sources_title": "சரிபார்க்கப்பட்ட ஆதாரங்கள்",
  "tier_government": "அரசாங்கம்",
  "tier_news": "செய்தி",
  "tier_other": "மற்றவை",
  "stance_supports": "ஆதரிக்கிறது",
  "stance_contradicts": "எதிர்க்கிறது",
  "stance_neutral": "நடுநிலை",
  "reset_button": "மற்றொரு உண்மையை சரிபார்",
  "error_empty": "தயவுசெய்து ஒரு கூற்றை உள்ளிடவும் அல்லது படத்தை பதிவேற்றவும்.",
  "error_generic": "ஏதோ தவறு நடந்தது. மீண்டும் முயற்சிக்கவும்.",
  "error_no_text": "படத்திலிருந்து உரையை பிரிக்க முடியவில்லை. மீண்டும் முயற்சிக்கவும்.",
  "limited_sources": "வரையறுக்கப்பட்ட ஆதாரங்கள் கண்டுபிடிக்கப்பட்டன."
}
```

**Step 5: Commit**

```bash
git add i18n/
git commit -m "feat: add i18n strings for EN, ZH, MS, TA"
```

---

## Task 2: OCR Service

**Files:**
- Create: `services/ocr.py`
- Create: `tests/test_ocr.py`

**Step 1: Write the failing test**

```python
# tests/test_ocr.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

@pytest.mark.asyncio
async def test_extract_text_from_image_returns_string():
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "CPF withdrawal age raised to 65"

    with patch("services.ocr.client.chat.completions.create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_response
        from services.ocr import extract_text_from_image
        result = await extract_text_from_image(b"fake_image_bytes", "image/png")
        assert isinstance(result, str)
        assert len(result) > 0

@pytest.mark.asyncio
async def test_extract_text_returns_none_on_empty_response():
    mock_response = MagicMock()
    mock_response.choices[0].message.content = ""

    with patch("services.ocr.client.chat.completions.create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_response
        from services.ocr import extract_text_from_image
        result = await extract_text_from_image(b"fake_image_bytes", "image/png")
        assert result is None
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_ocr.py -v
```
Expected: `ImportError` or `ModuleNotFoundError`

**Step 3: Implement services/ocr.py**

```python
import base64
from openai import AsyncOpenAI
from config import settings

client = AsyncOpenAI(api_key=settings.openai_api_key)

async def extract_text_from_image(image_bytes: bytes, content_type: str) -> str | None:
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Extract all visible text from this image exactly as written. "
                            "Return only the extracted text, no commentary. "
                            "If there is no readable text, return an empty string."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{content_type};base64,{b64}"},
                    },
                ],
            }
        ],
        max_tokens=1000,
    )
    text = response.choices[0].message.content.strip()
    return text if text else None
```

**Step 4: Run tests**

```bash
pytest tests/test_ocr.py -v
```
Expected: 2 PASSED

**Step 5: Commit**

```bash
git add services/ocr.py tests/test_ocr.py
git commit -m "feat: add GPT-4o Vision OCR service"
```

---

## Task 3: Brave Search Service

**Files:**
- Create: `services/search.py`
- Create: `tests/test_search.py`

**Step 1: Write the failing test**

```python
# tests/test_search.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

MOCK_BRAVE_RESPONSE = {
    "web": {
        "results": [
            {"title": "MOH Advisory", "url": "https://www.moh.gov.sg/advisory", "description": "Official MOH info"},
            {"title": "CNA Article", "url": "https://www.channelnewsasia.com/article", "description": "CNA coverage"},
        ]
    }
}

@pytest.mark.asyncio
async def test_search_returns_list_of_results():
    mock_response = MagicMock()
    mock_response.json = AsyncMock(return_value=MOCK_BRAVE_RESPONSE)
    mock_response.raise_for_status = MagicMock()

    with patch("services.search.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        from services.search import brave_search
        results = await brave_search("CPF withdrawal age")
        assert isinstance(results, list)
        assert len(results) == 2
        assert results[0]["url"] == "https://www.moh.gov.sg/advisory"

@pytest.mark.asyncio
async def test_search_returns_empty_list_on_no_results():
    mock_response = MagicMock()
    mock_response.json = AsyncMock(return_value={"web": {"results": []}})
    mock_response.raise_for_status = MagicMock()

    with patch("services.search.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        from services.search import brave_search
        results = await brave_search("nonexistent claim")
        assert results == []
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_search.py -v
```
Expected: `ImportError`

**Step 3: Implement services/search.py**

```python
import httpx
from config import settings

BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"

async def brave_search(query: str, count: int = 10) -> list[dict]:
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": settings.brave_api_key,
    }
    params = {"q": query, "count": count, "search_lang": "en", "country": "SG"}

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(BRAVE_SEARCH_URL, headers=headers, params=params)
        response.raise_for_status()
        data = await response.json()

    results = data.get("web", {}).get("results", [])
    return [
        {"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("description", "")}
        for r in results
    ]
```

**Step 4: Run tests**

```bash
pytest tests/test_search.py -v
```
Expected: 2 PASSED

**Step 5: Commit**

```bash
git add services/search.py tests/test_search.py
git commit -m "feat: add Brave Search service"
```

---

## Task 4: URL Scraper Service

**Files:**
- Create: `services/scraper.py`
- Create: `tests/test_scraper.py`

**Step 1: Write the failing test**

```python
# tests/test_scraper.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

@pytest.mark.asyncio
async def test_fetch_and_convert_returns_markdown():
    mock_response = MagicMock()
    mock_response.text = "<html><body><p>CPF is a retirement scheme.</p></body></html>"
    mock_response.raise_for_status = MagicMock()

    with patch("services.scraper.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        with patch("services.scraper.trafilatura.extract", return_value="CPF is a retirement scheme."):
            from services.scraper import fetch_as_markdown
            result = await fetch_as_markdown("https://www.cpf.gov.sg/article")
            assert result is not None
            assert "CPF" in result

@pytest.mark.asyncio
async def test_fetch_returns_none_on_failure():
    with patch("services.scraper.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(side_effect=Exception("timeout"))
        mock_client_class.return_value = mock_client

        from services.scraper import fetch_as_markdown
        result = await fetch_as_markdown("https://bad-url.example.com")
        assert result is None
```

**Step 2: Run to verify failure**

```bash
pytest tests/test_scraper.py -v
```
Expected: `ImportError`

**Step 3: Implement services/scraper.py**

```python
import asyncio
import httpx
import trafilatura

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; FactCheckerSG/1.0)"
}

async def fetch_as_markdown(url: str) -> str | None:
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            response = await client.get(url, headers=HEADERS)
            response.raise_for_status()
            html = response.text
        text = trafilatura.extract(html, include_links=False, include_tables=False)
        return text if text else None
    except Exception:
        return None

async def fetch_all(urls: list[str]) -> list[dict]:
    tasks = [fetch_as_markdown(url) for url in urls]
    results = await asyncio.gather(*tasks)
    return [
        {"url": url, "markdown": md}
        for url, md in zip(urls, results)
        if md is not None
    ]
```

**Step 4: Run tests**

```bash
pytest tests/test_scraper.py -v
```
Expected: 2 PASSED

**Step 5: Commit**

```bash
git add services/scraper.py tests/test_scraper.py
git commit -m "feat: add async URL scraper with trafilatura"
```

---

## Task 5: Source Tier Classifier

**Files:**
- Create: `services/tier.py`
- Create: `tests/test_tier.py`

**Step 1: Write failing test**

```python
# tests/test_tier.py
from services.tier import classify_tier

def test_gov_sg_is_government():
    assert classify_tier("https://www.moh.gov.sg/advisory") == "government"

def test_cpf_is_government():
    assert classify_tier("https://www.cpf.gov.sg/member") == "government"

def test_cna_is_news():
    assert classify_tier("https://www.channelnewsasia.com/singapore") == "news"

def test_straits_times_is_news():
    assert classify_tier("https://www.straitstimes.com/singapore") == "news"

def test_unknown_is_other():
    assert classify_tier("https://www.reddit.com/r/singapore") == "other"
```

**Step 2: Run to verify failure**

```bash
pytest tests/test_tier.py -v
```
Expected: `ImportError`

**Step 3: Implement services/tier.py**

```python
from urllib.parse import urlparse

GOV_DOMAINS = {".gov.sg"}
NEWS_DOMAINS = {
    "channelnewsasia.com", "cna.asia",
    "straitstimes.com",
    "todayonline.com",
    "mothership.sg",
    "zaobao.com.sg",
    "beritaharian.sg",
    "tamilmurasu.com.sg",
    "8world.com",
}

def classify_tier(url: str) -> str:
    try:
        hostname = urlparse(url).hostname or ""
    except Exception:
        return "other"

    if any(hostname.endswith(d) for d in GOV_DOMAINS):
        return "government"
    if any(hostname.endswith(d) or hostname == d for d in NEWS_DOMAINS):
        return "news"
    return "other"
```

**Step 4: Run tests**

```bash
pytest tests/test_tier.py -v
```
Expected: 5 PASSED

**Step 5: Commit**

```bash
git add services/tier.py tests/test_tier.py
git commit -m "feat: add source tier classifier for SG domains"
```

---

## Task 6: Verifier Service (ChatGPT)

**Files:**
- Create: `services/verifier.py`
- Create: `tests/test_verifier.py`

**Step 1: Write failing test**

```python
# tests/test_verifier.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

MOCK_SOURCES = [
    {"url": "https://www.moh.gov.sg/advisory", "title": "MOH", "tier": "government", "snippet": "No such policy.", "markdown": "No such policy exists."}
]

MOCK_GPT_RESPONSE = """{
  "verdict": "false",
  "summary": "This claim is not supported by official sources.",
  "explanation": "The Ministry of Health has not announced any such policy.",
  "sources": [
    {
      "url": "https://www.moh.gov.sg/advisory",
      "title": "MOH",
      "tier": "government",
      "credibility_label": "Official Government Source",
      "stance": "contradicts",
      "snippet": "No such policy exists."
    }
  ]
}"""

@pytest.mark.asyncio
async def test_verify_returns_structured_result():
    mock_response = MagicMock()
    mock_response.choices[0].message.content = MOCK_GPT_RESPONSE

    with patch("services.verifier.client.chat.completions.create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_response
        from services.verifier import verify_claim
        result = await verify_claim("CPF age raised to 70", MOCK_SOURCES, "en")
        assert result["verdict"] in ("verified", "false", "unverified")
        assert "summary" in result
        assert "sources" in result
        assert isinstance(result["sources"], list)
```

**Step 2: Run to verify failure**

```bash
pytest tests/test_verifier.py -v
```
Expected: `ImportError`

**Step 3: Implement services/verifier.py**

```python
import json
from openai import AsyncOpenAI
from config import settings

client = AsyncOpenAI(api_key=settings.openai_api_key)

SYSTEM_PROMPT = """You are a fact-checking assistant for Singapore.
You will receive a claim and a list of sources with their content.
Respond ONLY in {language}.
Analyse the sources and return a JSON object with this exact structure:
{{
  "verdict": "verified" | "false" | "unverified",
  "summary": "2-3 sentence summary of your finding",
  "explanation": "Detailed paragraph explaining the verdict",
  "sources": [
    {{
      "url": "source url",
      "title": "source title",
      "tier": "government" | "news" | "other",
      "credibility_label": "human-readable credibility description",
      "stance": "supports" | "contradicts" | "neutral",
      "snippet": "relevant excerpt from the source"
    }}
  ]
}}
Sort sources: government first, then news, then other.
Return ONLY valid JSON, no markdown code blocks."""

LANGUAGE_NAMES = {
    "en": "English",
    "zh": "Simplified Chinese",
    "ms": "Malay",
    "ta": "Tamil",
}

def _build_sources_text(sources: list[dict]) -> str:
    parts = []
    for i, s in enumerate(sources, 1):
        parts.append(
            f"Source {i}:\nURL: {s['url']}\nTitle: {s['title']}\nTier: {s['tier']}\n"
            f"Snippet: {s.get('snippet', '')}\nContent:\n{s.get('markdown', '')[:2000]}"
        )
    return "\n\n---\n\n".join(parts)

async def verify_claim(claim: str, sources: list[dict], language: str = "en") -> dict:
    lang_name = LANGUAGE_NAMES.get(language, "English")
    system = SYSTEM_PROMPT.format(language=lang_name)
    sources_text = _build_sources_text(sources)
    user_message = f"Claim to verify: {claim}\n\nSources:\n{sources_text}"

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_message},
        ],
        max_tokens=2000,
        temperature=0.1,
    )
    content = response.choices[0].message.content.strip()
    return json.loads(content)
```

**Step 4: Run tests**

```bash
pytest tests/test_verifier.py -v
```
Expected: 1 PASSED

**Step 5: Commit**

```bash
git add services/verifier.py tests/test_verifier.py
git commit -m "feat: add ChatGPT verifier service with multilingual support"
```

---

## Task 7: Pipeline Orchestrator

**Files:**
- Create: `services/pipeline.py`
- Create: `tests/test_pipeline.py`

**Step 1: Write failing test**

```python
# tests/test_pipeline.py
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_pipeline_emits_progress_and_result_events():
    events = []

    async def collect_events(claim, language):
        from services.pipeline import run_pipeline
        async for event in run_pipeline(claim, language):
            events.append(event)

    with patch("services.pipeline.brave_search", new_callable=AsyncMock) as mock_search, \
         patch("services.pipeline.fetch_all", new_callable=AsyncMock) as mock_fetch, \
         patch("services.pipeline.verify_claim", new_callable=AsyncMock) as mock_verify:

        mock_search.return_value = [
            {"url": "https://www.moh.gov.sg/a", "title": "MOH", "snippet": "info"}
        ]
        mock_fetch.return_value = [
            {"url": "https://www.moh.gov.sg/a", "markdown": "Content here"}
        ]
        mock_verify.return_value = {
            "verdict": "false",
            "summary": "Not true.",
            "explanation": "Details.",
            "sources": []
        }

        await collect_events("some claim", "en")

    event_types = [e["type"] for e in events]
    assert "progress" in event_types
    assert "result" in event_types

@pytest.mark.asyncio
async def test_pipeline_emits_error_on_no_sources():
    events = []

    with patch("services.pipeline.brave_search", new_callable=AsyncMock) as mock_search, \
         patch("services.pipeline.fetch_all", new_callable=AsyncMock) as mock_fetch:

        mock_search.return_value = []
        mock_fetch.return_value = []

        from services.pipeline import run_pipeline
        async for event in run_pipeline("obscure claim", "en"):
            events.append(event)

    assert any(e["type"] == "error" for e in events)
```

**Step 2: Run to verify failure**

```bash
pytest tests/test_pipeline.py -v
```
Expected: `ImportError`

**Step 3: Implement services/pipeline.py**

```python
import asyncio
from typing import AsyncGenerator
from services.search import brave_search
from services.scraper import fetch_all
from services.verifier import verify_claim
from services.tier import classify_tier

async def run_pipeline(
    claim: str, language: str = "en"
) -> AsyncGenerator[dict, None]:

    yield {"type": "progress", "step": 1, "message": "step_1"}

    search_results = await brave_search(claim)
    if not search_results:
        yield {"type": "error", "message": "error_generic"}
        return

    for r in search_results:
        r["tier"] = classify_tier(r["url"])

    yield {"type": "progress", "step": 2, "message": "step_2"}

    urls = [r["url"] for r in search_results]
    fetched = await fetch_all(urls)

    fetched_map = {f["url"]: f["markdown"] for f in fetched}
    for r in search_results:
        r["markdown"] = fetched_map.get(r["url"], "")

    sources_with_content = [r for r in search_results if r.get("markdown")]
    if len(sources_with_content) < 2:
        sources_with_content = search_results

    yield {"type": "progress", "step": 3, "message": "step_3"}

    try:
        result = await verify_claim(claim, sources_with_content, language)
        yield {"type": "result", "data": result}
    except Exception as e:
        yield {"type": "error", "message": "error_generic"}
```

**Step 4: Run tests**

```bash
pytest tests/test_pipeline.py -v
```
Expected: 2 PASSED

**Step 5: Run all tests**

```bash
pytest tests/ -v
```
Expected: All PASSED

**Step 6: Commit**

```bash
git add services/pipeline.py tests/test_pipeline.py
git commit -m "feat: add pipeline orchestrator with SSE event emission"
```

---

## Task 8: FastAPI Routes

**Files:**
- Modify: `main.py`
- Create: `tests/test_routes.py`

**Step 1: Write failing test**

```python
# tests/test_routes.py
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_home_returns_200():
    from main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/")
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_verify_text_returns_task_id():
    from main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/verify", data={"text": "CPF age raised", "language": "en"})
    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
```

**Step 2: Run to verify failure**

```bash
pytest tests/test_routes.py::test_verify_text_returns_task_id -v
```
Expected: FAIL (route not implemented)

**Step 3: Implement main.py fully**

```python
import asyncio
import json
import uuid
from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sse_starlette.sse import EventSourceResponse
from pathlib import Path

from services.ocr import extract_text_from_image
from services.pipeline import run_pipeline

app = FastAPI(title="Fact Verifier SG")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# In-memory task store: task_id -> asyncio.Queue
_task_queues: dict[str, asyncio.Queue] = {}

def _load_i18n() -> dict:
    i18n = {}
    for lang in ("en", "zh", "ms", "ta"):
        path = Path(f"i18n/{lang}.json")
        if path.exists():
            i18n[lang] = json.loads(path.read_text())
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
                event = await asyncio.wait_for(queue.get(), timeout=90)
                if event is None:
                    break
                yield {"event": event["type"], "data": json.dumps(event)}
        except asyncio.TimeoutError:
            yield {"event": "error", "data": json.dumps({"message": "error_generic"})}
        finally:
            _task_queues.pop(task_id, None)

    return EventSourceResponse(event_generator())
```

**Step 4: Run tests**

```bash
pytest tests/test_routes.py -v
```
Expected: 2 PASSED

**Step 5: Commit**

```bash
git add main.py tests/test_routes.py
git commit -m "feat: add FastAPI routes for verify and SSE stream"
```

---

## Task 9: Frontend — index.html

**Files:**
- Create: `templates/index.html`

**Step 1: Create templates/index.html**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title id="page-title">Fact Verifier SG</title>
  <link rel="stylesheet" href="/static/style.css" />
</head>
<body>
  <!-- i18n data injected from server -->
  <script id="i18n-data" type="application/json">{{ i18n | tojson }}</script>

  <header>
    <div class="lang-switcher">
      <button class="lang-btn active" data-lang="en">EN</button>
      <button class="lang-btn" data-lang="zh">中文</button>
      <button class="lang-btn" data-lang="ms">BM</button>
      <button class="lang-btn" data-lang="ta">தமிழ்</button>
    </div>
  </header>

  <main>
    <!-- State 1: Input -->
    <section id="state-input">
      <h1 id="app-title"></h1>
      <p id="app-subtitle"></p>

      <form id="verify-form" enctype="multipart/form-data">
        <textarea id="claim-input" name="text" rows="5" maxlength="2000"></textarea>

        <div class="upload-area" id="upload-area">
          <label for="image-input" id="upload-label"></label>
          <input type="file" id="image-input" name="image" accept="image/png,image/jpeg,image/webp" hidden />
          <div id="preview-container" hidden>
            <img id="image-preview" src="" alt="preview" />
            <button type="button" id="clear-image">✕</button>
          </div>
        </div>

        <input type="hidden" name="language" id="language-input" value="en" />
        <button type="submit" id="submit-btn" class="btn-primary"></button>
        <p id="form-error" class="error-msg" hidden></p>
      </form>
    </section>

    <!-- State 2: Loading -->
    <section id="state-loading" hidden>
      <div class="steps-container">
        <div class="step" id="step-1"><span class="step-icon">○</span><span class="step-label" id="step-1-label"></span></div>
        <div class="step" id="step-2"><span class="step-icon">○</span><span class="step-label" id="step-2-label"></span></div>
        <div class="step" id="step-3"><span class="step-icon">○</span><span class="step-label" id="step-3-label"></span></div>
      </div>
      <p id="checking-message"></p>
    </section>

    <!-- State 3: Result -->
    <section id="state-result" hidden>
      <div id="verdict-badge" class="verdict-badge"></div>
      <p id="result-summary" class="result-summary"></p>
      <p id="result-explanation" class="result-explanation"></p>

      <h2 id="sources-title"></h2>
      <div id="sources-list"></div>

      <button id="reset-btn" class="btn-secondary"></button>
    </section>

    <!-- State 4: Error -->
    <section id="state-error" hidden>
      <p id="error-message" class="error-msg"></p>
      <button id="error-reset-btn" class="btn-secondary"></button>
    </section>
  </main>

  <script src="/static/app.js"></script>
</body>
</html>
```

**Step 2: Commit**

```bash
git add templates/index.html
git commit -m "feat: add Jinja2 HTML template with 4 UI states"
```

---

## Task 10: Frontend — CSS

**Files:**
- Create: `static/style.css`

**Step 1: Create static/style.css**

```css
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --green: #16a34a;
  --red: #dc2626;
  --yellow: #d97706;
  --gov-color: #1d4ed8;
  --news-color: #7c3aed;
  --other-color: #64748b;
  --bg: #f8fafc;
  --card-bg: #ffffff;
  --text: #1e293b;
  --muted: #64748b;
  --border: #e2e8f0;
  --radius: 12px;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 18px;
  background: var(--bg);
  color: var(--text);
  min-height: 100vh;
}

header {
  display: flex;
  justify-content: flex-end;
  padding: 16px 24px;
  background: var(--card-bg);
  border-bottom: 1px solid var(--border);
}

main {
  max-width: 720px;
  margin: 0 auto;
  padding: 32px 24px;
}

/* Language switcher */
.lang-switcher { display: flex; gap: 8px; }
.lang-btn {
  padding: 6px 14px;
  border: 1px solid var(--border);
  border-radius: 20px;
  background: none;
  cursor: pointer;
  font-size: 15px;
  color: var(--muted);
}
.lang-btn.active {
  background: var(--text);
  color: white;
  border-color: var(--text);
}

/* Input state */
h1 { font-size: 28px; font-weight: 700; margin-bottom: 8px; }
p { line-height: 1.6; color: var(--muted); margin-bottom: 24px; }

textarea {
  width: 100%;
  padding: 16px;
  border: 2px solid var(--border);
  border-radius: var(--radius);
  font-size: 18px;
  resize: vertical;
  font-family: inherit;
  margin-bottom: 16px;
  transition: border-color 0.2s;
}
textarea:focus { outline: none; border-color: var(--text); }

.upload-area {
  border: 2px dashed var(--border);
  border-radius: var(--radius);
  padding: 20px;
  text-align: center;
  cursor: pointer;
  margin-bottom: 24px;
  transition: border-color 0.2s;
}
.upload-area:hover { border-color: var(--text); }
.upload-area label { cursor: pointer; color: var(--muted); font-size: 16px; }

#preview-container { position: relative; display: inline-block; }
#image-preview { max-height: 160px; border-radius: 8px; }
#clear-image {
  position: absolute; top: -8px; right: -8px;
  background: var(--red); color: white;
  border: none; border-radius: 50%;
  width: 24px; height: 24px; cursor: pointer; font-size: 12px;
}

.btn-primary {
  width: 100%;
  padding: 18px;
  background: var(--text);
  color: white;
  border: none;
  border-radius: var(--radius);
  font-size: 20px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s;
}
.btn-primary:hover { opacity: 0.85; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-secondary {
  padding: 14px 28px;
  background: none;
  color: var(--text);
  border: 2px solid var(--border);
  border-radius: var(--radius);
  font-size: 18px;
  cursor: pointer;
  margin-top: 24px;
}

.error-msg { color: var(--red); font-size: 15px; margin-top: 8px; }

/* Loading state */
.steps-container { display: flex; flex-direction: column; gap: 20px; margin: 40px 0; }
.step { display: flex; align-items: center; gap: 16px; font-size: 20px; }
.step-icon { font-size: 24px; width: 32px; text-align: center; }
.step.done .step-icon { color: var(--green); }
.step.active .step-icon { animation: spin 1s linear infinite; display: inline-block; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

/* Result state */
.verdict-badge {
  display: inline-block;
  padding: 12px 28px;
  border-radius: 40px;
  font-size: 22px;
  font-weight: 700;
  margin-bottom: 24px;
  letter-spacing: 1px;
}
.verdict-verified { background: #dcfce7; color: var(--green); }
.verdict-false { background: #fee2e2; color: var(--red); }
.verdict-unverified { background: #fef9c3; color: var(--yellow); }

.result-summary { font-size: 20px; font-weight: 600; color: var(--text); margin-bottom: 16px; }
.result-explanation { font-size: 17px; color: var(--muted); margin-bottom: 32px; }

h2 { font-size: 20px; font-weight: 600; margin-bottom: 16px; }

/* Source cards */
.source-card {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 18px;
  margin-bottom: 12px;
}
.source-header { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; flex-wrap: wrap; }
.tier-badge {
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 600;
  color: white;
}
.tier-government { background: var(--gov-color); }
.tier-news { background: var(--news-color); }
.tier-other { background: var(--other-color); }
.stance-tag {
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 13px;
  border: 1px solid var(--border);
  color: var(--muted);
}
.stance-supports { border-color: var(--green); color: var(--green); }
.stance-contradicts { border-color: var(--red); color: var(--red); }

.source-title { font-weight: 600; font-size: 16px; margin-bottom: 4px; }
.source-url { font-size: 13px; color: var(--muted); word-break: break-all; margin-bottom: 8px; }
.source-snippet { font-size: 15px; color: var(--muted); line-height: 1.5; }
```

**Step 2: Commit**

```bash
git add static/style.css
git commit -m "feat: add CSS with accessible high-contrast design for medium-age users"
```

---

## Task 11: Frontend — JavaScript

**Files:**
- Create: `static/app.js`

**Step 1: Create static/app.js**

```javascript
const I18N = JSON.parse(document.getElementById('i18n-data').textContent);
let currentLang = 'en';

function t(key) {
  return (I18N[currentLang] && I18N[currentLang][key]) || I18N['en'][key] || key;
}

function setLang(lang) {
  currentLang = lang;
  document.getElementById('language-input').value = lang;

  document.querySelectorAll('.lang-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.lang === lang);
  });

  // Update all translatable text
  document.getElementById('app-title').textContent = t('app_title');
  document.getElementById('app-subtitle').textContent = t('app_subtitle');
  document.getElementById('claim-input').placeholder = t('input_placeholder');
  document.getElementById('upload-label').textContent = t('upload_label');
  document.getElementById('submit-btn').textContent = t('submit_button');
  document.getElementById('checking-message').textContent = t('checking_message');
  document.getElementById('step-1-label').textContent = t('step_1');
  document.getElementById('step-2-label').textContent = t('step_2');
  document.getElementById('step-3-label').textContent = t('step_3');
  document.getElementById('reset-btn').textContent = t('reset_button');
  document.getElementById('error-reset-btn').textContent = t('reset_button');
}

// Language switcher
document.querySelectorAll('.lang-btn').forEach(btn => {
  btn.addEventListener('click', () => setLang(btn.dataset.lang));
});

// Image upload
const uploadArea = document.getElementById('upload-area');
const imageInput = document.getElementById('image-input');
const previewContainer = document.getElementById('preview-container');
const imagePreview = document.getElementById('image-preview');

uploadArea.addEventListener('click', () => imageInput.click());
uploadArea.addEventListener('dragover', e => { e.preventDefault(); uploadArea.style.borderColor = '#1e293b'; });
uploadArea.addEventListener('dragleave', () => { uploadArea.style.borderColor = ''; });
uploadArea.addEventListener('drop', e => {
  e.preventDefault();
  const file = e.dataTransfer.files[0];
  if (file) handleImageFile(file);
});

imageInput.addEventListener('change', () => {
  if (imageInput.files[0]) handleImageFile(imageInput.files[0]);
});

function handleImageFile(file) {
  const reader = new FileReader();
  reader.onload = e => {
    imagePreview.src = e.target.result;
    previewContainer.hidden = false;
    document.getElementById('upload-label').hidden = true;
  };
  reader.readAsDataURL(file);
}

document.getElementById('clear-image').addEventListener('click', e => {
  e.stopPropagation();
  imageInput.value = '';
  previewContainer.hidden = true;
  document.getElementById('upload-label').hidden = false;
});

// State management
function showState(name) {
  ['input', 'loading', 'result', 'error'].forEach(s => {
    document.getElementById(`state-${s}`).hidden = s !== name;
  });
}

function setStep(active) {
  for (let i = 1; i <= 3; i++) {
    const el = document.getElementById(`step-${i}`);
    el.classList.remove('done', 'active');
    if (i < active) el.querySelector('.step-icon').textContent = '✅';
    else if (i === active) {
      el.querySelector('.step-icon').textContent = '⏳';
      el.classList.add('active');
    } else {
      el.querySelector('.step-icon').textContent = '○';
    }
  }
}

function renderResult(data) {
  const badge = document.getElementById('verdict-badge');
  badge.className = 'verdict-badge';
  const verdictKey = `verdict_${data.verdict}`;
  badge.textContent = t(verdictKey);
  badge.classList.add(`verdict-${data.verdict}`);

  document.getElementById('result-summary').textContent = data.summary || '';
  document.getElementById('result-explanation').textContent = data.explanation || '';
  document.getElementById('sources-title').textContent = t('sources_title');

  const list = document.getElementById('sources-list');
  list.innerHTML = '';
  (data.sources || []).forEach(source => {
    const card = document.createElement('div');
    card.className = 'source-card';
    const tierLabel = t(`tier_${source.tier}`) || source.tier;
    const stanceLabel = t(`stance_${source.stance}`) || source.stance;
    card.innerHTML = `
      <div class="source-header">
        <span class="tier-badge tier-${source.tier}">${tierLabel}</span>
        <span class="stance-tag stance-${source.stance}">${stanceLabel}</span>
      </div>
      <div class="source-title">${escHtml(source.title || '')}</div>
      <div class="source-url"><a href="${escHtml(source.url)}" target="_blank" rel="noopener">${escHtml(source.url)}</a></div>
      <div class="source-snippet">${escHtml(source.snippet || '')}</div>
    `;
    list.appendChild(card);
  });
}

function escHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// Form submission
document.getElementById('verify-form').addEventListener('submit', async e => {
  e.preventDefault();
  const errorEl = document.getElementById('form-error');
  errorEl.hidden = true;

  const text = document.getElementById('claim-input').value.trim();
  const hasImage = imageInput.files.length > 0;
  if (!text && !hasImage) {
    errorEl.textContent = t('error_empty');
    errorEl.hidden = false;
    return;
  }

  const formData = new FormData(e.target);
  showState('loading');
  setStep(1);

  let taskId;
  try {
    const res = await fetch('/verify', { method: 'POST', body: formData });
    const json = await res.json();
    if (json.error) throw new Error(json.error);
    taskId = json.task_id;
  } catch {
    showState('error');
    document.getElementById('error-message').textContent = t('error_generic');
    return;
  }

  const es = new EventSource(`/stream/${taskId}`);

  es.addEventListener('progress', e => {
    const data = JSON.parse(e.data);
    setStep(data.step);
  });

  es.addEventListener('result', e => {
    es.close();
    const data = JSON.parse(e.data);
    renderResult(data.data || data);
    showState('result');
  });

  es.addEventListener('error', e => {
    es.close();
    let msg = t('error_generic');
    try { msg = t(JSON.parse(e.data).message) || msg; } catch {}
    document.getElementById('error-message').textContent = msg;
    showState('error');
  });
});

// Reset buttons
document.getElementById('reset-btn').addEventListener('click', () => showState('input'));
document.getElementById('error-reset-btn').addEventListener('click', () => showState('input'));

// Init
setLang('en');
```

**Step 2: Commit**

```bash
git add static/app.js
git commit -m "feat: add vanilla JS frontend with SSE, multilingual, image upload"
```

---

## Task 12: End-to-End Smoke Test

**Step 1: Copy .env and fill in real API keys**

```bash
cp .env.example .env
# Edit .env and fill BRAVE_API_KEY and OPENAI_API_KEY
```

**Step 2: Run the server**

```bash
uvicorn main:app --reload
```

**Step 3: Open browser**

Navigate to `http://127.0.0.1:8000`

**Step 4: Test text input**
- Type: "The CPF withdrawal age has been raised to 70"
- Click "Check Fact"
- Verify step-by-step progress appears
- Verify verdict + sources are displayed

**Step 5: Test image upload**
- Take a screenshot of a WhatsApp message
- Upload it via the upload area
- Verify text is extracted and fact-checked

**Step 6: Test language switching**
- Switch to 中文 before submitting
- Verify UI labels change
- Verify result is in Chinese

**Step 7: Final commit**

```bash
git add .
git commit -m "feat: complete fact verifier MVP"
```
