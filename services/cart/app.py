import logging
import uuid
from contextvars import ContextVar

import google.cloud.logging
from fastapi import FastAPI, APIRouter, Request, Response, status
from google.cloud.logging_v2.handlers import CloudLoggingHandler
from google.cloud.logging_v2.handlers.transports import SyncTransport
from pydantic import BaseModel
import redis, os

HEADER = "X-Correlation-ID"
correlation_id = ContextVar("correlation_id", default="-")
log = logging.getLogger("cart")


def add_correlation_id(record):
    record.correlation_id = correlation_id.get()
    record.json_fields = {"service": "cart", "correlation_id": record.correlation_id}
    return True


handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(levelname)s [%(correlation_id)s] %(name)s %(message)s"))
log.addFilter(add_correlation_id)
log.addHandler(handler)
log.setLevel(logging.INFO)
log.propagate = False

# send the same logs to Google Cloud Logging as structured entries
try:
    cloud_handler = CloudLoggingHandler(google.cloud.logging.Client(), name="cart", transport=SyncTransport)
    log.addHandler(cloud_handler)
except Exception as e:
    log.warning("cloud logging is off, logs only go to the terminal: %s", e)

userRouter = APIRouter(prefix="/cart", tags=["Cart"])

class Item(BaseModel):
    id: int
    categories: list[str]
    description: str
    name: str
    price: float

def get_redis():
    return redis.Redis(
        host=os.getenv("REDIS_HOST", "redis"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        db=0,
        decode_responses=True,
    )


@userRouter.get("/{user_id}")
async def getUserItems(user_id: int):
    with get_redis() as r:
        items = r.lrange(f"user:{user_id}:items", 0, -1)

    if items:
        log.info("cart of user %s has %d items", user_id, len(items))
        return [Item.model_validate_json(item).model_dump() for item in items]
    else:
        log.info("cart of user %s is empty", user_id)
        return Response(status_code=status.HTTP_404_NOT_FOUND)

@userRouter.post("/{user_id}", status_code=status.HTTP_201_CREATED)
async def addUserItems(user_id: int, item: Item):
    with get_redis() as r:
        r.rpush(f"user:{user_id}:items", item.model_dump_json())
    log.info("added item %s to cart of user %s", item.id, user_id)

    return {"message": f"Item {item.id} added to user {user_id}'s cart."}

@userRouter.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deleteUserItem(user_id: int, item_id: int):
    with get_redis() as r:
        items = r.lrange(f"user:{user_id}:items", 0, -1)
        for item in items:
            item_data = Item.model_validate_json(item)
            if item_data.id == item_id:
                r.lrem(f"user:{user_id}:items", 1, item)
                log.info("removed item %s from cart of user %s", item_id, user_id)
                return Response(status_code=status.HTTP_204_NO_CONTENT)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

app = FastAPI()
app.include_router(userRouter)


@app.middleware("http")
async def add_correlation_header(request: Request, call_next):
    cid = request.headers.get(HEADER) or str(uuid.uuid4())
    correlation_id.set(cid)
    response = await call_next(request)
    response.headers[HEADER] = cid
    return response
