/**
 * k6 Stress Test — gradual ramp to find breaking point
 * Run: k6 run stress-test.js
 */
import http from "k6/http";
import { sleep, check } from "k6";
import { Rate, Trend } from "k6/metrics";

const errorRate    = new Rate("errors");
const latency      = new Trend("latency_ms");

export const options = {
  stages: [
    { duration: "2m",  target: 10  },
    { duration: "2m",  target: 25  },
    { duration: "2m",  target: 50  },
    { duration: "2m",  target: 100 },
    { duration: "2m",  target: 150 },
    { duration: "2m",  target: 200 },  // likely breaking point
    { duration: "3m",  target: 0   },  // recovery
  ],
  thresholds: {
    http_req_failed:   ["rate<0.5"],
    http_req_duration: ["p(99)<5000"],
  },
};

const SERVICES = [
  "http://localhost:8001",
  "http://localhost:8002",
  "http://localhost:8003",
  "http://localhost:8004",
  "http://localhost:8005",
];

const ENDPOINTS = [
  { method: "GET",  path: "/health" },
  { method: "GET",  path: "/health" },
  { method: "GET",  path: "/health" },
];

export default function () {
  const base = SERVICES[Math.floor(Math.random() * SERVICES.length)];
  const res  = http.get(`${base}/health`, { timeout: "5s" });

  check(res, { "healthy": (r) => r.status === 200 });
  errorRate.add(res.status !== 200);
  latency.add(res.timings.duration);

  sleep(0.05);
}

export function handleSummary(data) {
  return {
    "stress-test-results.json": JSON.stringify(data, null, 2),
  };
}
