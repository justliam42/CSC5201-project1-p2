from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/checkout", tags=["Checkout"])

@router.get("/{user_id}", response_class=HTMLResponse)
async def checkout(user_id: str):
    print(f"Checkout triggered for user: {user_id}")
    return f"<p>Checkout for user <strong>{user_id}</strong> is not implemented yet.</p>"