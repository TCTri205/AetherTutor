"""
Collaboration API — Team management, shared resources, and invitations.

Endpoints:
- POST   /teams                    — Create a team
- GET    /teams                    — List user's teams
- GET    /teams/{team_id}          — Get team details
- PUT    /teams/{team_id}          — Update team
- DELETE /teams/{team_id}          — Delete team (owner only)
- GET    /teams/{team_id}/members  — List team members
- POST   /teams/{team_id}/invite   — Invite user to team
- POST   /teams/{team_id}/invite/{invite_id}/accept — Accept invitation
- POST   /teams/{team_id}/invite/{invite_id}/decline — Decline invitation
- POST   /teams/{team_id}/share    — Share a resource with team
- DELETE /teams/{team_id}/share/{resource_id} — Unshare resource
- GET    /teams/{team_id}/shared   — List shared resources
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user_id
from app.dependencies import DBDependency
from app.models.team import Team, TeamMember, TeamRole
from app.models.shared_resource import SharedResource, SharedResourceType, SharePermission
from app.models.user import User
from app.services.email_service import (
    generate_verification_token,
)
from app.config import settings

router = APIRouter(prefix="/collaboration", tags=["collaboration"])


# ---------------------------------------------------------------------------
# Team CRUD
# ---------------------------------------------------------------------------

@router.post("/teams", status_code=status.HTTP_201_CREATED)
async def create_team(
    name: str,
    description: Optional[str] = None,
    max_members: int = 50,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: DBDependency = None,
):
    """Create a new team. User becomes owner with ADMIN role."""
    # Create team
    team = Team(
        name=name,
        description=description,
        owner_id=user_id,
        max_members=max_members,
    )
    db.add(team)
    await db.flush()

    # Add owner as admin member
    membership = TeamMember(
        team_id=team.id,
        user_id=user_id,
        role=TeamRole.ADMIN,
        is_active=True,
    )
    db.add(membership)
    await db.commit()
    await db.refresh(team)

    logger.info(f"Team created: {team.id} by {user_id}")
    return {
        "id": team.id,
        "name": team.name,
        "description": team.description,
        "owner_id": team.owner_id,
        "max_members": team.max_members,
        "created_at": team.created_at.isoformat() if team.created_at else None,
    }


@router.get("/teams")
async def list_teams(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: DBDependency = None,
):
    """List all teams the user is a member of."""
    query = (
        select(Team, TeamMember.role, TeamMember.is_active)
        .join(TeamMember, Team.id == TeamMember.team_id)
        .where(TeamMember.user_id == user_id, TeamMember.is_active == True)
    )
    result = await db.execute(query)
    rows = result.all()

    teams = []
    for team, role, is_active in rows:
        # Count members
        member_count_query = (
            select(func.count())
            .select_from(TeamMember)
            .where(TeamMember.team_id == team.id, TeamMember.is_active == True)
        )
        member_count_result = await db.execute(member_count_query)
        member_count = member_count_result.scalar() or 0

        teams.append({
            "id": team.id,
            "name": team.name,
            "description": team.description,
            "owner_id": team.owner_id,
            "my_role": role.value,
            "member_count": member_count,
            "created_at": team.created_at.isoformat() if team.created_at else None,
        })

    return {"teams": teams, "total": len(teams)}


@router.get("/teams/{team_id}")
async def get_team(
    team_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: DBDependency = None,
):
    """Get team details (must be member)."""
    membership = await _get_membership(db, team_id, user_id)
    if not membership:
        raise HTTPException(status_code=404, detail="Team not found or not a member")

    team = membership.team
    return {
        "id": team.id,
        "name": team.name,
        "description": team.description,
        "owner_id": team.owner_id,
        "max_members": team.max_members,
        "my_role": membership.role.value,
        "created_at": team.created_at.isoformat() if team.created_at else None,
    }


@router.put("/teams/{team_id}")
async def update_team(
    team_id: uuid.UUID,
    name: Optional[str] = None,
    description: Optional[str] = None,
    max_members: Optional[int] = None,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: DBDependency = None,
):
    """Update team (admin only)."""
    membership = await _require_role(db, team_id, user_id, TeamRole.ADMIN)

    team = membership.team
    if name:
        team.name = name
    if description is not None:
        team.description = description
    if max_members:
        team.max_members = max_members

    await db.commit()
    await db.refresh(team)

    logger.info(f"Team updated: {team.id} by {user_id}")
    return {"id": team.id, "name": team.name, "description": team.description}


@router.delete("/teams/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team(
    team_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: DBDependency = None,
):
    """Delete team (owner only)."""
    team_query = select(Team).where(Team.id == team_id, Team.owner_id == user_id)
    result = await db.execute(team_query)
    team = result.scalar_one_or_none()

    if not team:
        raise HTTPException(
            status_code=403, detail="Only team owner can delete"
        )

    await db.delete(team)
    await db.commit()
    logger.info(f"Team deleted: {team_id} by {user_id}")


# ---------------------------------------------------------------------------
# Team Members
# ---------------------------------------------------------------------------

@router.get("/teams/{team_id}/members")
async def list_team_members(
    team_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: DBDependency = None,
):
    """List all active team members."""
    membership = await _get_membership(db, team_id, user_id)
    if not membership:
        raise HTTPException(status_code=404, detail="Team not found or not a member")

    query = (
        select(TeamMember, User.email, User.username, User.full_name, User.avatar_url)
        .join(User, TeamMember.user_id == User.id)
        .where(TeamMember.team_id == team_id, TeamMember.is_active == True)
    )
    result = await db.execute(query)
    rows = result.all()

    members = []
    for tm, email, username, full_name, avatar_url in rows:
        members.append({
            "id": tm.id,
            "user_id": tm.user_id,
            "email": email,
            "username": username,
            "full_name": full_name,
            "avatar_url": avatar_url,
            "role": tm.role.value,
            "is_active": tm.is_active,
            "invited_by": str(tm.invited_by) if tm.invited_by else None,
            "joined_at": tm.created_at.isoformat() if tm.created_at else None,
        })

    return {"members": members, "total": len(members)}


# ---------------------------------------------------------------------------
# Invitations
# ---------------------------------------------------------------------------

@router.post("/teams/{team_id}/invite", status_code=status.HTTP_201_CREATED)
async def invite_to_team(
    team_id: uuid.UUID,
    email: str,
    role: str = "viewer",
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: DBDependency = None,
):
    """
    Invite a user to team by email.
    
    If user exists, creates membership directly.
    If user doesn't exist, sends invitation email (mock mode logs link).
    """
    # Check inviter is admin
    await _require_role(db, team_id, user_id, TeamRole.ADMIN)

    # Check team exists and member count
    team_query = select(Team).where(Team.id == team_id)
    result = await db.execute(team_query)
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Find user by email
    user_query = select(User).where(User.email == email)
    user_result = await db.execute(user_query)
    target_user = user_result.scalar_one_or_none()

    # Validate role
    try:
        invite_role = TeamRole(role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: {role}")

    if target_user:
        # User exists — check if already member
        existing = await _get_membership(db, team_id, target_user.id)
        if existing:
            raise HTTPException(
                status_code=400, detail="User is already a team member"
            )

        # Create membership
        new_member = TeamMember(
            team_id=team_id,
            user_id=target_user.id,
            role=invite_role,
            invited_by=user_id,
            is_active=True,
        )
        db.add(new_member)
        await db.commit()
        await db.refresh(new_member)

        # Send notification via WebSocket if online
        from app.api.websocket import ws_manager
        online_count = ws_manager.get_room_count(f"team:{team_id}")

        return {
            "status": "added",
            "member_id": new_member.id,
            "user_id": target_user.id,
            "email": email,
            "role": invite_role.value,
        }
    else:
        # User doesn't exist — send invitation email
        # Generate invitation token (reuse email verification token logic)
        invite_token = generate_verification_token(email)

        # Send email (mock mode if SMTP not configured)
        invite_link = f"{settings.FRONTEND_URL}/invite/{team_id}?token={invite_token}"
        
        if settings.SMTP_HOST:
            # TODO: Send actual invitation email when SMTP configured
            logger.info(f"Invitation email would be sent to {email}: {invite_link}")
        else:
            logger.info(f"INVITATION LINK (mock mode): {invite_link}")

        return {
            "status": "invited",
            "email": email,
            "role": invite_role.value,
            "invite_link": invite_link,
            "note": "User will be added when they accept the invitation",
        }


@router.post("/teams/{team_id}/invite/{invite_id}/accept")
async def accept_invitation(
    team_id: uuid.UUID,
    invite_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: DBDependency = None,
):
    """Accept a team invitation (for existing users)."""
    membership = await _get_membership(db, team_id, user_id)
    if membership:
        raise HTTPException(status_code=400, detail="Already a team member")

    # Find the invitation (we'll use TeamMember with is_active=False as invitation)
    invite_query = select(TeamMember).where(
        TeamMember.id == invite_id,
        TeamMember.team_id == team_id,
        TeamMember.user_id == user_id,
    )
    invite_result = await db.execute(invite_query)
    invitation = invite_result.scalar_one_or_none()

    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")

    # Activate membership
    invitation.is_active = True
    await db.commit()

    logger.info(f"User {user_id} accepted invitation to team {team_id}")
    return {"status": "accepted", "team_id": team_id}


# ---------------------------------------------------------------------------
# Shared Resources
# ---------------------------------------------------------------------------

@router.post("/teams/{team_id}/share", status_code=status.HTTP_201_CREATED)
async def share_resource(
    team_id: uuid.UUID,
    resource_type: str,
    resource_id: uuid.UUID,
    permission: str = "view",
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: DBDependency = None,
):
    """Share a resource with a team."""
    # Must be team member
    membership = await _get_membership(db, team_id, user_id)
    if not membership:
        raise HTTPException(status_code=404, detail="Team not found or not a member")

    # Validate resource type
    try:
        res_type = SharedResourceType(resource_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid resource type: {resource_type}. Valid: {[r.value for r in SharedResourceType]}",
        )

    # Validate permission
    try:
        perm = SharePermission(permission)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid permission: {permission}. Valid: {[p.value for p in SharePermission]}",
        )

    # Check if already shared
    existing_query = select(SharedResource).where(
        SharedResource.team_id == team_id,
        SharedResource.resource_type == res_type,
        SharedResource.resource_id == resource_id,
        SharedResource.is_active == True,
    )
    existing_result = await db.execute(existing_query)
    existing = existing_result.scalar_one_or_none()

    if existing:
        raise HTTPException(status_code=400, detail="Resource already shared with this team")

    # Create share record
    share = SharedResource(
        team_id=team_id,
        resource_type=res_type,
        resource_id=resource_id,
        shared_by=user_id,
        default_permission=perm,
    )
    db.add(share)
    await db.commit()
    await db.refresh(share)

    # Notify team members via WebSocket
    from app.api.websocket import ws_manager
    room_name = f"team:{team_id}"
    await ws_manager.broadcast_to_room(room_name, {
        "event": "resource_shared",
        "data": {
            "resource_type": res_type.value,
            "resource_id": str(resource_id),
            "permission": perm.value,
            "shared_by": str(user_id),
        },
    })

    logger.info(f"Resource shared: {res_type.value}:{resource_id} with team {team_id}")
    return {
        "id": share.id,
        "resource_type": res_type.value,
        "resource_id": str(resource_id),
        "permission": perm.value,
    }


@router.delete("/teams/{team_id}/share/{share_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unshare_resource(
    team_id: uuid.UUID,
    share_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: DBDependency = None,
):
    """Unshare a resource from a team."""
    share_query = select(SharedResource).where(
        SharedResource.id == share_id,
        SharedResource.team_id == team_id,
    )
    share_result = await db.execute(share_query)
    share = share_result.scalar_one_or_none()

    if not share:
        raise HTTPException(status_code=404, detail="Shared resource not found")

    # Must be shared_by or admin
    membership = await _get_membership(db, team_id, user_id)
    if share.shared_by != user_id and membership.role not in (TeamRole.ADMIN,):
        raise HTTPException(status_code=403, detail="Cannot unshare this resource")

    share.is_active = False
    await db.commit()

    logger.info(f"Resource unshared: {share_id} from team {team_id}")


@router.get("/teams/{team_id}/shared")
async def list_shared_resources(
    team_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: DBDependency = None,
):
    """List all resources shared with a team."""
    membership = await _get_membership(db, team_id, user_id)
    if not membership:
        raise HTTPException(status_code=404, detail="Team not found or not a member")

    query = (
        select(SharedResource)
        .where(
            SharedResource.team_id == team_id,
            SharedResource.is_active == True,
        )
        .order_by(SharedResource.created_at.desc())
    )
    result = await db.execute(query)
    resources = result.scalars().all()

    return {
        "resources": [
            {
                "id": r.id,
                "resource_type": r.resource_type.value,
                "resource_id": str(r.resource_id),
                "permission": r.default_permission.value,
                "shared_by": str(r.shared_by),
                "shared_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in resources
        ],
        "total": len(resources),
    }


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

async def _get_membership(
    db: AsyncSession, team_id: uuid.UUID, user_id: uuid.UUID
) -> TeamMember | None:
    """Get user's team membership."""
    query = select(TeamMember).where(
        TeamMember.team_id == team_id,
        TeamMember.user_id == user_id,
        TeamMember.is_active == True,
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def _require_role(
    db: AsyncSession, team_id: uuid.UUID, user_id: uuid.UUID, min_role: TeamRole
) -> TeamMember:
    """Check user has at least the specified role, raise 403 if not."""
    membership = await _get_membership(db, team_id, user_id)
    if not membership:
        raise HTTPException(status_code=404, detail="Team not found or not a member")

    role_hierarchy = {TeamRole.VIEWER: 0, TeamRole.EDITOR: 1, TeamRole.ADMIN: 2}
    if role_hierarchy.get(membership.role, -1) < role_hierarchy[min_role]:
        raise HTTPException(
            status_code=403, detail=f"Requires {min_role.value} role or higher"
        )

    return membership
