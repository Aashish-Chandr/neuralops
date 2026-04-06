/**
 * k6 Normal Traffic Simulation
 * Simulates realistic steady-state traffic across all 5 microservices.
 * Run: k6 run normal-traffic.js
 */
import http from "k6/http";
import { sleep, check } from "k6";
import { Counter, Rate, Trend } from "k6/metrics";

const errorRate   = new Rate("errors");
const latencyTrend = new Trend("request_latency");

export const options = {
  stages: [
    { duration: "1m",  target: 10 },   // ramp up
    { duration: "5m",  target: 10 },   // steady state
    { duration: "30s", target: 0  },   // ramp down
  ],
  thresholds: {
    http_req_failed:   ["rate<0.05"],   // <5% errors
    http_req_duration: ["p(95)<500"],   // 95th percentile < 500ms
  },
};

const BASE_URLS = {
  user:         "http://localhost:8001",
  order:        "http://localhost:8002",
  payment:      "http://localhost:8003",
  inventory:    "http://localhost:8004",
  notification: "http://localhost:8005",
};

const HEADERS = { "Content-Type": "application/json" };

function randomInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

export default function () {
  const scenario = randomInt(1, 5);

  if (scenario === 1) {
    // User login flow
    const res = http.post(`${BASE_URLS.user}/login`,
      JSON.stringify({ username: "testuser", password: "password123" }),
      { headers: HEADERS }
    );
    check(res, { "login 200": (r) => r.status === 200 });
    errorRate.add(res.status !== 200);
    latencyTrend.add(res.timings.duration);

  } else if (scenario === 2) {
    // Order creation flow
    const res = http.post(`${BASE_URLS.order}/orders`,
      JSON.stringify({ user_id: randomInt(1000, 9999), items: [{ product_id: "42", qty: 2 }] }),
      { headers: HEADERS }
    );
    check(res, { "order 201": (r) => r.status === 201 });
    errorRate.add(res.status !== 201);
    latencyTrend.add(res.timings.duration);

  } else if (scenario === 3) {
    // Payment processing
    const res = http.post(`${BASE_URLS.payment}/payments`,
      JSON.stringify({ order_id: randomInt(10000, 99999), amount: 49.99, card_token: "tok_test" }),
      { headers: HEADERS }
    );
    check(res, { "payment 200": (r) => r.status === 200 });
    errorRate.add(res.status !== 200);
    latencyTrend.add(res.timings.duration);

  } else if (scenario === 4) {
    // Inventory check
    const res = http.get(`${BASE_URLS.inventory}/inventory/${randomInt(1, 100)}`);
    check(res, { "inventory 200": (r) => r.status === 200 });
    errorRate.add(res.status !== 200);
    latencyTrend.add(res.timings.duration);

  } else {
    // Notification send
    const res = http.post(`${BASE_URLS.notification}/notify`,
      JSON.stringify({ user_id: randomInt(1000, 9999), channel: "email", message: "Your order shipped!" }),
      { headers: HEADERS }
    );
    check(res, { "notify 200": (r) => r.status === 200 });
    errorRate.add(res.status !== 200);
    latencyTrend.add(res.timings.duration);
  }

  sleep(Math.random() * 2 + 0.5);  // 0.5–2.5s think time
}
