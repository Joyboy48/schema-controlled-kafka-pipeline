import json
from confluent_kafka import Producer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer
from confluent_kafka.serialization import SerializationContext, MessageField

# Load Avro schema
with open("user.avsc") as f:
    schema_str = f.read()

# Schema Registry configuration
schema_registry_conf = {
    'url': 'http://localhost:8081'
}

schema_registry_client = SchemaRegistryClient(schema_registry_conf)

avro_serializer = AvroSerializer(
    schema_registry_client,
    schema_str
)

# Kafka Producer configuration
producer_conf = {
    'bootstrap.servers': 'localhost:9092'
}

producer = Producer(producer_conf)

# Delivery callback
def delivery_report(err, msg):
    if err:
        print(f"Delivery failed: {err}")
    else:
        print(f"Message delivered to {msg.topic()} partition [{msg.partition()}]")

# Read JSON input
with open("users.json") as f:
    users = json.load(f)

# Produce messages
for user in users:
    serialized_value = avro_serializer(
        user,
        SerializationContext("users-topic", MessageField.VALUE)
    )

    producer.produce(
        topic="users-topic",
        value=serialized_value,
        on_delivery=delivery_report
    )

producer.flush()
print("All messages sent successfully!")
