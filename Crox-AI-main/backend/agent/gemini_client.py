import json
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from config import get_settings

T = TypeVar("T", bound=BaseModel)

_MAX_RETRIES = 2


class GeminiNotConfigured(RuntimeError):
    pass


def _client():
    settings = get_settings()
    if not settings.gemini_api_key:
        raise GeminiNotConfigured("GEMINI_API_KEY is not set in .env")

    from google import genai

    return genai.Client(api_key=settings.gemini_api_key)


async def generate_structured(prompt: str, response_model: type[T]) -> T:
    """Calls Gemini asking for JSON matching response_model's schema, validates
    the result with Pydantic, and retries with the validation error fed back
    into the prompt if it doesn't parse. Never returns unvalidated output.
    """
    settings = get_settings()
    client = _client()
    schema = response_model.model_json_schema()
    full_prompt = (
        f"{prompt}\n\n"
        f"Respond with ONLY a single JSON object matching this JSON schema:\n"
        f"{json.dumps(schema)}"
    )

    last_error: Exception | None = None
    for attempt in range(_MAX_RETRIES + 1):
        response = await client.aio.models.generate_content(
            model=settings.gemini_model,
            contents=full_prompt,
            config={"response_mime_type": "application/json"},
        )
        raw = response.text
        try:
            data = json.loads(raw)
            return response_model(**data)
        except (json.JSONDecodeError, ValidationError, TypeError) as exc:
            last_error = exc
            full_prompt = (
                f"{prompt}\n\n"
                f"Your previous response was invalid JSON for this schema: {json.dumps(schema)}\n"
                f"Previous response:\n{raw}\n"
                f"Validation error: {exc}\n"
                f"Respond again with ONLY a corrected JSON object."
            )
    raise ValueError(f"Gemini did not return valid {response_model.__name__} after retries: {last_error}")


async def extract_structured_fields(resume_text: str) -> dict:
    from pydantic import BaseModel as _BM

    class ResumeFields(_BM):
        name: str = ""
        email: str = ""
        phone: str = ""
        college: str = ""
        skills: list[str] = []

    result = await generate_structured(
        f"Extract candidate fields from this resume text:\n\n{resume_text}",
        ResumeFields,
    )
    return result.model_dump()
