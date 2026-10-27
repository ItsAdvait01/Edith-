import json
import base64
import urllib.request
import ssl
import certifi
from cnfig.settings import (
    ACTIVE_PROVIDER,
    OLLAMA_URL,
    OLLAMA_MODEL,
    CLOUD_API_URL,
    CLOUD_API_KEY,
    CLOUD_MODEL,
    REQUEST_TIMEOUT,
    STREAM
)


class LLM:
    """Universal LLM Adapter for both local Ollama and Cloud APIs."""

    def __init__(self, provider=None):
        self.provider = provider or ACTIVE_PROVIDER
        self.ssl_context = ssl.create_default_context(cafile=certifi.where())

    def _build_request(self, messages, stream=False):
        if self.provider == "cloud":
            payload = {
                "model": CLOUD_MODEL,
                "messages": messages,
                "stream": stream
            }
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {CLOUD_API_KEY}",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json"
            }
            url = CLOUD_API_URL
        else:
            payload = {
                "model": OLLAMA_MODEL,
                "messages": messages,
                "stream": stream
            }
            headers = {"Content-Type": "application/json"}
            url = OLLAMA_URL
            
        data = json.dumps(payload).encode("utf-8")
        return urllib.request.Request(url, data=data, headers=headers)

    def ask_sync(self, messages):
        """Non-streaming request, returns full text silently. Used by AI Planner."""
        request = self._build_request(messages, stream=False)
        
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT, context=self.ssl_context) as response:
                body = json.loads(response.read().decode("utf-8"))
                
                if self.provider == "cloud":
                    return body.get("choices", [{}])[0].get("message", {}).get("content", "")
                else:
                    return body.get("message", {}).get("content", "")
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = f": {e.read().decode('utf-8', errors='replace')}"
            except Exception:
                pass
            return f"Cloud API Error: {e.code} {e.reason}{detail}"
        except Exception as e:
            return f"Connection Error: {str(e)}"

    def ask_stream(self, messages):
        """Streaming request, prints to stdout. Used by Chat."""
        request = self._build_request(messages, stream=True)
        response_text = ""
        
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT, context=self.ssl_context) as response:
                for line in response:
                    if not line:
                        continue
                        
                    decoded = line.decode("utf-8").strip()
                    if not decoded:
                        continue

                    if self.provider == "cloud":
                        # OpenAI SSE format (data: {...})
                        if decoded.startswith("data: "):
                            data_str = decoded[6:]
                            if data_str == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data_str)
                                text = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                if text:
                                    print(text, end="", flush=True)
                                    response_text += text
                            except json.JSONDecodeError:
                                pass
                    else:
                        # Ollama JSON stream format
                        try:
                            chunk = json.loads(decoded)
                            if "message" in chunk:
                                text = chunk["message"].get("content", "")
                                if text:
                                    print(text, end="", flush=True)
                                    response_text += text
                        except json.JSONDecodeError:
                            pass
                            
            print()
            return response_text
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                raw_body = e.read().decode('utf-8', errors='replace')
                body_json = json.loads(raw_body)
                detail = body_json.get("error", {}).get("message", raw_body)
            except Exception:
                pass
            error_msg = f"\n[EDITH SYSTEM ERROR] Cloud API rejected the request: HTTP {e.code} ({e.reason})."
            if detail:
                error_msg += f"\nDetails from provider: {detail}\n"
            else:
                error_msg += "\n(Please check your API key, model name, and provider limits.)\n"
            print(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"\n[EDITH SYSTEM ERROR] Connection failed: {str(e)}\n"
            print(error_msg)
            return error_msg

    def ask_vision(self, prompt, image_path):
        """Send an image + text prompt to the vision model. Returns analysis as plain text.
        
        Supports both Ollama (images list in messages) and cloud (OpenAI vision content array).
        """
        try:
            with open(image_path, "rb") as f:
                image_b64 = base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            return f"Vision Error: Could not read image — {e}"

        try:
            if self.provider == "cloud":
                # OpenAI vision format: content is an array with text + image_url
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_b64}",
                                    "detail": "high",
                                },
                            },
                        ],
                    }
                ]
                payload = {"model": CLOUD_MODEL, "messages": messages, "stream": False}
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {CLOUD_API_KEY}",
                }
                url = CLOUD_API_URL
            else:
                # Ollama vision format: images list alongside normal messages
                messages = [{"role": "user", "content": prompt, "images": [image_b64]}]
                payload = {"model": OLLAMA_MODEL, "messages": messages, "stream": False}
                headers = {"Content-Type": "application/json"}
                url = OLLAMA_URL

            data = json.dumps(payload).encode("utf-8")
            request = urllib.request.Request(url, data=data, headers=headers)

            with urllib.request.urlopen(
                request, timeout=REQUEST_TIMEOUT, context=self.ssl_context
            ) as response:
                body = json.loads(response.read().decode("utf-8"))
                if self.provider == "cloud":
                    return body.get("choices", [{}])[0].get("message", {}).get("content", "")
                else:
                    return body.get("message", {}).get("content", "")

        except Exception as e:
            return f"Vision Error: {e}"

    def ask(self, messages):
        """Legacy alias, defaults to stream if settings.STREAM is True."""
        if STREAM:
            return self.ask_stream(messages)
        return self.ask_sync(messages)