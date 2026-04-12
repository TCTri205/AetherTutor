from .base import Base
from .user import User
from .document import Document, DocumentStatus, ProcessingStep
from .graph import DocumentChunk, GraphEntity, GraphRelation, EntityAlias
from .entity_document import EntityDocument
from .conversation import Conversation, Message, MessageStatus

# Stage 2 models
from .flashcard import Flashcard, StudySession
from .quiz import Quiz, QuizResult, QuizAnswer
from .note import Note, NoteLink
from .note_entity_link import NoteEntityLink

# v1.2: User, Session & Topic Management
from .user_session import UserSession
from .topic import Topic
from .document_topic import DocumentTopic
from .note_topic import NoteTopic
from .study_session_group import StudySessionGroup

# Stage 4 Phase 3: Collaboration
from .team import Team, TeamMember, TeamRole
from .shared_resource import SharedResource, SharedResourceType, SharePermission

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
    "EntityDocument",
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
    "NoteEntityLink",
    # v1.2: User, Session & Topic
    "UserSession",
    "Topic",
    "DocumentTopic",
    "NoteTopic",
    "StudySessionGroup",
    # Stage 4 Phase 3: Collaboration
    "Team", "TeamMember", "TeamRole",
    "SharedResource", "SharedResourceType", "SharePermission",
]
