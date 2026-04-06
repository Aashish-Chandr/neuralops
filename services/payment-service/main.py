import sys, os, time, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from base_service import create_app
from fastapi import HTTPException
from pydantic import BaseModel

app, metrics = create_app("payment-service")
svc = metrics["service_name"]

class PaymentRequest(BaseModel):
    order_id: int
    amount: float
    card_token: str

@app.post("/payments")
def process_payment(req: PaymentRequest):
    # Payment service intentionally has higher base latency (external gateway simulation)
    start = time.time()
    chaos = metrics["chaos"]
    if chaos and random.random() < 0.5:
        metrics["REQUEST_COUNT"].labels(service=svc, method="POST", endpoint="/payments", status="500").inc()
        raise HTTPException(status_code=500, detail="Payment gateway timeout")
    base_latency = random.uniform(0.2, 0.6)  # higher base latency
    extra = random.uniform(1.5, 5.0) if chaos else 0
    time.sleep(base_latency + extra)
    metrics["REQUEST_LATENCY"].labels(service=svc, endpoint="/payments").observe(time.time() - start)
    metrics["REQUEST_COUNT"].labels(service=svc, method="POST", endpoint="/payments", status="200").inc()
    return {
        "payment_id": random.randint(100000, 999999),
        "status": "approved",
        "amount": req.amount,
        "transaction_ref": f"TXN-{random.randint(1000000, 9999999)}"
    }

@app.get("/payments/{payment_id}")
def get_payment(payment_id: int):
    metrics["REQUEST_COUNT"].labels(service=svc, method="GET", endpoint="/payments", status="200").inc()
    return {"payment_id": payment_id, "status": "settled"}

@app.post("/refunds")
def refund(payment_id: int, amount: float):
    time.sleep(random.uniform(0.1, 0.3))
    metrics["REQUEST_COUNT"].labels(service=svc, method="POST", endpoint="/refunds", status="200").inc()
    return {"refund_id": random.randint(100000, 999999), "status": "processed"}
