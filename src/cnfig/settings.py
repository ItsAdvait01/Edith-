import os

# 'ollama' or 'cloud'
ACTIVE_PROVIDER = os.environ.get("EDITH_AI_PROVIDER", "ollama")

# Local Ollama Config
OLLAMA_URL = os.environ.get("EDITH_OLLAMA_URL", "http://127.0.0.1:11434/api/chat")
OLLAMA_MODEL = os.environ.get("EDITH_OLLAMA_MODEL", "gemma3:4b")

# Cloud API Config (OpenAI Compatible Standard)
CLOUD_API_URL = os.environ.get("EDITH_CLOUD_URL", "https://api.openai.com/v1/chat/completions")
CLOUD_API_KEY = os.environ.get("EDITH_CLOUD_KEY", "")
CLOUD_MODEL = os.environ.get("EDITH_CLOUD_MODEL", "gpt-4o")

REQUEST_TIMEOUT = int(os.environ.get("EDITH_REQUEST_TIMEOUT", 120))
STREAM = True