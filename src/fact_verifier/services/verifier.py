from datetime import datetime, timezone
from openai import AsyncOpenAI
from fact_verifier.config import settings

client = AsyncOpenAI(api_key=settings.openai_api_key)

SYSTEM_PROMPT = """You are a fact-checking assistant for Singapore.
You will receive a claim and a list of sources with their content.
Respond ONLY in {language}.
Analyse the sources and produce a structured fact-check result.
Sort sources: government first, then news, then other."""

VERIFY_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "fact_check_result",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "verdict": {"type": "string", "enum": ["verified", "false", "unverified"]},
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
1. Whether it is a verifiable factual claim (a statement asserting something is true)
2. If yes, generate an optimised web search query to find evidence for or against it

NOT a verifiable claim: questions ("how do I..."), recipes, opinions, greetings, nonsense.
IS a verifiable claim: statements asserting facts ("X is Y", "X happened", "X costs Y")

Always write search_query in English, regardless of the language of the input."""

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


async def parse_claim(claim: str) -> dict:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    system = f"{PARSE_CLAIM_PROMPT}\n\nCurrent timestamp: {now}"
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": claim},
        ],
        max_tokens=200,
        temperature=0,
        response_format=PARSE_CLAIM_SCHEMA,
    )
    if not response.choices:
        raise ValueError("OpenAI returned empty choices list")
    import json
    return json.loads(response.choices[0].message.content)


async def verify_claim(claim: str, sources: list[dict], language: str = "en") -> dict:
    lang_name = LANGUAGE_NAMES.get(language, "English")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    system = SYSTEM_PROMPT.format(language=lang_name) + f"\n\nCurrent timestamp: {now}"
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
        response_format=VERIFY_SCHEMA,
    )
    if not response.choices:
        raise ValueError("OpenAI returned empty choices list")
    import json
    return json.loads(response.choices[0].message.content)
