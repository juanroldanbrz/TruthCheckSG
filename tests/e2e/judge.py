from pydantic import BaseModel
from openai import OpenAI


class UIJudgement(BaseModel):
    passed: bool
    reason: str


def llm_judge(prompt: str) -> UIJudgement:
    client = OpenAI()
    response = client.beta.chat.completions.parse(
        model="gpt-5-mini-2025-08-07",
        messages=[{"role": "user", "content": prompt}],
        response_format=UIJudgement,
    )
    return response.choices[0].message.parsed