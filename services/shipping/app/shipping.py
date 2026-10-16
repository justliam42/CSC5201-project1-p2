def calculate_shipping(item_count: int) -> float:
    """
    Calculates the shipping cost based on the number of items in the cart:
    - $0.00 if the cart is empty
    - $8.99 if there are three or fewer items in the cart
    - $2.00 additional for each item beyond the third
    """
    if item_count == 0:
        return 0.00
    elif item_count <= 3:
        return 8.99
    else:
        extra_items = item_count - 3
        return round(8.99 + (2.00 * extra_items), 2)