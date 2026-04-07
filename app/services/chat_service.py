import uuid
import json
import asyncio
import logging
from typing import AsyncGenerator, List, Optional, Dict, Any
from fastapi import BackgroundTasks
from sqlalchemy import update
from ..models.conversation import MessageStatus, Conversation
from ..repositories.chat_repo import ChatRepository
from ..core.retriever import Retriever
from ..services.llm_service import llm_service
from ..constants import RETRIEVAL_HISTORY_LENGTH, LLM_STREAM_TIMEOUT_SECONDS, LLM_MAX_TOKENS_TITLE_GENERATION

logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self, chat_repo: ChatRepository, retriever: Retriever):
        self.chat_repo = chat_repo
        self.retriever = retriever

    async def get_or_create_conversation(self, document_id: uuid.UUID, conversation_id: Optional[uuid.UUID] = None) -> uuid.UUID:
        if conversation_id:
            conv = await self.chat_repo.get_conversation(conversation_id)
            if conv:
                return conv.id
        
        new_conv = await self.chat_repo.create_conversation(document_id)
        return new_conv.id

    async def chat_stream(
        self,
        conversation_id: uuid.UUID,
        document_id: uuid.UUID,
        user_query: str,
        background_tasks: BackgroundTasks,
        mode: str = "socratic"
    ) -> AsyncGenerator[str, None]:
        """
        Main chat flow with SSE streaming and double-commit strategy.
        """
        # 0. Context Validation: Ensure conversation belongs to the document
        conv = await self.chat_repo.get_conversation(conversation_id)
        if not conv or conv.document_id != document_id:
            from fastapi import HTTPException
            logger.error(f"Context mismatch: conv {conversation_id} does not belong to doc {document_id}")
            raise HTTPException(status_code=400, detail="Conversation/Document mismatch or not found")

        # 1. Commit 1: Save User Message
        user_msg = await self.chat_repo.add_message(
            conversation_id=conversation_id,
            role="user",
            content=user_query
        )
        await self.chat_repo.session.commit() # Hardening: Explicit commit for user message

        # 2. Get Recent History (last 10 messages, BEFORE creating PENDING)
        # This ensures we don't accidentally include the PENDING message we're about to create
        history = await self.chat_repo.get_last_n_messages(conversation_id, n=RETRIEVAL_HISTORY_LENGTH)

        # 3. Retrieve Context (Hybrid: Top-k chunks/graph)
        context, found_entities = await self.retriever.retrieve(user_query, str(document_id))
        context_str = "\n".join([f"[{c['type']}] {c['content']}" for c in context])

        # 4. Construct Prompt
        messages = self._construct_tutor_prompt(mode, context_str, history, user_query)

        # 5. Commit 2: Create PENDING Assistant Message
        assistant_msg = await self.chat_repo.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content="",
            status=MessageStatus.PENDING,
            context_used={"retrieval": context}
        )
        await self.chat_repo.session.commit() # Hardening: Explicit commit for PENDING state

        # 6. Yield Meta Info
        yield f"event: meta\ndata: {json.dumps({'message_id': str(assistant_msg.id), 'conversation_id': str(conversation_id)})}\n\n"

        full_content = ""
        try:
            # 7. Start Streaming from LLM with timeout
            stream = await llm_service.stream_chat_completion(messages)
            
            # Add timeout to prevent hanging streams
            async def stream_with_timeout():
                async for chunk in stream:
                    yield chunk
            
            try:
                async with asyncio.timeout(LLM_STREAM_TIMEOUT_SECONDS):  # 2 minutes timeout
                    async for chunk in stream_with_timeout():
                        if chunk.choices and chunk.choices[0].delta.content:
                            delta = chunk.choices[0].delta.content
                            full_content += delta
                            yield f"event: chunk\ndata: {json.dumps({'delta': delta})}\n\n"
            except asyncio.TimeoutError:
                logger.error(f"Stream timeout after {len(full_content)} chars")
                raise Exception(f"LLM stream timed out after {LLM_STREAM_TIMEOUT_SECONDS} seconds")

            # 8. Commit 3 (Success): Update message to COMPLETED
            await self.chat_repo.update_message(
                assistant_msg.id,
                content=full_content,
                status=MessageStatus.COMPLETED
            )
            yield f"event: done\ndata: {json.dumps({'content_full': full_content, 'context_used': assistant_msg.context_used, 'found_entities': found_entities}, default=str)}\n\n"

        except (asyncio.CancelledError, GeneratorExit):
            logger.warning(f"Stream disconnected for message {assistant_msg.id}")
            # Commit 3 (Failure/Disconnect): Save partial content and mark as FAILED
            await self.chat_repo.update_message(
                assistant_msg.id, 
                content=full_content, 
                status=MessageStatus.FAILED
            )
            await self.chat_repo.session.commit()
            raise # Re-raise to allow cleanup

        except Exception as e:
            logger.error(f"Stream error: {e}")
            # Commit 3 (Failure): Save partial content and mark as FAILED
            await self.chat_repo.update_message(
                assistant_msg.id, 
                content=full_content, 
                status=MessageStatus.FAILED
            )
            await self.chat_repo.session.commit()
            yield f"event: error\ndata: {json.dumps({'detail': str(e), 'code': 'STREAM_INTERRUPTED'})}\n\n"
        
        finally:
            # Trigger title generation if it's the first assistant message
            if len(history) <= 1:
                background_tasks.add_task(self.generate_conversation_title, conversation_id, user_query)

    def _construct_tutor_prompt(self, mode: str, context: str, history: List[Any], query: str) -> List[Dict[str, str]]:
        system_role = (
            "You are a Socratic tutor. You never give direct answers. Instead, you ask guiding questions "
            "to help the student find the answer themselves based on the provided context."
            if mode == "socratic" else
            "You are a Feynman tutor. Explain complex concepts in the context as simply as possible, "
            "using analogies that a 5-year-old would understand."
        )

        prompt_messages = [{"role": "system", "content": system_role}]
        
        # Add context as a system message
        prompt_messages.append({
            "role": "system", 
            "content": f"Knowledge Context for the tutoring session:\n{context}\n\nUse ONLY this context for information."
        })

        # Add history messages (excluding the current user query which is added separately)
        for h in history:
            if h.role != "system":
                # History was fetched before creating the PENDING message,
                # so it won't include it. Safe to add all non-system messages.
                prompt_messages.append({"role": h.role, "content": h.content})

        # Final query
        # Ensure the last message in prompt is the current query if it wasn't already in history
        if not prompt_messages or prompt_messages[-1]["content"] != query:
            prompt_messages.append({"role": "user", "content": query})

        return prompt_messages

    async def generate_conversation_title(self, conversation_id: uuid.UUID, first_query: str):
        """
        Background task to generate a meaningful title for the conversation.
        Creates its own database session to avoid using closed request sessions.
        """
        from ..database import AsyncSessionLocal
        
        try:
            # Create a new session for the background task
            async with AsyncSessionLocal() as session:
                chat_repo = ChatRepository(session)
                
                prompt = f"Generate a very short title (max 5 words) for a conversation that starts with: '{first_query}'"
                response = await llm_service.get_chat_completion([
                    {"role": "user", "content": prompt}
                ], max_tokens=LLM_MAX_TOKENS_TITLE_GENERATION)

                title = response.choices[0].message.content.strip().strip('"')
                await chat_repo.session.execute(
                    update(Conversation)
                    .where(Conversation.id == conversation_id)
                    .values(title=title)
                )
                await chat_repo.session.commit()
                logger.info(f"Generated title for {conversation_id}: {title}")
        except Exception as e:
            logger.error(f"Failed to generate title: {e}")
