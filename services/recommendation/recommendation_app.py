import uuid

from fastapi import FastAPI, Request

import recommendation

app = FastAPI()
app.include_router(recommendation.router)


@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    cid = request.headers.get(recommendation.HEADER) or str(uuid.uuid4())
    if recommendation.HEADER not in request.headers:
        request.scope["headers"].append((b"x-correlation-id", cid.encode()))
    response = await call_next(request)
    response.headers[recommendation.HEADER] = cid
    return response
