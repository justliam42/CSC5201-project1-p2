from fastapi import FastAPI, APIRouter, Response, status
from pydantic import BaseModel

router = APIRouter(prefix="/", tags=["Frontend"])

@router.get("/", response_class=Response, status_code=status.HTTP_200_OK)
async def root():
    # TODO Serve a frontend page
    return {"message": "Welcome to the FastAPI application!"}