import os

import requests
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/recommendations", tags=["Recommendation"])

CART_URL = os.getenv("CART_URL", "https://cart-service-km6fpv6l4a-uc.a.run.app")
CATALOG_URL = os.getenv("CATALOG_URL", "https://catalog-km6fpv6l4a-uc.a.run.app")
TIMEOUT = 90


def get_json(url):
    try:
        response = requests.get(url, timeout=TIMEOUT)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as error:
        raise HTTPException(502, "cart or catalog service error") from error


@router.get("/{user_id}")
def recommendations(user_id: int):
    cart = get_json(f"{CART_URL}/cart/{user_id}")
    products = get_json(f"{CATALOG_URL}/products")
    if isinstance(products, dict):
        products = products["products"]

    cart_ids = {str(item.get("id", item.get("product_id"))) for item in cart["items"]}
    cart_categories = set()
    for product in products:
        if str(product.get("id", product.get("product_id"))) in cart_ids:
            cart_categories.update(product["categories"])

    recommended = []
    for product in products:
        if (
            str(product.get("id", product.get("product_id"))) not in cart_ids
            and cart_categories.intersection(product["categories"])
        ):
            recommended.append(product)
            if len(recommended) == 5:
                break

    return recommended
