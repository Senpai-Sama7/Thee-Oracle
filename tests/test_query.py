import pika
import uuid
import json
import sys


class OracleClient:
    def __init__(self):
        # Establish connection to the synchronized RabbitMQ container
        credentials = pika.PlainCredentials("admin", "oracle_pass_2026")
        parameters = pika.ConnectionParameters(host="localhost", credentials=credentials)

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
