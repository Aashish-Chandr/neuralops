import sys, os, time, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from base_service import create_app
from fastapi import HTTPException
from pydantic import BaseModel

app, metrics = create_app("notification-service")
svc = metrics["service_name"]

class NotificationRequest(BaseModel):
    user_id: int
    channel: str  # email | sms | push
    message: str

@app.post("/notify")
def send_notification(req: NotificationRequest):
    start = time.time()
    chaos = metrics["chaos"]
    if chaos and random.random() < 0.45:
        metrics["REQUEST_COUNT"].labels(service=svc, method="POST", endpoint="/notify", status="500").inc()
        raise HTTPException(status_code=500, detail="Notification provider down")
    time.sleep(random.uniform(0.01, 0.08) if not chaos else random.uniform(0.3, 1.5))
    metrics["REQUEST_LATENCY"].labels(service=svc, endpoint="/notify").observe(time.time() - start)
    metrics["REQUEST_COUNT"].labels(service=svc, method="POST", endpoint="/notify", status="200").inc()
    return {"notification_id": random.randint(1000000, 9999999), "status": "sent", "channel": req.channel}

@app.get("/notifications/{user_id}")
def get_notifications(user_id: int):
    metrics["REQUEST_COUNT"].labels(service=svc, method="GET", endpoint="/notifications", status="200").inc()
    return {"user_id": user_id, "notifications": [{"id": i, "message": f"Notification {i}", "read": False} for i in range(5)]}
