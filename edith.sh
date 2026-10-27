#!/bin/bash

# Navigate to EDITH directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Load optional .env if present
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Default to Ollama unless specified
if [ "$1" == "gpt" ]; then
    echo "🧠 Booting EDITH with ChatGPT (GPT-4o)..."
    export EDITH_AI_PROVIDER="cloud"
    export EDITH_CLOUD_KEY="${EDITH_OPENAI_KEY:-your-openai-api-key}"
    export EDITH_CLOUD_URL="https://api.openai.com/v1/chat/completions"
    export EDITH_CLOUD_MODEL="gpt-4o"

elif [ "$1" == "groq" ]; then
    echo "🧠 Booting EDITH with Groq (Llama-3)..."
    export EDITH_AI_PROVIDER="cloud"
    export EDITH_CLOUD_KEY="${EDITH_GROQ_KEY:-your-groq-api-key}"
    export EDITH_CLOUD_URL="https://api.groq.com/openai/v1/chat/completions"
    export EDITH_CLOUD_MODEL="llama-3.3-70b-versatile"

else
    echo "🧠 Booting EDITH with Local Ollama..."
    export EDITH_AI_PROVIDER="ollama"
fi

# Launch EDITH
python src/app.py
