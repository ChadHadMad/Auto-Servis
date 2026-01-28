import os
import json
import time
import pika
import subprocess
import os
import smtplib
from email.message import EmailMessage

RABBIT_HOST = os.getenv("RABBIT_HOST", "rabbitmq")
RABBIT_QUEUE = os.getenv("RABBIT_QUEUE", "order_status_events")

SMTP_HOST = os.getenv("SMTP_HOST", "postfix-relay")
SMTP_PORT = int(os.getenv("SMTP_PORT", 25))
BOSS_EMAIL = os.getenv("BOSS_EMAIL", "enigmas.smm@gmail.com")


def send_email_to_boss(event: dict):
    subject = "[AUTOSERVIS] Status narudžbe promijenjen"
    body = f"""
Promjena statusa narudžbe:

ID narudžbe: {event.get('order_id')}
Novi status: {event.get('new_status')}
Datum servisa: {event.get('service_date')}

-- Automatska obavijest sustava
"""

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = os.getenv("EMAIL_FROM", "no-reply@autoservis.local")
    msg["To"] = BOSS_EMAIL
    msg.set_content(body)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.send_message(msg)
        print(f"[worker] Mail poslan za order_id={event.get('order_id')}")
    except Exception as e:
        print(f"[worker] SMTP greška: {e}")


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
            print(f"[worker] Event received: {msg}", flush=True)

            if (
            msg.get("event") == "order_status_changed"
            and msg.get("new_status") in ("finished", "cancelled")
            ):
                send_email_to_boss(msg)

            ch.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as e:
            print(f"[worker] Error: {e}", flush=True)
            # NE ACK → poruka ostaje u queueu

    channel.basic_qos(prefetch_count=10)
    channel.basic_consume(queue=RABBIT_QUEUE, on_message_callback=callback)

    channel.start_consuming()


if __name__ == "__main__":
    main()
