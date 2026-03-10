from fastapi import FastAPI, Query
from pydantic import BaseModel, Field
from typing import Optional, List

app = FastAPI(title="FastAPI Day 2 Assignment")

# ── Sample Data ──────────────────────────────────────────────────────────────

products = [
    {"id": 1, "name": "Wireless Mouse", "price": 499, "category": "Electronics", "in_stock": True},
    {"id": 2, "name": "Notebook",       "price": 99,  "category": "Stationery",  "in_stock": True},
    {"id": 3, "name": "USB Hub",        "price": 799, "category": "Electronics", "in_stock": False},
    {"id": 4, "name": "Pen Set",        "price": 49,  "category": "Stationery",  "in_stock": True},
]

orders   = []
feedback = []

# ── Day-1 base endpoints ─────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "Welcome to the FastAPI store!"}


@app.get("/products")
def get_products():
    return {"products": products}




# ── Q4: /products/summary — must be declared BEFORE /products/filter ─────────

@app.get("/products/summary")
def product_summary():
    """Q4: Product Summary Dashboard"""
    in_stock   = [p for p in products if     p["in_stock"]]
    out_stock  = [p for p in products if not p["in_stock"]]
    expensive  = max(products, key=lambda p: p["price"])
    cheapest   = min(products, key=lambda p: p["price"])
    categories = list(set(p["category"] for p in products))
    return {
        "total_products":     len(products),
        "in_stock_count":     len(in_stock),
        "out_of_stock_count": len(out_stock),
        "most_expensive":     {"name": expensive["name"], "price": expensive["price"]},
        "cheapest":           {"name": cheapest["name"],  "price": cheapest["price"]},
        "categories":         categories,
    }


# ── Q1: /products/filter — adds min_price param ──────────────────────────────

@app.get("/products/filter")
def filter_products(
    category:  str = Query(None, description="Filter by category"),
    max_price: int = Query(None, description="Maximum price"),
    min_price: int = Query(None, description="Minimum price"),
):
    result = products.copy()

    if category:
        result = [p for p in result if p["category"].lower() == category.lower()]

    if max_price is not None:
        result = [p for p in result if p["price"] <= max_price]

    if min_price is not None:
        result = [p for p in result if p["price"] >= min_price]

    return {"products": result, "count": len(result)}

@app.get("/products/{product_id}")
def get_product(product_id: int):
    for product in products:
        if product["id"] == product_id:
            return {"product": product}
    return {"error": "Product not found"}

# ── Q2: /products/{product_id}/price ─────────────────────────────────────────

@app.get("/products/{product_id}/price")
def get_product_price(product_id: int):
    """Q2: Return only name and price for a given product ID"""
    for product in products:
        if product["id"] == product_id:
            return {"name": product["name"], "price": product["price"]}
    return {"error": "Product not found"}


# ── Pydantic models ───────────────────────────────────────────────────────────

class OrderRequest(BaseModel):
    customer_name: str = Field(..., min_length=2, max_length=100)
    product_id:    int = Field(..., gt=0)
    quantity:      int = Field(..., gt=0, le=100)


class CustomerFeedback(BaseModel):
    """Q3: Feedback model — rating 1-5, comment optional"""
    customer_name: str           = Field(..., min_length=2, max_length=100)
    product_id:    int           = Field(..., gt=0)
    rating:        int           = Field(..., ge=1, le=5)
    comment:       Optional[str] = Field(None, max_length=300)


class OrderItem(BaseModel):
    """Q5: Single item in a bulk order"""
    product_id: int = Field(..., gt=0)
    quantity:   int = Field(..., gt=0, le=50)


class BulkOrder(BaseModel):
    """Q5: Bulk order with list of items"""
    company_name:  str             = Field(..., min_length=2)
    contact_email: str             = Field(..., min_length=5)
    items:         List[OrderItem] = Field(..., min_length=1)


# ── POST /orders — Bonus: status starts as "pending" ─────────────────────────

@app.post("/orders")
def place_order(order: OrderRequest):
    order_id  = len(orders) + 1
    new_order = {
        "order_id":      order_id,
        "customer_name": order.customer_name,
        "product_id":    order.product_id,
        "quantity":      order.quantity,
        "status":        "pending",          # Bonus: was "confirmed"
    }
    orders.append(new_order)
    return {"message": "Order placed", "order": new_order}


# ── Q3: POST /feedback ────────────────────────────────────────────────────────

@app.post("/feedback")
def submit_feedback(data: CustomerFeedback):
    """Q3: Accept validated customer feedback"""
    feedback.append(data.model_dump())
    return {
        "message":        "Feedback submitted successfully",
        "feedback":       data.model_dump(),
        "total_feedback": len(feedback),
    }


# ── Q5: POST /orders/bulk ─────────────────────────────────────────────────────

@app.post("/orders/bulk")
def place_bulk_order(order: BulkOrder):
    """Q5: Bulk order — partial success, reports confirmed and failed items"""
    confirmed, failed, grand_total = [], [], 0
    for item in order.items:
        product = next((p for p in products if p["id"] == item.product_id), None)
        if not product:
            failed.append({"product_id": item.product_id, "reason": "Product not found"})
        elif not product["in_stock"]:
            failed.append({"product_id": item.product_id, "reason": f"{product['name']} is out of stock"})
        else:
            subtotal     = product["price"] * item.quantity
            grand_total += subtotal
            confirmed.append({"product": product["name"], "qty": item.quantity, "subtotal": subtotal})
    return {
        "company":     order.company_name,
        "confirmed":   confirmed,
        "failed":      failed,
        "grand_total": grand_total,
    }


# ── Bonus: GET /orders/{order_id} ────────────────────────────────────────────

@app.get("/orders/{order_id}")
def get_order(order_id: int):
    """Bonus: Retrieve a single order by ID"""
    for order in orders:
        if order["order_id"] == order_id:
            return {"order": order}
    return {"error": "Order not found"}


# ── Bonus: PATCH /orders/{order_id}/confirm ──────────────────────────────────

@app.patch("/orders/{order_id}/confirm")
def confirm_order(order_id: int):
    """Bonus: Move a pending order to confirmed"""
    for order in orders:
        if order["order_id"] == order_id:
            order["status"] = "confirmed"
            return {"message": "Order confirmed", "order": order}
    return {"error": "Order not found"}
