from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from confluent_kafka import Producer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer
from confluent_kafka.serialization import SerializationContext, MessageField

app = FastAPI(title="User Kafka Producer Service")

# Load Avro schema
with open("user.avsc") as f:
    schema_str = f.read()

# Schema Registry
schema_registry_client = SchemaRegistryClient(
    {'url': 'http://localhost:8081'}
)

avro_serializer = AvroSerializer(
    schema_registry_client,
    schema_str
)

# Kafka Producer
producer = Producer({
    'bootstrap.servers': 'localhost:9092'
})

# Pydantic model for request validation
class User(BaseModel):
    userId: int
    name: str
    email: str

# Delivery callback
def delivery_report(err, msg):
    if err:
        print(f"Delivery failed: {err}")
    else:
        print(f"Message delivered to {msg.topic()} partition [{msg.partition()}]")

@app.get("/health")
def health_check():
    return {"status": "Service is running"}

@app.post("/users")
def publish_user(user: User):
    try:
        serialized_value = avro_serializer(
            user.dict(),
            SerializationContext("users-topic", MessageField.VALUE)
        )

        producer.produce(
            topic="users-topic",
            value=serialized_value,
            on_delivery=delivery_report
        )

        producer.flush()

        return {"status": "User event published successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
