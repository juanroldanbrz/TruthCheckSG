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
