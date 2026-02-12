from confluent_kafka import Consumer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroDeserializer
from confluent_kafka.serialization import SerializationContext, MessageField

# Schema Registry config
schema_registry_client = SchemaRegistryClient(
    {'url': 'http://localhost:8081'}
)

# Avro Deserializer
avro_deserializer = AvroDeserializer(
    schema_registry_client
)

# Kafka Consumer config
consumer_conf = {
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'user-consumer-group',
    'auto.offset.reset': 'earliest'
}

consumer = Consumer(consumer_conf)
consumer.subscribe(['users-topic'])

print("Consumer started. Waiting for messages...\n")

try:
    while True:
        msg = consumer.poll(1.0)

        if msg is None:
            continue

        if msg.error():
            print(f"Consumer error: {msg.error()}")
            continue

        user = avro_deserializer(
            msg.value(),
            SerializationContext(msg.topic(), MessageField.VALUE)
        )

        print("Received User Event:")
        print(user)
        print("-" * 40)

except KeyboardInterrupt:
    print("Stopping consumer...")

finally:
    consumer.close()
