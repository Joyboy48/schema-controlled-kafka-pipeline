## Schema‑Controlled Kafka Streams (Docker + Avro + FastAPI)

### Overview

This project demonstrates a **schema‑controlled Kafka pipeline** using:

- **Apache Kafka** (Docker)
- **Confluent Schema Registry**
- **Avro schemas**
- **FastAPI producer service** (HTTP → Kafka)
- **Python consumer service** (Kafka → console)

All Kafka messages are validated against a **central Avro schema**, enforced by Schema Registry. This guarantees:

- **Data contract enforcement**
- **Schema validation and evolution**
- **Producer–consumer compatibility**

For a deep dive into how schemas work, see `SCHEMA.md`.

---

### Architecture

- **Producer side**
  - FastAPI service in `producer/`
  - Accepts HTTP `POST /users` with JSON body
  - Serializes the request to Avro using the **user schema**
  - Registers/uses schemas from **Schema Registry**
  - Publishes Avro messages to Kafka topic `users-topic`

- **Consumer side**
  - Python service in `consumer/`
  - Subscribes to `users-topic`
  - Uses **AvroDeserializer** + Schema Registry to decode messages
  - Prints the decoded `User` events to the console

- **Infrastructure (Docker)**
  - `zookeeper` → coordinates Kafka
  - `kafka` → message broker
  - `schema-registry` → stores Avro schemas, enforces compatibility
  - `producer` → FastAPI HTTP → Kafka bridge
  - `consumer` → reads from Kafka and logs events

High‑level flow:

```text
HTTP Request (JSON User)
        ↓
FastAPI Producer (AvroSerializer)
        ↓
Schema Registry  ↔  Kafka Topic `users-topic`
        ↓
AvroDeserializer Consumer
        ↓
Console / Downstream services
```

---

### Project structure

```text
.
├── docker-compose.yml
├── README.md
├── SCHEMA.md
├── producer
│   ├── app.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── user.avsc
└── consumer
    ├── consumer.py
    ├── Dockerfile
    └── requirements.txt
```

- **`docker-compose.yml`**: Brings up Kafka, Schema Registry, producer, and consumer.
- **`producer/`**: FastAPI service that publishes user events to Kafka using Avro.
- **`consumer/`**: Long‑running consumer that reads and decodes Avro messages.
- **`SCHEMA.md`**: Detailed explanation of the Avro schema and Schema Registry.

---

### Technologies

- **Apache Kafka 7.5.0**
- **Confluent Schema Registry 7.5.0**
- **Docker Compose**
- **Python 3.12**
- **FastAPI + Uvicorn**
- **confluent-kafka[avro]**

---

### The Avro schema (`producer/user.avsc`)

Current `User` schema:

```json
{
  "type": "record",
  "name": "User",
  "namespace": "com.example",
  "fields": [
    { "name": "userId", "type": "int" },
    { "name": "name", "type": "string" },
    { "name": "email", "type": "string" },
    {
      "name": "phone",
      "type": ["null", "string"],
      "default": null
    }
  ]
}
```

- `userId`: integer (required)
- `name`: string (required)
- `email`: string (required)
- `phone`: optional string (`null` or `string`, default `null`)

Every message value on `users-topic` must conform to this shape. Invalid payloads (wrong type, missing required fields) are rejected during Avro serialization **before** they reach Kafka.

See `SCHEMA.md` for full details on **schema evolution** and **compatibility modes**.

---

### Running the stack

#### 1. Start Kafka + services

From the project root:

```bash
docker-compose down -v
docker network prune -f
docker-compose up --build
```

This will start:

- Zookeeper
- Kafka broker
- Schema Registry
- FastAPI producer (`producer` service, port `8000`)
- Avro consumer (`consumer` service)

Give it ~60 seconds for everything to become healthy.

You can verify Schema Registry:

```text
GET http://localhost:8081/subjects
```

Initially, you may see an empty `{}` until the first message is produced.

---

### Using the FastAPI producer

#### Health check

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{ "status": "Service is running" }
```

#### Publish a `User` event

Send a POST request to `POST /users`:

```bash
curl -X POST "http://localhost:8000/users" \
  -H "Content-Type: application/json" \
  -d '{
        "userId": 1,
        "name": "Ace",
        "email": "ace@example.com",
        "phone": "+1-555-0000"
      }'
```

You can omit `phone` (it will default to `null`):

```bash
curl -X POST "http://localhost:8000/users" \
  -H "Content-Type: application/json" \
  -d '{
        "userId": 2,
        "name": "Joyboy",
        "email": "joyboy@example.com"
      }'
```

If the JSON does not match the schema (e.g., `"userId": "1"` as a string), the request fails with an error and **no message is written** to Kafka.

---

### Observing the consumer

The `consumer` service runs inside Docker and logs to the container output.

You should see logs like:

```text
Consumer started. Waiting for messages...

Received User Event:
{'userId': 1, 'name': 'Ace', 'email': 'ace@example.com', 'phone': '+1-555-0000'}
----------------------------------------
Received User Event:
{'userId': 2, 'name': 'Joyboy', 'email': 'joyboy@example.com', 'phone': None}
----------------------------------------
```

If there are schema or compatibility issues, the consumer will print appropriate errors instead of silently failing.

---

### Learning outcomes

By running this project you can see, end‑to‑end:

- How to **containerize Kafka + Schema Registry** with Docker.
- How to build a **schema‑aware HTTP producer** using FastAPI and `confluent-kafka`.
- How a **consumer uses Schema Registry** to decode Avro messages.
- How **schema evolution** and optional fields (like `phone`) work in a real Kafka pipeline.

