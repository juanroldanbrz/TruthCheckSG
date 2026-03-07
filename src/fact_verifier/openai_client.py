import itertools
from fact_verifier.config import settings


def _get_async_openai_class():
    if settings.langfuse_secret_key and settings.langfuse_public_key:
        import os
        os.environ.setdefault("LANGFUSE_SECRET_KEY", settings.langfuse_secret_key)
        os.environ.setdefault("LANGFUSE_PUBLIC_KEY", settings.langfuse_public_key)
        os.environ.setdefault("LANGFUSE_HOST", settings.langfuse_host)
        try:
            from langfuse.openai import AsyncOpenAI
            return AsyncOpenAI
        except Exception:
            pass
    from openai import AsyncOpenAI
    return AsyncOpenAI


def _build_clients():
    AsyncOpenAI = _get_async_openai_class()
    keys = [k.strip() for k in settings.openai_keys.split(",") if k.strip()]
    return [AsyncOpenAI(api_key=key) for key in keys]


_clients = _build_clients()
_cycle = itertools.cycle(_clients)


def get_client():
    return next(_cycle)