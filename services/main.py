import logging
import uuid
from fastapi import FastAPI, APIRouter, Request, Response, status
from pydantic import BaseModel
import checkout, frontend

app = FastAPI()

app.include_router(checkout.router)
app.include_router(frontend.router)

# frontend logs use the same handlers as checkout (terminal + Cloud Logging)
frontend_log = logging.getLogger("frontend")


def add_frontend_fields(record):
    cid = checkout.correlation_id.get()
    record.correlation_id = cid
    record.json_fields = {"service": "frontend", "correlation_id": cid}
    return True


frontend_log.addFilter(add_frontend_fields)
for h in checkout.log.handlers:
    frontend_log.addHandler(h)
frontend_log.setLevel(logging.INFO)
frontend_log.propagate = False


@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    cid = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    if "X-Correlation-ID" not in request.headers:
        request.scope["headers"].append((b"x-correlation-id", cid.encode()))
    checkout.correlation_id.set(cid)
    response = await call_next(request)
    frontend_log.info("%s %s -> %s", request.method, request.url.path, response.status_code)
    response.headers["X-Correlation-ID"] = cid
    return response

# Fastapi finds the 'app' variable and runs it when executing `fastapi run main.py`
