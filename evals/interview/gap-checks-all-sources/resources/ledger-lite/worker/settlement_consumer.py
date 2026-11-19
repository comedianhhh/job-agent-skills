"""Kafka consumer: applies settled postings to the balance read model (at-least-once)."""
from confluent_kafka import Consumer

TOPIC = "ledger.postings.settled"


def run(apply_posting, conf):
    consumer = Consumer({**conf, "group.id": "balance-read-model", "enable.auto.commit": False})
    consumer.subscribe([TOPIC])
    while True:
        msg = consumer.poll(1.0)
        if msg is None or msg.error():
            continue
        apply_posting(msg.value())  # idempotent by posting id
        consumer.commit(message=msg)
