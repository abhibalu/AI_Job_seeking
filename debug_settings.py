from backend.settings import settings
print(f"Base URL: '{settings.OPENROUTER_BASE_URL}'")
print(f"Computed URL: '{settings.OPENROUTER_BASE_URL}/chat/completions' if not ends with ...")
url = settings.OPENROUTER_BASE_URL if settings.OPENROUTER_BASE_URL.endswith("/chat/completions") else f"{settings.OPENROUTER_BASE_URL}/chat/completions"
print(f"Final URL: '{url}'")
