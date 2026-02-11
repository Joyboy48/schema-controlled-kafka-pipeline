📌 Schema-Controlled Kafka Streams (Docker + Avro)
📖 Overview

This project demonstrates a schema-controlled Kafka pipeline using:

Apache Kafka (Docker)

Confluent Schema Registry

Avro schemas

Python Producer

JSON → Avro → Kafka data flow

The system ensures that all Kafka messages strictly follow a predefined schema, enabling:

Data contract enforcement

Schema validation

Schema evolution support

Producer–consumer compatibility

🏗️ Architecture
JSON File
    ↓
Python Producer
    ↓ (Avro Serialization)
Schema Registry
    ↓
Kafka Topic

Components
Component	Purpose
Zookeeper	Kafka coordination
Kafka	Message broker
Schema Registry	Stores and validates Avro schemas
Python Producer	Reads JSON & publishes schema-controlled messages
📂 Project Structure
.
├── docker-compose.yml
├── producer.py
├── user.avsc
├── users.json
└── README.md

🧱 Technologies Used

Apache Kafka 7.5.0

Confluent Schema Registry 7.5.0

Docker Compose

Python 3.12

confluent-kafka (Avro serializer)

🚀 Setup Instructions
1️⃣ Start Kafka Infrastructure
docker-compose down -v
docker network prune -f
docker-compose up -d


Wait ~60 seconds for Kafka to initialize.

Verify Schema Registry:

http://localhost:8081


You should see:

{}

2️⃣ Install Python Dependencies
pip install confluent-kafka[avro]

3️⃣ Run Producer
python producer.py


Expected Output:

Message delivered to users-topic partition [0]
Message delivered to users-topic partition [0]
All messages sent successfully!

🧬 Avro Schema (user.avsc)
{
  "type": "record",
  "name": "User",
  "namespace": "com.example",
  "fields": [
    {"name": "userId", "type": "int"},
    {"name": "name", "type": "string"},
    {"name": "email", "type": "string"}
  ]
}


This schema ensures:

Strict data validation

Type enforcement

Version compatibility

Centralized schema management

🔍 How Schema Control Works

Producer reads JSON data.

Data is serialized using AvroSerializer.

Schema is registered in Schema Registry.

Kafka stores data in Avro binary format.

Consumers can retrieve schema dynamically.

Schema Registry endpoint:

GET http://localhost:8081/subjects

🔒 Why Schema-Controlled Kafka?

Without schema control:

Producers can send inconsistent data

Consumers may break on format changes

With Schema Registry:

Data contracts are enforced

Backward/forward compatibility is supported

Versioning is centralized

Production safety improves

🛠️ Kafka Listener Configuration

This setup uses dual listeners:

Listener	Used By
localhost:9092	External Python Producer
kafka:29092	Internal Docker services

This avoids common Kafka networking issues in Docker environments.

🧪 Example Input (users.json)
[
  {
    "userId": 1,
    "name": "Ace",
    "email": "ace@example.com"
  },
  {
    "userId": 2,
    "name": "Joyboy",
    "email": "joyboy@example.com"
  }
]

📈 Future Improvements

Add Kafka Consumer

Implement Kafka Streams processing

Demonstrate schema evolution (v2 schema)

Add Kafdrop UI

Add REST Proxy

Move to Java-based microservice

🎯 Learning Outcome

This project demonstrates:

Docker-based Kafka setup

Avro schema management

Schema Registry integration

JSON → Avro serialization

Distributed system networking configuration