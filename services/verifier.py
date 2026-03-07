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
    # Strip markdown code fences if GPT wraps the JSON despite being told not to
    if content.startswith("```"):
        content = content.split("```", 2)[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()
    return json.loads(content)
