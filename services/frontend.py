import os

import requests
from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="services/templates")
router = APIRouter(prefix="", tags=["Frontend"])

CATALOG_URL = os.getenv("CATALOG_URL", "https://catalog-km6fpv6l4a-uc.a.run.app")
CART_URL = os.getenv("CART_URL", "https://cart-service-km6fpv6l4a-uc.a.run.app")
RECOMMENDATION_URL = os.getenv("RECOMMENDATION_URL", "https://recommendation-service-617213266896.us-central1.run.app")
TIMEOUT = 90


def get_products(url):
    response = requests.get(f"{url}/products", timeout=TIMEOUT)
    response.raise_for_status()
    data = response.json()
    return data.get("products", data) if isinstance(data, dict) else data


@router.get("/", response_class=Response, status_code=status.HTTP_200_OK)
async def root(request: Request):
    products = get_products(CATALOG_URL)
    return templates.TemplateResponse(
        "index.html",
        name="index.html",
        context={"request": request, "products": products},
    )


@router.post("/cart/{user_id}/{product_id}", response_class=HTMLResponse)
def add_to_cart(user_id: int, product_id: int):
    product = requests.get(
        f"{CATALOG_URL}/products/{product_id}", timeout=TIMEOUT
    )
    if product.status_code != 200:
        raise HTTPException(product.status_code, "product is not in the catalog")

    response = requests.post(
        f"{CART_URL}/cart/{user_id}", json=product.json(), timeout=TIMEOUT
    )
    if response.status_code >= 400:
        raise HTTPException(502, "cart service error")
    return HTMLResponse("Added to cart")


@router.get("/recommendations/{user_id}", response_class=HTMLResponse)
def recommendations(user_id: int, request: Request):
    if not RECOMMENDATION_URL:
        return HTMLResponse(
            "<p>Recommendations are not configured.</p>", status_code=503
        )

    response = requests.get(
        f"{RECOMMENDATION_URL}/recommendations/{user_id}", timeout=TIMEOUT
    )
    response.raise_for_status()
    data = response.json()
    products = data.get("products", data) if isinstance(data, dict) else data
    return templates.TemplateResponse(
        "recommendations.html", {"request": request, "products": products}
    )
