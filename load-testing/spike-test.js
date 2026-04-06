/**
 * k6 Spike Test — sudden 10x traffic surge on payment-service
 * This is the primary demo scenario: spike triggers anomaly detection → auto-remediation
 * Run: k6 run spike-test.js
 */
import http from "k6/http";
import { sleep, check } from "k6";
import { Rate } from "k6/metrics";

const errorRate = new Rate("errors");

export const options = {
  stages: [
    { duration: "1m",  target: 5  },   // normal baseline
    { duration: "30s", target: 50 },   // sudden spike — 10x
    { duration: "2m",  target: 50 },   // sustained spike (anomaly should trigger here)
    { duration: "30s", target: 5  },   // drop back (remediation should have acted)
    { duration: "2m",  target: 5  },   // verify recovery
  ],
  thresholds: {
    // We EXPECT failures during the spike — that's the point
    http_req_failed: ["rate<0.8"],
  },
};

const PAYMENT_URL = "http://localhost:8003";
const HEADERS = { "Content-Type": "application/json" };

export default function () {
  const res = http.post(
    `${PAYMENT_URL}/payments`,
    JSON.stringify({
      order_id: Math.floor(Math.random() * 90000) + 10000,
      amount: parseFloat((Math.random() * 500).toFixed(2)),
      card_token: "tok_spike_test",
    }),
    { headers: HEADERS, timeout: "10s" }
  );

  check(res, {
    "status 200": (r) => r.status === 200,
    "latency < 2s": (r) => r.timings.duration < 2000,
  });

  errorRate.add(res.status !== 200);
  sleep(0.1);
}

export function handleSummary(data) {
  return {
    "spike-test-results.json": JSON.stringify(data, null, 2),
  };
}
