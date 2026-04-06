#!/bin/bash
# Provision Kafka topics for NeuralOps
# Usage: ./scripts/provision_kafka_topics.sh [bootstrap-server]
# Default bootstrap server: localhost:9092

set -e

BOOTSTRAP=${1:-localhost:9092}
echo "Provisioning Kafka topics on $BOOTSTRAP..."

create_topic() {
  local topic=$1
  local partitions=${2:-3}
  local retention_ms=${3:-86400000}  # 24h default

  kafka-topics.sh --create \
    --if-not-exists \
    --bootstrap-server "$BOOTSTRAP" \
    --topic "$topic" \
    --partitions "$partitions" \
    --replication-factor 1 \
    --config retention.ms="$retention_ms" \
    --config cleanup.policy=delete

  echo "  ✓ $topic (partitions=$partitions, retention=${retention_ms}ms)"
}

# metrics-stream: high throughput, 3 partitions, 24h retention
create_topic "metrics-stream" 3 86400000

# anomaly-alerts: low volume, 1 partition, 7 day retention for audit
create_topic "anomaly-alerts" 1 604800000

echo ""
echo "Topics created. Listing:"
kafka-topics.sh --list --bootstrap-server "$BOOTSTRAP"
