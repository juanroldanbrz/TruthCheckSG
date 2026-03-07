import os
from datetime import datetime, timezone
from fact_verifier.config import settings

if settings.langfuse_secret_key and settings.langfuse_public_key:
    os.environ.setdefault("LANGFUSE_SECRET_KEY", settings.langfuse_secret_key)
    os.environ.setdefault("LANGFUSE_PUBLIC_KEY", settings.langfuse_public_key)
    os.environ.setdefault("LANGFUSE_HOST", settings.langfuse_host)
    try:
        from langfuse.openai import AsyncOpenAI
    except Exception:
        from openai import AsyncOpenAI
else:
    from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=settings.openai_api_key)

SYSTEM_PROMPT = """You are a fact-checking assistant for Singapore.
You will receive a claim and a list of sources with their content.
Respond ONLY in {language}.
Analyse the sources and produce a structured fact-check result.
Sort sources: government first, then news, then other.

Use the following five-tier verdict scale:
- true: The claim is correct. Reliable sources confirm this.
- likely_true: Mostly correct but small details may be unclear. Most evidence supports this claim.
- unverified: Not enough information to confirm or deny. Cannot determine if true or false yet.
- likely_false: Evidence suggests it is probably wrong. Most reliable sources say this is not correct.
- false: The claim is incorrect. Reliable sources show this claim is not true."""

VERIFY_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "fact_check_result",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "verdict": {"type": "string", "enum": ["true", "likely_true", "likely_false", "false", "unverified"]},
                "summary": {"type": "string"},
                "explanation": {"type": "string"},
                "sources": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string"},
                            "title": {"type": "string"},
                            "tier": {"type": "string", "enum": ["government", "news", "other"]},
                            "credibility_label": {"type": "string"},
                            "stance": {"type": "string", "enum": ["supports", "contradicts", "neutral"]},
                            "snippet": {"type": "string"},
                        },
                        "required": ["url", "title", "tier", "credibility_label", "stance", "snippet"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["verdict", "summary", "explanation", "sources"],
            "additionalProperties": False,
        },
    },
}

PARSE_CLAIM_PROMPT = """You are a pre-processing agent for a fact-checking system.

Given a user input, determine:
1. Whether it is a verifiable factual claim or an investigative question about provided content
2. If yes, generate an optimised web search query to find evidence for or against it

NOT relevant: generic questions ("how do I..."), recipes, greetings, nonsense with no image context.
IS relevant: statements asserting facts ("X is Y", "X happened") OR questions about an uploaded image
  (e.g. "is this a scam?", "is this investment legitimate?", "is this real?") — the image provides
  the factual content being investigated.

When an image is provided alongside a question, treat the combination as a verifiable investigation.
Always write search_query in {language}."""

PARSE_CLAIM_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "claim_parse_result",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "is_relevant": {"type": "boolean"},
                "search_query": {"type": "string"},
            },
            "required": ["is_relevant", "search_query"],
            "additionalProperties": False,
        },
    },
}

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


def _strip_fenced_json(content: str) -> str:
    content = content.strip()
    if content.startswith("```"):
        lines = content.splitlines()
        return "\n".join(lines[1:-1]).strip()
    return content


def _build_user_content(text: str, image_bytes: bytes | None, image_content_type: str | None) -> str | list:
    if not image_bytes or not image_content_type:
        return text
    import base64
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    return [
        {"type": "text", "text": text},
        {"type": "image_url", "image_url": {"url": f"data:{image_content_type};base64,{b64}"}},
    ]


async def parse_claim(
    claim: str,
    language: str = "en",
    image_bytes: bytes | None = None,
    image_content_type: str | None = None,
) -> dict:
    lang_name = LANGUAGE_NAMES.get(language, "English")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    system = PARSE_CLAIM_PROMPT.format(language=lang_name) + f"\n\nCurrent timestamp: {now}"
    user_content = _build_user_content(claim, image_bytes, image_content_type)
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ],
        max_tokens=200,
        temperature=0,
        response_format=PARSE_CLAIM_SCHEMA,
    )
    if not response.choices:
        raise ValueError("OpenAI returned empty choices list")
    import json
    return json.loads(_strip_fenced_json(response.choices[0].message.content))


async def verify_claim(
    claim: str,
    sources: list[dict],
    language: str = "en",
    image_bytes: bytes | None = None,
    image_content_type: str | None = None,
) -> dict:
    lang_name = LANGUAGE_NAMES.get(language, "English")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    system = SYSTEM_PROMPT.format(language=lang_name) + f"\n\nCurrent timestamp: {now}"
    sources_text = _build_sources_text(sources)
    text_content = f"Claim to verify: {claim}\n\nSources:\n{sources_text}"
    user_content = _build_user_content(text_content, image_bytes, image_content_type)

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ],
        max_tokens=2000,
        temperature=0.1,
        response_format=VERIFY_SCHEMA,
    )
    if not response.choices:
        raise ValueError("OpenAI returned empty choices list")
    import json
    return json.loads(_strip_fenced_json(response.choices[0].message.content))
