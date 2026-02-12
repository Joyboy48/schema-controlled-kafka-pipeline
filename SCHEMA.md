## Schema Documentation – How It Really Works

### 1. What is a “schema” in this project?

In this project, a **schema** is a formal contract that describes the structure of the data sent to Kafka.

- **Format**: Apache Avro  
- **Stored in**:
  - `producer/user.avsc` in this repo
  - Confluent **Schema Registry** at runtime
- **Used by**:
  - The FastAPI producer in `producer/app.py`
  - The Avro consumer in `consumer/consumer.py`

The schema guarantees that every message on the Kafka topic has:

- The **same fields**
- The **same data types**
- A **versioned, centrally managed definition**

Without this, producers could send arbitrary JSON, and consumers would easily break when data changes.

---

### 2. The Avro schema file (`producer/user.avsc`)

Your current schema file:

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

- **`type: "record"`**: This is a structured object (similar to a class).  
- **`name` / `namespace`**: Together form a logical name: `com.example.User`.  
- **`fields`**:
  - **`userId`**: integer (required)
  - **`name`**: string (required)
  - **`email`**: string (required)
  - **`phone`**: optional string (`null` or `string`, default `null`)

Every message value sent to Kafka must **match this shape** (with `phone` optional):

```json
{
  "userId": 1,
  "name": "Ace",
  "email": "ace@example.com",
  "phone": "+1-555-0000"
}
```

If a **required** field is missing or has the wrong type, or if `phone` is neither `null` nor a string, serialization will fail **before** the message reaches Kafka.

---

### 3. How the producer uses the schema (`producer/app.py`)

Key parts from `producer/app.py`:

- **Load schema from file**:

```python
with open("user.avsc") as f:
    schema_str = f.read()
```

- **Connect to Schema Registry (inside Docker network)**:

```python
schema_registry_client = SchemaRegistryClient(
    {'url': 'http://schema-registry:8081'}
)
```

- **Create an Avro serializer bound to that schema**:

```python
avro_serializer = AvroSerializer(
    schema_registry_client,
    schema_str
)
```

- **Serialize each user record and send to Kafka**:

```python
@app.post("/users")
def publish_user(user: User):
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
```

**What actually happens during `avro_serializer(...)`:**

1. The Avro schema string (`schema_str`) is **registered** in Schema Registry for subject `users-topic-value` if it is new.  
2. Schema Registry returns a **schema ID** (an integer).  
3. The Python client encodes the message as:
   - A magic byte (to indicate Avro format)
   - The 4-byte schema ID
   - The Avro‑encoded binary payload
4. The final binary value is what is actually written to the Kafka topic.

So, messages on Kafka are **not JSON**; they are **Avro binary + schema ID**, and the schema itself lives in Schema Registry.

---

### 4. How Schema Registry organizes schemas

Schema Registry stores schemas grouped by **subject**.

- **Typical subject for value schemas**: `<topic>-value`  
- In this project, for topic `users-topic`, the subject is usually:

```text
users-topic-value
```

For each subject, Schema Registry keeps:

- **Versions**: `v1`, `v2`, `v3`, ...  
- **Compatibility mode**: whether new versions must be backward/forward compatible, etc.

You can inspect subjects:

```text
GET http://localhost:8081/subjects
```

And see specific versions and schemas:

```text
GET http://localhost:8081/subjects/users-topic-value/versions
GET http://localhost:8081/subjects/users-topic-value/versions/1
```

---

### 5. How the consumer uses the schema (`consumer/consumer.py`)

The consumer is also Avro‑aware:

```python
schema_registry_client = SchemaRegistryClient(
    {'url': 'http://schema-registry:8081'}
)

avro_deserializer = AvroDeserializer(schema_registry_client)
```

For each message:

```python
user = avro_deserializer(
    msg.value(),
    SerializationContext(msg.topic(), MessageField.VALUE)
)
```

Steps:

1. Consumer reads the message from Kafka.  
2. `AvroDeserializer` reads the magic byte and schema ID from the payload.  
3. It calls Schema Registry to fetch the corresponding schema.  
4. It decodes the Avro binary into a Python dict matching the `User` schema.

Because the schema ID is embedded in each message, consumers **do not need to hard‑code the schema**; they always decode with the exact version that was used to produce the event.

---

### 6. JSON → Avro mapping (what must match)

Example HTTP body sent to `POST /users`:

```json
{
  "userId": 1,
  "name": "Ace",
  "email": "ace@example.com",
  "phone": "+1-555-0000"
}
```

For each incoming JSON:

- **Field names** must match the Avro schema (`userId`, `name`, `email`, `phone`).  
- **Field types** must match:
  - `userId`: integer (no strings like `"1"`)  
  - `name`, `email`: strings  
  - `phone`: either a string or omitted/`null`

If you send:

```json
{
  "userId": "1",
  "name": "Ace",
  "email": "ace@example.com"
}
```

Then:

- FastAPI/Pydantic may reject it (wrong type for `userId`), or  
- Avro serialization will fail, and **no message is written** to Kafka.

This is the core of schema control: **bad or unexpected data is rejected before hitting Kafka**.

---

### 7. Schema evolution – changing schemas safely

Over time, you might want to **evolve** the `User` schema, for example by adding fields or making fields optional.

You already have one evolution pattern in place:

- `phone` is a **new optional field**:
  - Type is a union: `["null", "string"]`
  - Default value is `null`

Why this is safe under **BACKWARD compatibility**:

- Old consumers that only know about `userId`, `name`, `email` can still read messages:
  - They ignore the new `phone` field.  
- New producers can start sending `phone` without breaking old readers.

Other rules of thumb:

- **Safe changes** (usually allowed under backward compatibility):
  - Add a new field with a **default** value.
  - Make a field optional via union with `"null"` and a sensible default.
- **Dangerous changes** (often rejected by Schema Registry):
  - Removing fields without defaults.
  - Changing field types incompatibly (e.g., `int` → `string`).
  - Renaming fields without using Avro aliases.

If a new schema version is incompatible with the configured compatibility mode, **Schema Registry rejects the new schema** and your producer will fail during registration. This prevents silently breaking existing consumers.

---

### 8. Compatibility modes (high level)

Schema Registry supports several compatibility settings per subject:

- **BACKWARD**: New schema can be read by old consumers.  
- **FORWARD**: Old data can be read by new consumers.  
- **FULL**: Both backward and forward must hold.  
- **NONE**: No compatibility checks (dangerous in production).

Typical usage:

- **Development / experiments**: You may relax to `NONE` or `BACKWARD`.  
- **Production**: Prefer `BACKWARD` or `FULL` to protect consumers.

You configure this per subject via Schema Registry REST API or UI (if available).

---

### 9. How all pieces fit together

- **You define the contract** in `producer/user.avsc`.  
- **Producer (FastAPI)**:
  - Validates incoming HTTP JSON with Pydantic.
  - Serializes using Avro and Schema Registry.
  - Publishes Avro messages with embedded schema IDs to `users-topic`.
- **Kafka**:
  - Stores the raw Avro binary payloads.  
- **Consumer**:
  - Reads messages from `users-topic`.
  - Uses the schema ID to fetch the correct schema from Schema Registry.
  - Decodes the messages into Python dicts matching the `User` schema.

This is what “schema‑controlled Kafka streams” means in this project: **data is versioned, validated, and centrally governed by an Avro schema**, not just loose JSON between services.

