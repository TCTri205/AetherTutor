from openai import AsyncOpenAI
from typing import Optional, List, Dict, Any, Type
import json
from pydantic import BaseModel, ValidationError
from ..config import settings

class LLMService:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        # Use explicit base_url or OLLAMA_BASE_URL if no valid OpenAI key provided
        is_openai_valid = api_key and not api_key.startswith("your_")
        if not is_openai_valid and settings.OPENAI_API_KEY:
             is_openai_valid = not settings.OPENAI_API_KEY.startswith("your_")

        target_base_url = base_url or (None if is_openai_valid else settings.OLLAMA_BASE_URL)
        target_api_key = api_key or settings.OPENAI_API_KEY or "ollama"
        if not target_api_key or target_api_key.startswith("your_"):
            target_api_key = "ollama"

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

    async def structured_extraction(
        self,
        prompt: str,
        response_model: Type[BaseModel],
        model: str = settings.DEFAULT_LLM_MODEL,
        max_retries: int = 3
    ) -> Optional[BaseModel]:
        """
        Calls the LLM with a prompt and enforces JSON format.
        Retries on JSON decoding errors.
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
                    temperature=0.1
                )
                
                raw_content = response.choices[0].message.content
                if not raw_content:
                    continue
                
                data = json.loads(raw_content)
                return response_model.model_validate(data)
                
            except (json.JSONDecodeError, ValueError, ValidationError) as e:
                print(f"Extraction attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    return None
            except Exception as e:
                print(f"Unexpected error during extraction: {e}")
                return None
        
        return None

llm_service = LLMService()
