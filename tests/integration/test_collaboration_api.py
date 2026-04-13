"""
Integration tests for Collaboration API (Sprint 15).

Tests:
- Team CRUD operations
- Team member management
- Invitations
- Shared resources
- WebSocket connection and events
"""
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.testclient import TestClient

from app.models.user import User
from app.models.team import Team, TeamMember, TeamRole
from app.models.shared_resource import SharedResource, SharedResourceType, SharePermission


# --- Fixtures ---

@pytest.fixture
async def team_owner_user(test_db: AsyncSession) -> User:
    """Create a user who will own a team."""
    user = User(
        id=uuid.uuid4(),
        email=f"owner_{uuid.uuid4().hex[:6]}@example.com",
        hashed_password="hashed",
        is_active=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def team_member_user(test_db: AsyncSession) -> User:
    """Create a user who will join a team."""
    user = User(
        id=uuid.uuid4(),
        email=f"member_{uuid.uuid4().hex[:6]}@example.com",
        hashed_password="hashed",
        is_active=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def sample_team(test_db: AsyncSession, team_owner_user: User) -> Team:
    """Create a team with owner as admin."""
    team = Team(
        name="Test Team Alpha",
        description="A test team for collaboration tests",
        owner_id=team_owner_user.id,
        max_members=50,
    )
    test_db.add(team)
    await test_db.flush()

    membership = TeamMember(
        team_id=team.id,
        user_id=team_owner_user.id,
        role=TeamRole.ADMIN,  # Uses enum value 'admin' (lowercase)
        is_active=True,
    )
    test_db.add(membership)
    await test_db.commit()
    await test_db.refresh(team)
    return team


# --- Agent API Integration Tests (need DB fixtures) ---

@pytest.mark.asyncio
async def test_list_agents_api(async_client: AsyncClient, team_owner_user: User):
    """Test GET /agents endpoint."""
    from app.services.security import create_access_token
    from app.core.agents.registry import agent_registry
    from app.core.agents.language_agent import LanguageAgent

    if not agent_registry.is_registered("language_agent"):
        agent_registry.register(
            LanguageAgent(),
            agent_id="language_agent",
            enabled=True,
            metadata={"builtin": True},
        )

    token = create_access_token(str(team_owner_user.id))

    response = await async_client.get(
        "/api/v1/agents",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "agents" in data


@pytest.mark.asyncio
async def test_get_agent_api(async_client: AsyncClient, team_owner_user: User):
    """Test GET /agents/{id} endpoint."""
    from app.services.security import create_access_token
    from app.core.agents.registry import agent_registry
    from app.core.agents.math_agent import MathAgent

    if not agent_registry.is_registered("math_agent"):
        agent_registry.register(
            MathAgent(),
            agent_id="math_agent",
            enabled=True,
            metadata={"builtin": True},
        )

    token = create_access_token(str(team_owner_user.id))

    response = await async_client.get(
        "/api/v1/agents/math_agent",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "Math Agent" in data["name"] or "math" in data["name"].lower()


@pytest.mark.asyncio
async def test_get_nonexistent_agent_api(async_client: AsyncClient, team_owner_user: User):
    """Test GET /agents/{id} for non-existent agent."""
    from app.services.security import create_access_token

    token = create_access_token(str(team_owner_user.id))

    response = await async_client.get(
        "/api/v1/agents/nonexistent_agent",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_unregister_builtin_agent_api(async_client: AsyncClient, team_owner_user: User):
    """Test cannot unregister built-in agents."""
    from app.services.security import create_access_token
    from app.core.agents.registry import agent_registry
    from app.core.agents.language_agent import LanguageAgent

    # Ensure language_agent is registered
    if not agent_registry.is_registered("language_agent"):
        agent_registry.register(
            LanguageAgent(),
            agent_id="language_agent",
            enabled=True,
            metadata={"builtin": True},
        )

    token = create_access_token(str(team_owner_user.id))

    response = await async_client.delete(
        "/api/v1/agents/language_agent",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


# --- Helper: Authenticate and get JWT token ---

async def authenticate_user(client: AsyncClient, user: User) -> str:
    """Generate JWT token for test user."""
    from app.services.security import create_access_token
    token = create_access_token(str(user.id))
    return token


# --- Team CRUD Tests ---

@pytest.mark.asyncio
async def test_create_team(async_client: AsyncClient, team_owner_user: User):
    """Test creating a new team."""
    token = await authenticate_user(async_client, team_owner_user)

    response = await async_client.post(
        "/api/v1/collaboration/teams",
        params={"name": "New Test Team", "description": "Test description"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Test Team"
    assert data["owner_id"] == str(team_owner_user.id)


@pytest.mark.asyncio
async def test_list_teams(async_client: AsyncClient, sample_team: Team, team_owner_user: User):
    """Test listing user's teams."""
    token = await authenticate_user(async_client, team_owner_user)

    response = await async_client.get(
        "/api/v1/collaboration/teams",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    team_names = [t["name"] for t in data["teams"]]
    assert sample_team.name in team_names


@pytest.mark.asyncio
async def test_get_team(async_client: AsyncClient, sample_team: Team, team_owner_user: User):
    """Test getting team details."""
    token = await authenticate_user(async_client, team_owner_user)

    response = await async_client.get(
        f"/api/v1/collaboration/teams/{sample_team.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(sample_team.id)
    assert data["name"] == sample_team.name
    assert "my_role" in data


@pytest.mark.asyncio
async def test_get_team_not_member(async_client: AsyncClient, sample_team: Team, team_member_user: User):
    """Test getting team when not a member returns 404."""
    token = await authenticate_user(async_client, team_member_user)

    response = await async_client.get(
        f"/api/v1/collaboration/teams/{sample_team.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_team(async_client: AsyncClient, sample_team: Team, team_owner_user: User):
    """Test updating team details (admin only)."""
    token = await authenticate_user(async_client, team_owner_user)

    response = await async_client.put(
        f"/api/v1/collaboration/teams/{sample_team.id}",
        params={"name": "Updated Team Name"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Team Name"


@pytest.mark.asyncio
async def test_update_team_non_admin(async_client: AsyncClient, sample_team: Team, team_member_user: User, test_db: AsyncSession):
    """Test that non-admin cannot update team."""
    # Add user as viewer
    membership = TeamMember(
        team_id=sample_team.id,
        user_id=team_member_user.id,
        role=TeamRole.VIEWER,
        is_active=True,
    )
    test_db.add(membership)
    await test_db.commit()

    token = await authenticate_user(async_client, team_member_user)

    response = await async_client.put(
        f"/api/v1/collaboration/teams/{sample_team.id}",
        params={"name": "Hacked Name"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_team(async_client: AsyncClient, team_owner_user: User, test_db: AsyncSession):
    """Test deleting team (owner only)."""
    # Create team
    team = Team(
        name="Delete Me Team",
        owner_id=team_owner_user.id,
        max_members=50,
    )
    test_db.add(team)
    await test_db.flush()
    membership = TeamMember(team_id=team.id, user_id=team_owner_user.id, role=TeamRole.ADMIN, is_active=True)
    test_db.add(membership)
    await test_db.commit()

    token = await authenticate_user(async_client, team_owner_user)

    response = await async_client.delete(
        f"/api/v1/collaboration/teams/{team.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_team_non_owner(async_client: AsyncClient, sample_team: Team, team_member_user: User, test_db: AsyncSession):
    """Test that non-owner cannot delete team."""
    membership = TeamMember(
        team_id=sample_team.id,
        user_id=team_member_user.id,
        role=TeamRole.ADMIN,
        is_active=True,
    )
    test_db.add(membership)
    await test_db.commit()

    token = await authenticate_user(async_client, team_member_user)

    response = await async_client.delete(
        f"/api/v1/collaboration/teams/{sample_team.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


# --- Team Members Tests ---

@pytest.mark.asyncio
async def test_list_team_members(async_client: AsyncClient, sample_team: Team, team_owner_user: User):
    """Test listing team members."""
    token = await authenticate_user(async_client, team_owner_user)

    response = await async_client.get(
        f"/api/v1/collaboration/teams/{sample_team.id}/members",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert any(m["user_id"] == str(team_owner_user.id) for m in data["members"])


# --- Shared Resources Tests ---

@pytest.mark.asyncio
async def test_share_resource(async_client: AsyncClient, sample_team: Team, team_owner_user: User):
    """Test sharing a resource with team."""
    token = await authenticate_user(async_client, team_owner_user)
    resource_id = uuid.uuid4()

    response = await async_client.post(
        f"/api/v1/collaboration/teams/{sample_team.id}/share",
        params={
            "resource_type": "graph",
            "resource_id": str(resource_id),
            "permission": "edit",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["resource_type"] == "graph"
    assert data["resource_id"] == str(resource_id)
    assert data["permission"] == "edit"


@pytest.mark.asyncio
async def test_share_resource_duplicate(async_client: AsyncClient, sample_team: Team, team_owner_user: User):
    """Test cannot share same resource twice."""
    token = await authenticate_user(async_client, team_owner_user)
    resource_id = uuid.uuid4()

    # First share
    await async_client.post(
        f"/api/v1/collaboration/teams/{sample_team.id}/share",
        params={
            "resource_type": "graph",
            "resource_id": str(resource_id),
            "permission": "view",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    # Second share should fail
    response = await async_client.post(
        f"/api/v1/collaboration/teams/{sample_team.id}/share",
        params={
            "resource_type": "graph",
            "resource_id": str(resource_id),
            "permission": "edit",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_list_shared_resources(async_client: AsyncClient, sample_team: Team, team_owner_user: User):
    """Test listing shared resources."""
    token = await authenticate_user(async_client, team_owner_user)
    resource_id = uuid.uuid4()

    # Share a resource
    await async_client.post(
        f"/api/v1/collaboration/teams/{sample_team.id}/share",
        params={
            "resource_type": "note",
            "resource_id": str(resource_id),
            "permission": "view",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    # List shared resources
    response = await async_client.get(
        f"/api/v1/collaboration/teams/{sample_team.id}/shared",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert any(r["resource_id"] == str(resource_id) for r in data["resources"])


@pytest.mark.asyncio
async def test_unshare_resource(async_client: AsyncClient, sample_team: Team, team_owner_user: User):
    """Test unsharing a resource."""
    token = await authenticate_user(async_client, team_owner_user)
    resource_id = uuid.uuid4()

    # Share first
    share_resp = await async_client.post(
        f"/api/v1/collaboration/teams/{sample_team.id}/share",
        params={
            "resource_type": "flashcard",
            "resource_id": str(resource_id),
            "permission": "edit",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    share_id = share_resp.json()["id"]

    # Unshare
    response = await async_client.delete(
        f"/api/v1/collaboration/teams/{sample_team.id}/share/{share_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 204


# --- WebSocket Connection Manager Tests (Unit) ---

class TestConnectionManager:
    """Unit tests for WebSocket ConnectionManager."""

    @pytest.fixture
    def manager(self):
        from app.api.websocket import ConnectionManager
        return ConnectionManager()

    def test_add_to_room(self, manager):
        """Test adding connection to room."""
        conn_id = "conn-1"
        user_id = "user-1"
        manager.active_connections[conn_id] = {
            "websocket": None,
            "user_id": user_id,
            "rooms": set(),
            "metadata": {},
            "connected_at": "2026-01-01T00:00:00",
            "last_heartbeat": "2026-01-01T00:00:00",
        }
        manager.user_connections[user_id] = {conn_id}

        result = manager.add_to_room(conn_id, "graph:123")
        assert result is True
        assert conn_id in manager.rooms["graph:123"]

    def test_remove_from_room(self, manager):
        """Test removing connection from room."""
        conn_id = "conn-1"
        user_id = "user-1"
        manager.active_connections[conn_id] = {
            "websocket": None,
            "user_id": user_id,
            "rooms": {"graph:123"},
            "metadata": {},
            "connected_at": "2026-01-01T00:00:00",
            "last_heartbeat": "2026-01-01T00:00:00",
        }
        manager.user_connections[user_id] = {conn_id}
        manager.rooms["graph:123"] = {conn_id}

        manager.remove_from_room(conn_id, "graph:123")
        assert conn_id not in manager.rooms.get("graph:123", set())

    def test_get_online_users_in_room_deduplicates(self, manager):
        """Test that online users are deduplicated by user_id."""
        manager.active_connections = {
            "conn-1": {"websocket": None, "user_id": "user-1", "rooms": {"room-a"}, "metadata": {}},
            "conn-2": {"websocket": None, "user_id": "user-1", "rooms": {"room-a"}, "metadata": {}},
            "conn-3": {"websocket": None, "user_id": "user-2", "rooms": {"room-a"}, "metadata": {}},
        }
        manager.rooms["room-a"] = {"conn-1", "conn-2", "conn-3"}

        users = manager.get_online_users_in_room("room-a")
        assert len(users) == 2
        user_ids = {u["user_id"] for u in users}
        assert user_ids == {"user-1", "user-2"}

    def test_get_connection_stats(self, manager):
        """Test connection statistics."""
        manager.active_connections = {
            "conn-1": {"websocket": None, "user_id": "user-1", "rooms": set(), "metadata": {}},
            "conn-2": {"websocket": None, "user_id": "user-2", "rooms": set(), "metadata": {}},
        }
        manager.user_connections = {
            "user-1": {"conn-1"},
            "user-2": {"conn-2"},
        }
        manager.rooms = {}

        stats = manager.get_connection_stats()
        assert stats["total_connections"] == 2
        assert stats["unique_users"] == 2
        assert stats["total_rooms"] == 0
