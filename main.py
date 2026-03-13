from fastapi import FastAPI, Query, Response, status
from pydantic import BaseModel, Field
from typing import Optional, List

app = FastAPI(title="FastAPI Day 4 Assignment")

# ── Sample Data ───────────────────────────────────────────────────────────────

products = [
    {"id": 1, "name": "Wireless Mouse", "price": 499, "category": "Electronics", "in_stock": True},
    {"id": 2, "name": "Notebook",       "price": 99,  "category": "Stationery",  "in_stock": True},
    {"id": 3, "name": "USB Hub",        "price": 799, "category": "Electronics", "in_stock": False},
    {"id": 4, "name": "Pen Set",        "price": 49,  "category": "Stationery",  "in_stock": True},
]

orders   = []
feedback = []

# ── Pydantic Models ───────────────────────────────────────────────────────────

class NewProduct(BaseModel):
    name:     str  = Field(..., min_length=1)
    price:    int  = Field(..., gt=0)
    category: str  = Field(..., min_length=1)
    in_stock: bool = True

class OrderRequest(BaseModel):
    customer_name: str = Field(..., min_length=2)
    product_id:    int = Field(..., gt=0)
    quantity:      int = Field(..., gt=0, le=100)

class CustomerFeedback(BaseModel):
    customer_name: str           = Field(..., min_length=2, max_length=100)
    product_id:    int           = Field(..., gt=0)
    rating:        int           = Field(..., ge=1, le=5)
    comment:       Optional[str] = Field(None, max_length=300)

class OrderItem(BaseModel):
    product_id: int = Field(..., gt=0)
    quantity:   int = Field(..., gt=0, le=50)

class BulkOrder(BaseModel):
    company_name:  str             = Field(..., min_length=2)
    contact_email: str             = Field(..., min_length=5)
    items:         List[OrderItem] = Field(..., min_length=1)

# ── Helper ────────────────────────────────────────────────────────────────────

def find_product(product_id: int):
    return next((p for p in products if p["id"] == product_id), None)

# ── Base Endpoints ────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "Welcome to the FastAPI store!"}

@app.get("/products")
def get_products():
    return {"products": products, "total": len(products)}

# ══════════════════════════════════════════════════════════════════════════════
# IMPORTANT: All fixed /products/... routes MUST come before /products/{id}
# ══════════════════════════════════════════════════════════════════════════════

# ── Q5: Inventory Audit ───────────────────────────────────────────────────────

@app.get("/products/audit")
def product_audit():
    """Q5: Store manager inventory audit"""
    in_stock_list  = [p for p in products if     p["in_stock"]]
    out_stock_list = [p for p in products if not p["in_stock"]]
    stock_value    = sum(p["price"] * 10 for p in in_stock_list)
    priciest       = max(products, key=lambda p: p["price"])
    return {
        "total_products":     len(products),
        "in_stock_count":     len(in_stock_list),
        "out_of_stock_names": [p["name"] for p in out_stock_list],
        "total_stock_value":  stock_value,
        "most_expensive":     {"name": priciest["name"], "price": priciest["price"]},
    }

# ── Summary (Day 2 Q4) ────────────────────────────────────────────────────────

@app.get("/products/summary")
def product_summary():
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

# ── Filter (Day 2 Q1) ─────────────────────────────────────────────────────────

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

# ── Bonus: Category-Wide Discount ────────────────────────────────────────────

@app.put("/products/discount")
def bulk_discount(
    category:         str = Query(..., description="Category to discount"),
    discount_percent: int = Query(..., ge=1, le=99, description="Discount %"),
):
    """Bonus: Apply a % discount to all products in a category"""
    updated = []
    for p in products:
        if p["category"].lower() == category.lower():
            p["price"] = int(p["price"] * (1 - discount_percent / 100))
            updated.append(p)
    if not updated:
        return {"message": f"No products found in category: {category}"}
    return {
        "message":          f"{discount_percent}% discount applied to {category}",
        "updated_count":    len(updated),
        "updated_products": updated,
    }

# ══════════════════════════════════════════════════════════════════════════════
# Dynamic routes — always AFTER fixed routes
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/products/{product_id}")
def get_product(product_id: int, response: Response):
    product = find_product(product_id)
    if not product:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"error": "Product not found"}
    return {"product": product}

# ── Day 2 Q2 ─────────────────────────────────────────────────────────────────

@app.get("/products/{product_id}/price")
def get_product_price(product_id: int, response: Response):
    product = find_product(product_id)
    if not product:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"error": "Product not found"}
    return {"name": product["name"], "price": product["price"]}

# ── Q1: Add New Product ───────────────────────────────────────────────────────

@app.post("/products")
def add_product(new_product: NewProduct, response: Response):
    """Q1: Add a product — returns 400 on duplicate name, 201 on success"""
    for p in products:
        if p["name"].lower() == new_product.name.lower():
            response.status_code = status.HTTP_400_BAD_REQUEST
            return {"error": f"Product '{new_product.name}' already exists"}

    next_id = max(p["id"] for p in products) + 1
    product = {
        "id":       next_id,
        "name":     new_product.name,
        "price":    new_product.price,
        "category": new_product.category,
        "in_stock": new_product.in_stock,
    }
    products.append(product)
    response.status_code = status.HTTP_201_CREATED
    return {"message": "Product added", "product": product}

# ── Q2: Update Product ────────────────────────────────────────────────────────

@app.put("/products/{product_id}")
def update_product(
    product_id: int,
    response:   Response,
    price:      Optional[int]  = Query(None, gt=0,  description="New price"),
    in_stock:   Optional[bool] = Query(None,        description="Stock status"),
    name:       Optional[str]  = Query(None,        description="New name"),
    category:   Optional[str]  = Query(None,        description="New category"),
):
    """Q2: Update price, stock, name, or category — supports multiple at once"""
    product = find_product(product_id)
    if not product:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"error": "Product not found"}

    if price    is not None: product["price"]    = price
    if in_stock is not None: product["in_stock"] = in_stock
    if name     is not None: product["name"]     = name
    if category is not None: product["category"] = category

    return {"message": "Product updated", "product": product}

# ── Q3: Delete Product ────────────────────────────────────────────────────────

@app.delete("/products/{product_id}")
def delete_product(product_id: int, response: Response):
    """Q3: Delete a product — returns 404 if not found"""
    product = find_product(product_id)
    if not product:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"error": "Product not found"}
    products.remove(product)
    return {"message": f"Product '{product['name']}' deleted"}

# ── Orders ────────────────────────────────────────────────────────────────────

@app.post("/orders")
def place_order(order: OrderRequest):
    order_id  = len(orders) + 1
    new_order = {
        "order_id":      order_id,
        "customer_name": order.customer_name,
        "product_id":    order.product_id,
        "quantity":      order.quantity,
        "status":        "pending",
    }
    orders.append(new_order)
    return {"message": "Order placed", "order": new_order}

@app.get("/orders/{order_id}")
def get_order(order_id: int):
    for order in orders:
        if order["order_id"] == order_id:
            return {"order": order}
    return {"error": "Order not found"}

@app.patch("/orders/{order_id}/confirm")
def confirm_order(order_id: int):
    for order in orders:
        if order["order_id"] == order_id:
            order["status"] = "confirmed"
            return {"message": "Order confirmed", "order": order}
    return {"error": "Order not found"}

# ── Feedback ──────────────────────────────────────────────────────────────────

@app.post("/feedback")
def submit_feedback(data: CustomerFeedback):
    feedback.append(data.model_dump())
    return {
        "message":        "Feedback submitted successfully",
        "feedback":       data.model_dump(),
        "total_feedback": len(feedback),
    }

# ── Bulk Orders ───────────────────────────────────────────────────────────────

@app.post("/orders/bulk")
def place_bulk_order(order: BulkOrder):
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
