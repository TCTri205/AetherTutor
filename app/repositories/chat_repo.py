import uuid
from typing import Optional, List
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.conversation import Conversation, Message, MessageStatus
from .base import BaseRepository

class ChatRepository(BaseRepository[Conversation]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Conversation)

    async def create_conversation(self, document_id: uuid.UUID, title: str = "Cuộc hội thoại mới") -> Conversation:
        conv = Conversation(
            document_id=document_id,
            title=title
        )
        self.session.add(conv)
        await self.session.flush()
        return conv

    async def get_conversation(self, conversation_id: uuid.UUID) -> Optional[Conversation]:
        return await self.get_by_id(conversation_id)

    async def list_conversations(self, document_id: uuid.UUID) -> List[Conversation]:
        result = await self.session.execute(
            select(Conversation)
            .where(Conversation.document_id == document_id)
            .order_by(Conversation.last_message_at.desc())
        )
        return list(result.scalars().all())

    async def delete_conversation(self, conversation_id: uuid.UUID) -> bool:
        return await self.delete(conversation_id)

    async def add_message(
        self,
        conversation_id: uuid.UUID,
        role: str,
        content: str,
        status: MessageStatus = MessageStatus.COMPLETED,
        context_used: Optional[dict] = None
    ) -> Message:
        # Get next sequence index
        result = await self.session.execute(
            select(func.coalesce(func.max(Message.sequence_index), -1))
            .where(Message.conversation_id == conversation_id)
        )
        next_index = result.scalar() + 1

        msg = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            sequence_index=next_index,
            status=status,
            context_used=context_used
        )
        self.session.add(msg)
        
        # Update conversation's last_message_at
        await self.session.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(last_message_at=func.now())
        )
        
        await self.session.flush()
        return msg

    async def update_message(
        self,
        message_id: uuid.UUID,
        content: Optional[str] = None,
        status: Optional[MessageStatus] = None,
        context_used: Optional[dict] = None
    ) -> Optional[Message]:
        result = await self.session.execute(
            select(Message).where(Message.id == message_id)
        )
        msg = result.scalars().first()
        if msg:
            if content is not None:
                msg.content = content
            if status is not None:
                msg.status = status
            if context_used is not None:
                msg.context_used = context_used
            await self.session.flush()
        return msg

    async def get_messages(self, conversation_id: uuid.UUID, limit: int = 50) -> List[Message]:
        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.sequence_index.asc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_last_n_messages(self, conversation_id: uuid.UUID, n: int = 10) -> List[Message]:
        """
        Lấy n tin nhắn gần nhất theo đúng thứ tự sequence.
        Tối ưu: Fetch DESC rồi reverse trong Python thay vì dùng subquery phức tạp.
        """
        # Fetch last n messages in descending order
        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.sequence_index.desc())
            .limit(n)
        )
        messages = list(result.scalars().all())
        # Reverse để có thứ tự tăng dần (chronological order)
        return list(reversed(messages))
