import pika
import uuid
import json
import sys
import os


RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "localhost")
RABBITMQ_USER = os.environ.get("RABBITMQ_USER", "")
RABBITMQ_PASS = os.environ.get("RABBITMQ_PASS", "")


def require_secret(name, value):
    if not value:
        raise RuntimeError(f"{name} must be set before running this helper")


class OracleClient:
    def __init__(self):
        # Establish connection to the synchronized RabbitMQ container
        require_secret("RABBITMQ_USER", RABBITMQ_USER)
        require_secret("RABBITMQ_PASS", RABBITMQ_PASS)
        credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
        parameters = pika.ConnectionParameters(host=RABBITMQ_HOST, credentials=credentials)

        try:
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
        except Exception as e:
            print(f"[!] Critical Connection Failure: {e}")
            sys.exit(1)

        # Declare a unique, exclusive callback queue for this specific request
        result = self.channel.queue_declare(queue="", exclusive=True)
        self.callback_queue = result.method.queue
        self.channel.basic_consume(queue=self.callback_queue, on_message_callback=self.on_response, auto_ack=True)

    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            self.response = body

    def call(self, query):
        self.response = None
        self.corr_id = str(uuid.uuid4())

        # Publish request to the 'knowledge_requests' queue
        self.channel.basic_publish(
            exchange="",
            routing_key="knowledge_requests",
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=self.corr_id,
            ),
            body=json.dumps({"query": query}),
        )

        # Block until the worker process returns the result
        while self.response is None:
            self.connection.process_data_events()
        return json.loads(self.response)


if __name__ == "__main__":
    oracle = OracleClient()
    query_text = "What is the status of the initialization protocol?"
    print(f"[*] Dispatching Knowledge Request: '{query_text}'")

    response = oracle.call(query_text)
    print(f"\n[ORACLE RESPONSE]:\n{json.dumps(response, indent=2)}")
