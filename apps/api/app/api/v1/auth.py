"""Auth endpoints - sync user profile from Supabase REST API."""
from fastapi import APIRouter, HTTPException
from app.core.supabase_rest import supabase_rest
from app.core.security import CurrentUserDep, get_current_user
from app.schemas import UserRead

router = APIRouter()


@router.get("/me", response_model=UserRead, summary="Current user profile")
async def get_me(user: CurrentUserDep):
    """Returns the profile of the authenticated user; auto-creates if missing."""
    rows = await supabase_rest.table("users", select="*", eq_filters={"id": str(user.id)})
    if rows:
        return UserRead.model_validate(rows[0])

    raw_name = (
        (user.user_metadata or {}).get("full_name")
        or user.email.split("@")[0].replace(".", " ").title()
    )
    data = {
        "id": str(user.id),
        "email": user.email,
        "full_name": raw_name,
        "status": "active",
    }
    await supabase_rest.insert("users", data, return_repr=False)

    rows = await supabase_rest.table("users", select="*", eq_filters={"id": str(user.id)})
    return UserRead.model_validate(rows[0])


@router.post("/logout", summary="Logout (client-side token discard)")
async def logout(user: CurrentUserDep):
    """Logout is handled client-side by discarding the JWT. Endpoint exists for audit hooks."""
    return {"status": "logged_out", "user_id": str(user.id)}
