import os

os.environ.setdefault("APP_KEY", "dev-app-key")
os.environ.setdefault("SEARCH_PROVIDER", "mock")
os.environ.setdefault("LLM_MODEL", "none")
os.environ.setdefault("CACHE_DIR", "./.cache-test")
