import os
import random
import string
import uuid
import logging
import httpx
from fastapi import FastAPI, HTTPException, Query, Request, Response
from pydantic import BaseModel
from app.shipping import calculate_shipping

try:
    import google.cloud.logging
    client = google.cloud.logging.Client()
    client.setup_logging()
except Exception:
    logging.basicConfig(level=logging.INFO)

logger = logging.getLogger("shipping-service")

app = FastAPI(title="Shipping Service")

CART_SERVICE_URL = os.getenv("CART_SERVICE_URL", "http://localhost:8001")

@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    correlation_id = (
        request.headers.get("X-Correlation-ID") 
        or request.headers.get("X-Request-ID") 
        or str(uuid.uuid4())
    )
    request.state.correlation_id = correlation_id
    
    logger.info(f"Incoming request {request.method} {request.url.path}", extra={"json_fields": {"service": "shipping", "correlation_id": correlation_id}})
    
    response: Response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response

class Address(BaseModel):
    street: str 
    city: str
    state: str
    zip_code: str
    country: str

class ShippingRequest(BaseModel):
    user_id: str
    address: Address

@app.get("/shipping/{order_id}")
async def get_shipping_estimate(
    request: Request, 
    order_id: str, 
    user_id: str = Query(..., description="The user ID to fetch cart contents")
):
    correlation_id = getattr(request.state, "correlation_id", None)
    headers = {"X-Correlation-ID": correlation_id} if correlation_id else {}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{CART_SERVICE_URL}/cart/{user_id}", headers=headers)
            response.raise_for_status()
            cart_data = response.json()
        except httpx.RequestError as e:
            logger.error(f"Failed to fetch cart: {str(e)}", extra={"json_fields": {"service": "shipping", "correlation_id": correlation_id}})
            raise HTTPException(status_code=502, detail=f"Failed to fetch cart from cart service: {str(e)}")

    if isinstance(cart_data, list):
        items = cart_data
    elif isinstance(cart_data, dict):
        items = cart_data.get("items", [])
    else:
        items = []

    item_count = len(items)
    cost = calculate_shipping(item_count)

    logger.info(f"Calculated shipping for order {order_id}: ${cost}", extra={"json_fields": {"service": "shipping", "correlation_id": correlation_id}})

    return {
        "order_id": order_id,
        "item_count": item_count,
        "shipping_cost": cost
    }

@app.post("/shipping/{order_id}")
async def ship_order(request: Request, order_id: str, payload: ShippingRequest):
    correlation_id = getattr(request.state, "correlation_id", None)
    logger.info(f"Executing shipping order process for {order_id}", extra={"json_fields": {"service": "shipping", "correlation_id": correlation_id}})

    tracking_num = "TRK-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=10))

    return {
        "status": "success",
        "order_id": order_id,
        "tracking_number": tracking_num,
        "message": "Order successfully shipped (mocked)."
    }