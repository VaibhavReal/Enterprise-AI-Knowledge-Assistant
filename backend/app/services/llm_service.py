from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import AsyncIterator
from openai import AsyncOpenAI
import anthropic
import httpx
import json

from app.core.config import get_settings

logger = logging.getLogger(__name__)

class BaseLLMProvider(ABC):
    """
    Abstract base for LLM providers.
    """
    
    @abstractmethod
    async def stream(self, messages: list[dict]) -> AsyncIterator[str]:
        """Stream tokens from the LLM. Yields string tokens."""
        pass
    
    @abstractmethod
    async def complete(self, messages: list[dict]) -> str:
        """Return full completion (for query rewriting, not main chat)."""
        pass


class GeminiProvider(BaseLLMProvider):
    """
    Google Gemini (Google AI Studio) Provider.
    Primary recommended LLM for high accuracy, low latency financial research.
    
    Supports:
    - gemini-2.5-flash (ultra-fast, accurate, high RPM limit)
    - gemini-1.5-flash
    - gemini-2.5-pro / gemini-1.5-pro
    """
    
    def __init__(self, api_key: str, model: str = "gemini-flash-lite-latest"):
        self.api_key = (api_key or "").strip()
        model_name = (model or "").strip()
        if not model_name or "2.5" in model_name or "1.5" in model_name or "2.0" in model_name:
            self.model = "gemini-flash-lite-latest"
        else:
            self.model = model_name
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"


    def _convert_messages(self, messages: list[dict]):
        """Convert standard message format to Gemini API format."""
        system_instruction = None
        contents = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                system_instruction = {"parts": [{"text": content}]}
            elif role == "assistant":
                contents.append({"role": "model", "parts": [{"text": content}]})
            else:
                contents.append({"role": "user", "parts": [{"text": content}]})
        return system_instruction, contents

    async def stream(self, messages: list[dict]) -> AsyncIterator[str]:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured in .env. Please add your Google AI Studio API key.")
        
        system_instruction, contents = self._convert_messages(messages)
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 4096,
            }
        }
        if system_instruction:
            payload["systemInstruction"] = system_instruction

        url = f"{self.base_url}/{self.model}:streamGenerateContent?alt=sse&key={self.api_key}"
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                if response.status_code != 200:
                    error_bytes = await response.aread()
                    error_msg = error_bytes.decode("utf-8", errors="ignore")
                    raise RuntimeError(f"Gemini API error ({response.status_code}): {error_msg}")
                
                async for line in response.aiter_lines():
                    line = line.strip()
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if not data_str:
                            continue
                        try:
                            data = json.loads(data_str)
                            candidates = data.get("candidates", [])
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts", [])
                                for part in parts:
                                    if "text" in part:
                                        yield part["text"]
                        except json.JSONDecodeError:
                            pass

    async def complete(self, messages: list[dict]) -> str:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured in .env.")
        
        system_instruction, contents = self._convert_messages(messages)
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 2048,
            }
        }
        if system_instruction:
            payload["systemInstruction"] = system_instruction

        url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(url, json=payload)
            if res.status_code != 200:
                raise RuntimeError(f"Gemini API error ({res.status_code}): {res.text}")
            data = res.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                return "".join(part.get("text", "") for part in parts)
            return ""


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI GPT-4o provider (secondary option).
    """
    
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.client = AsyncOpenAI(api_key=api_key, max_retries=0, timeout=3.0)
        self.model = model

    async def stream(self, messages: list[dict]) -> AsyncIterator[str]:
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
                timeout=5.0,
            )
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            raise e
    
    async def complete(self, messages: list[dict]) -> str:
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=False,
                timeout=5.0,
            )
            if response.choices and response.choices[0].message.content:
                return response.choices[0].message.content
            return ""
        except Exception as e:
            raise e


class ClaudeProvider(BaseLLMProvider):
    """
    Anthropic Claude Sonnet provider (third option).
    """
    
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20240620"):
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model
    
    async def stream(self, messages: list[dict]) -> AsyncIterator[str]:
        system = ""
        anthropic_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                anthropic_messages.append(msg)
                
        try:
            async with self.client.messages.stream(
                model=self.model,
                max_tokens=4096,
                system=system,
                messages=anthropic_messages,
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as e:
            raise e
    
    async def complete(self, messages: list[dict]) -> str:
        system = ""
        anthropic_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                anthropic_messages.append(msg)
                
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system,
                messages=anthropic_messages,
            )
            return response.content[0].text
        except Exception as e:
            raise e


class OllamaProvider(BaseLLMProvider):
    """
    Ollama local LLM provider (optional offline option).
    """
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3"):
        self.base_url = base_url
        self.model = model
    
    async def stream(self, messages: list[dict]) -> AsyncIterator[str]:
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST", 
                f"{self.base_url}/api/chat", 
                json={"model": self.model, "messages": messages, "stream": True}
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if "message" in data and "content" in data["message"]:
                                yield data["message"]["content"]
                        except json.JSONDecodeError:
                            pass
    
    async def complete(self, messages: list[dict]) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/chat", 
                json={"model": self.model, "messages": messages, "stream": False}
            )
            response.raise_for_status()
            data = response.json()
            if "message" in data and "content" in data["message"]:
                return data["message"]["content"]
            return ""


_llm_provider: BaseLLMProvider | None = None

def get_llm_provider() -> BaseLLMProvider:
    """
    Factory that returns the configured LLM provider singleton.
    Prioritizes Google Gemini / Google AI Studio as the first and primary option.
    """
    global _llm_provider
    if _llm_provider is None:
        settings = get_settings()
        provider = (settings.LLM_PROVIDER or "gemini").lower().strip()
        
        if provider == "gemini":
            _llm_provider = GeminiProvider(settings.GEMINI_API_KEY, settings.GEMINI_MODEL)
        elif provider == "openai":
            _llm_provider = OpenAIProvider(settings.OPENAI_API_KEY, settings.OPENAI_MODEL)
        elif provider == "claude":
            _llm_provider = ClaudeProvider(settings.ANTHROPIC_API_KEY, settings.ANTHROPIC_MODEL)
        elif provider == "ollama":
            _llm_provider = OllamaProvider(settings.OLLAMA_BASE_URL, settings.OLLAMA_MODEL)
        else:
            logger.info(f"Defaulting to GeminiProvider for provider '{provider}'")
            _llm_provider = GeminiProvider(settings.GEMINI_API_KEY, settings.GEMINI_MODEL)
            
    return _llm_provider
