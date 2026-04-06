from openai import AsyncOpenAI
from typing import Optional, List, Dict, Any
from ..config import settings

class LLMService:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        # Use explicit base_url or OLLAMA_BASE_URL if no OpenAI key provided
        target_base_url = base_url or (None if (api_key or settings.OPENAI_API_KEY) else settings.OLLAMA_BASE_URL)
        target_api_key = api_key or settings.OPENAI_API_KEY or "ollama"

        self.client = AsyncOpenAI(
            api_key=target_api_key,
            base_url=target_base_url
        )

    async def get_chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        model: str = settings.DEFAULT_LLM_MODEL,
        temperature: float = 0.7,
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

llm_service = LLMService()
