from .base import Base
from .user import User
from .document import Document, DocumentStatus, ProcessingStep
from .graph import DocumentChunk, GraphEntity, GraphRelation, EntityAlias
from .conversation import Conversation, Message, MessageStatus

# Stage 2 models
from .flashcard import Flashcard, StudySession
from .quiz import Quiz, QuizResult, QuizAnswer
from .note import Note, NoteLink

# v1.2: User, Session & Topic Management
from .user_session import UserSession
from .topic import Topic
from .document_topic import DocumentTopic
from .note_topic import NoteTopic
from .study_session_group import StudySessionGroup

__all__ = [
    "Base",
    "User",
    "Document",
    "DocumentStatus",
    "ProcessingStep",
    "DocumentChunk",
    "GraphEntity",
    "GraphRelation",
    "EntityAlias",
    "Conversation",
    "Message",
    "MessageStatus",
    # Stage 2
    "Flashcard",
    "StudySession",
    "Quiz",
    "QuizResult",
    "QuizAnswer",
    "Note",
    "NoteLink",
    # v1.2: User, Session & Topic
    "UserSession",
    "Topic",
    "DocumentTopic",
    "NoteTopic",
    "StudySessionGroup",
]
