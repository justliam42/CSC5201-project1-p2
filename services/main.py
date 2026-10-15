import uuid
from fastapi import FastAPI, APIRouter, Request, Response, status
from pydantic import BaseModel
import checkout, frontend

app = FastAPI()

app.include_router(checkout.router)
app.include_router(frontend.router)


@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    cid = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    if "X-Correlation-ID" not in request.headers:
        request.scope["headers"].append((b"x-correlation-id", cid.encode()))
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = cid
    return response

# Fastapi finds the 'app' variable and runs it when executing `fastapi run main.py`
