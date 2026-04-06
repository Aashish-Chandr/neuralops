import sys, os, time, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from base_service import create_app
from fastapi import HTTPException
from pydantic import BaseModel

app, metrics = create_app("order-service")
svc = metrics["service_name"]

class OrderRequest(BaseModel):
    user_id: int
    items: list[dict]

@app.post("/orders")
def create_order(req: OrderRequest):
    start = time.time()
    chaos = metrics["chaos"]
    if chaos and random.random() < 0.35:
        metrics["REQUEST_COUNT"].labels(service=svc, method="POST", endpoint="/orders", status="500").inc()
        raise HTTPException(status_code=500, detail="Order processing failed")
    latency = random.uniform(0.05, 0.2) if not chaos else random.uniform(0.8, 2.5)
    time.sleep(latency)
    metrics["REQUEST_LATENCY"].labels(service=svc, endpoint="/orders").observe(time.time() - start)
    metrics["REQUEST_COUNT"].labels(service=svc, method="POST", endpoint="/orders", status="201").inc()
    return {"order_id": random.randint(10000, 99999), "status": "pending", "total": round(random.uniform(10, 500), 2)}

@app.get("/orders/{order_id}")
def get_order(order_id: int):
    metrics["REQUEST_COUNT"].labels(service=svc, method="GET", endpoint="/orders", status="200").inc()
    return {"order_id": order_id, "status": random.choice(["pending", "processing", "shipped", "delivered"])}

@app.get("/orders")
def list_orders(user_id: int = 1):
    metrics["REQUEST_COUNT"].labels(service=svc, method="GET", endpoint="/orders/list", status="200").inc()
    return {"orders": [{"order_id": random.randint(10000, 99999), "status": "delivered"} for _ in range(3)]}
