import base64
from pydantic import BaseModel
from openai import AsyncOpenAI, RateLimitError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from fact_verifier.config import settings

client = AsyncOpenAI(api_key=settings.openai_api_key)


class ImageAnalysis(BaseModel):
    ocr_text: str
    intent: str


@retry(
    retry=retry_if_exception_type(RateLimitError),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    stop=stop_after_attempt(5),
    reraise=True,
)
async def analyze_image(image_bytes: bytes, content_type: str) -> ImageAnalysis | None:
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    try:
        response = await client.beta.chat.completions.parse(
            model="gpt-5-mini-2025-08-07",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Analyze this image and return two things:\n"
                                "1. ocr_text: All visible text in the image, exactly as written. "
                                "Return an empty string if there is no readable text.\n"
                                "2. intent: The actual purpose or goal of this image — what it is "
                                "trying to make the viewer believe, do, or buy. "
                                "Be specific about any promotional, misleading, or persuasive intent. "
                                "If the image is neutral (e.g. a news screenshot), state that plainly."
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{content_type};base64,{b64}"},
                        },
                    ],
                }
            ],
            response_format=ImageAnalysis,
            max_completion_tokens=settings.max_output_tokens,
        )
        if not response.choices:
            return None
        return response.choices[0].message.parsed
    except RateLimitError:
        raise
    except Exception:
        return None