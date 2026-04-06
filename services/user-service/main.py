import sys, os, time, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from base_service import create_app
from fastapi import HTTPException
from pydantic import BaseModel

app, metrics = create_app("user-service")
svc = metrics["service_name"]

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

@app.post("/login")
def login(req: LoginRequest):
    start = time.time()
    chaos = metrics["chaos"]
    if chaos and random.random() < 0.4:
        metrics["REQUEST_COUNT"].labels(service=svc, method="POST", endpoint="/login", status="500").inc()
        raise HTTPException(status_code=500, detail="Auth service unavailable")
    latency = random.uniform(0.05, 0.15) if not chaos else random.uniform(0.5, 3.0)
    time.sleep(latency)
    metrics["REQUEST_LATENCY"].labels(service=svc, endpoint="/login").observe(time.time() - start)
    metrics["REQUEST_COUNT"].labels(service=svc, method="POST", endpoint="/login", status="200").inc()
    return {"token": "fake-jwt-token", "user_id": random.randint(1000, 9999)}

@app.post("/register")
def register(req: RegisterRequest):
    start = time.time()
    chaos = metrics["chaos"]
    latency = random.uniform(0.05, 0.2) if not chaos else random.uniform(1.0, 4.0)
    time.sleep(latency)
    metrics["REQUEST_LATENCY"].labels(service=svc, endpoint="/register").observe(time.time() - start)
    metrics["REQUEST_COUNT"].labels(service=svc, method="POST", endpoint="/register", status="201").inc()
    return {"user_id": random.randint(1000, 9999), "status": "created"}

@app.get("/users/{user_id}")
def get_user(user_id: int):
    metrics["REQUEST_COUNT"].labels(service=svc, method="GET", endpoint="/users", status="200").inc()
    return {"user_id": user_id, "username": f"user_{user_id}", "email": f"user_{user_id}@example.com"}
