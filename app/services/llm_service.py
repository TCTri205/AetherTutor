from openai import AsyncOpenAI
from typing import Optional, List, Dict, Any, Type
import json
import logging
import asyncio
import random
from pydantic import BaseModel, ValidationError
from ..config import settings
from ..constants import (
    LLM_TEMPERATURE_CHAT, LLM_TEMPERATURE_EXTRACTION,
    LLM_MAX_RETRIES
)

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        # Use explicit base_url or OLLAMA_BASE_URL if no valid OpenAI key provided
        self.is_openai = api_key and not api_key.startswith("your_")
        if not self.is_openai and settings.OPENAI_API_KEY:
             self.is_openai = not settings.OPENAI_API_KEY.startswith("your_")

        target_base_url = base_url or (None if self.is_openai else settings.OLLAMA_BASE_URL)
        target_api_key = api_key or settings.OPENAI_API_KEY or "ollama"
        if not target_api_key or target_api_key.startswith("your_"):
            target_api_key = "ollama"

        self.client = AsyncOpenAI(
            api_key=target_api_key,
            base_url=target_base_url
        )

    async def health_check(self) -> bool:
        """
        Check if LLM service is reachable.
        """
        try:
            # Simple list models call or a very cheap completion
            await self.client.models.list()
            return True
        except Exception as e:
            logger.error(f"LLM Health Check failed: {e}")
            return False

    async def get_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = settings.DEFAULT_LLM_MODEL,
        temperature: float = LLM_TEMPERATURE_CHAT,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> Any:
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream
        )
        return response

    async def stream_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = settings.DEFAULT_LLM_MODEL,
        temperature: float = LLM_TEMPERATURE_CHAT,
        max_tokens: Optional[int] = None,
    ):
        """
        Helper for streaming completions.
        """
        return await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True
        )

    async def structured_extraction(
        self,
        prompt: str,
        response_model: Type[BaseModel],
        model: str = settings.DEFAULT_LLM_MODEL,
        max_retries: int = LLM_MAX_RETRIES
    ) -> Optional[BaseModel]:
        """
        Calls the LLM with a prompt and enforces JSON format.
        Uses exponential backoff with jitter for retries.
        """
        for attempt in range(max_retries):
            try:
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that outputs JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=LLM_TEMPERATURE_EXTRACTION
                )
                
                raw_content = response.choices[0].message.content
                if not raw_content:
                    continue
                
                data = json.loads(raw_content)
                return response_model.model_validate(data)
                
            except (json.JSONDecodeError, ValueError, ValidationError) as e:
                logger.warning(f"Extraction attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    return None
                
                # Exponential backoff with jitter
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                logger.info(f"Retrying in {wait_time:.2f} seconds...")
                await asyncio.sleep(wait_time)
                
            except Exception as e:
                logger.error(f"Unexpected error during extraction: {e}")
                return None
        
        return None

llm_service = LLMService()
