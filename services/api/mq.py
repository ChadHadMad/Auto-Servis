import os
import json
import pika

RABBIT_HOST = os.getenv("RABBIT_HOST", "rabbitmq")
RABBIT_QUEUE = os.getenv("RABBIT_QUEUE", "order_status_events")

def publish_status_event(payload: dict) -> None:
    """
    Publish event to RabbitMQ queue.
    """
    params = pika.ConnectionParameters(host=RABBIT_HOST)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    channel.queue_declare(queue=RABBIT_QUEUE, durable=True)

    body = json.dumps(payload).encode("utf-8")
    channel.basic_publish(
        exchange="",
        routing_key=RABBIT_QUEUE,
        body=body,
        properties=pika.BasicProperties(delivery_mode=2),  # durable
    )
    connection.close()
