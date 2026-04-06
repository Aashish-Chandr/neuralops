import sys, os, time, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from base_service import create_app
from fastapi import HTTPException

app, metrics = create_app("inventory-service")
svc = metrics["service_name"]

FAKE_INVENTORY = {str(i): random.randint(0, 500) for i in range(1, 101)}

@app.get("/inventory/{product_id}")
def get_stock(product_id: str):
    start = time.time()
    chaos = metrics["chaos"]
    if chaos and random.random() < 0.3:
        metrics["REQUEST_COUNT"].labels(service=svc, method="GET", endpoint="/inventory", status="503").inc()
        raise HTTPException(status_code=503, detail="Inventory DB unreachable")
    time.sleep(random.uniform(0.02, 0.1) if not chaos else random.uniform(0.5, 2.0))
    metrics["REQUEST_LATENCY"].labels(service=svc, endpoint="/inventory").observe(time.time() - start)
    metrics["REQUEST_COUNT"].labels(service=svc, method="GET", endpoint="/inventory", status="200").inc()
    qty = FAKE_INVENTORY.get(product_id, 0)
    return {"product_id": product_id, "quantity": qty, "status": "in_stock" if qty > 0 else "out_of_stock"}

@app.put("/inventory/{product_id}/reserve")
def reserve_stock(product_id: str, quantity: int = 1):
    metrics["REQUEST_COUNT"].labels(service=svc, method="PUT", endpoint="/inventory/reserve", status="200").inc()
    return {"product_id": product_id, "reserved": quantity, "status": "reserved"}

@app.get("/inventory")
def list_inventory():
    metrics["REQUEST_COUNT"].labels(service=svc, method="GET", endpoint="/inventory/list", status="200").inc()
    return {"items": [{"product_id": k, "quantity": v} for k, v in list(FAKE_INVENTORY.items())[:10]]}
