import os
import json
import time
import pika

RABBIT_HOST = os.getenv("RABBIT_HOST", "rabbitmq")
RABBIT_QUEUE = os.getenv("RABBIT_QUEUE", "order_status_events")


def connect_with_retry(max_attempts: int = 30, delay_seconds: int = 2):
    params = pika.ConnectionParameters(host=RABBIT_HOST)
    last_err = None

    for attempt in range(1, max_attempts + 1):
        try:
            return pika.BlockingConnection(params)
        except Exception as e:
            last_err = e
            print(f"[worker] RabbitMQ not ready ({attempt}/{max_attempts}): {e}")
            time.sleep(delay_seconds)

    raise last_err


def main():
    connection = connect_with_retry()
    channel = connection.channel()
    channel.queue_declare(queue=RABBIT_QUEUE, durable=True)

    print(f"[worker] Listening on queue: {RABBIT_QUEUE} (host={RABBIT_HOST})", flush=True)

    def callback(ch, method, properties, body):
        try:
            msg = json.loads(body.decode("utf-8"))
        except Exception:
            msg = {"raw": body.decode("utf-8", errors="ignore")}

        print(f"[worker] Event received: {msg}", flush=True)
        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_qos(prefetch_count=10)
    channel.basic_consume(queue=RABBIT_QUEUE, on_message_callback=callback)

    channel.start_consuming()


if __name__ == "__main__":
    main()
