from fastapi import APIRouter, Request, Response, status
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="services/templates")
router = APIRouter(prefix="", tags=["Frontend"])

@router.get("/", response_class=Response, status_code=status.HTTP_200_OK)
async def root(request: Request):
    return templates.TemplateResponse(
        "index.html", name="index.html", context={"request": request}
    )