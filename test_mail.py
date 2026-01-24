import pika
import json

RABBIT_HOST = "rabbitmq"  # promijeni ako ti je drugačiji hostname
RABBIT_QUEUE = "order_status_events"

def send_test_events(n=5):
    params = pika.ConnectionParameters(host=RABBIT_HOST)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    channel.queue_declare(queue=RABBIT_QUEUE, durable=True)

    for i in range(n):
        event = {
            "event": "order_status_changed",
            "order_id": f"auto_{i}",
            "new_status": "finished",
            "service_date": "2026-01-24",
            "worker_id": f"radnik_{i}"
        }
        channel.basic_publish(
            exchange="",
            routing_key=RABBIT_QUEUE,
            body=json.dumps(event),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        print(f"[test] Poslana poruka za {event['order_id']} od {event['worker_id']}")

    connection.close()

if __name__ == "__main__":
    send_test_events(10)  # pošalji 10 test događaja