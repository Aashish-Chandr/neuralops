"""Debug consumer — prints every message from metrics-stream. Use to verify pipeline."""
import os, json
from kafka import KafkaConsumer

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC = os.getenv("KAFKA_METRICS_TOPIC", "metrics-stream")

consumer = KafkaConsumer(
    TOPIC,
    bootstrap_servers=KAFKA_BOOTSTRAP,
    auto_offset_reset="latest",
    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    group_id="debug-consumer",
)

print(f"Listening on {TOPIC}...")
for msg in consumer:
    print(f"[{msg.partition}:{msg.offset}] {msg.value}")
