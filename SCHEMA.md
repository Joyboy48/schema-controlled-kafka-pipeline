## Schema Documentation – How It Really Works

### 1. What is a “schema” in this project?

In this project, a **schema** is a formal contract that describes the structure of the data sent to Kafka.

- **Format**: Apache Avro
- **Stored in**:
  - `user.avsc` in this repo
  - Confluent **Schema Registry** at runtime
- **Used by**:
  - The Python producer in `producer.py`
  - Any consumer that wants to read the messages correctly

The schema guarantees that every message on the Kafka topic has:

- The **same fields**
- The **same data types**
- A **versioned, centrally managed definition**

Without this, producers could send arbitrary JSON, and consumers would easily break when data changes.

---

### 2. The Avro schema file (`user.avsc`)

Your schema file:

```json
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
```

- **`type: "record"`**: This is a structured object (similar to a class).
- **`name` / `namespace`**: Together form a logical name: `com.example.User`.
- **`fields`**:
  - **`userId`**: integer
  - **`name`**: string
  - **`email`**: string

Every message value sent to Kafka must **match this shape**:

```json
{
  "userId": 1,
  "name": "Ace",
  "email": "ace@example.com"
}
```

If a field is missing or has the wrong type, serialization will fail **before** the message reaches Kafka.

---

### 3. How the producer uses the schema (`producer.py`)

Key parts from `producer.py`:

- **Load schema from file**:

```python
with open("user.avsc") as f:
    schema_str = f.read()
```

- **Connect to Schema Registry**:

```python
schema_registry_conf = {'url': 'http://localhost:8081'}
schema_registry_client = SchemaRegistryClient(schema_registry_conf)
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
```

**What actually happens during `avro_serializer(...)`:**

1. The Avro schema string (`schema_str`) is **registered** in Schema Registry if it is new.
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

### 5. How consumers use the schema

Even though this project currently focuses on the producer, a typical **Avro-aware consumer** does:

1. **Read the message from Kafka**:
   - Sees the magic byte + schema ID + binary payload.
2. **Ask Schema Registry** for the schema by ID.
3. **Decode the binary** Avro payload into a structured object using that schema.

Because the serializer always writes the schema ID into the message, consumers do **not** need to hard‑code the schema—they can always fetch the exact version that was used to write the data.

---

### 6. JSON → Avro mapping (what must match)

Your input file `users.json` looks like this:

```json
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
```

For each object in the list:

- **Field names** must match the Avro schema (`userId`, `name`, `email`).
- **Field types** must match:
  - `userId`: integer (no strings like `"1"`).
  - `name`, `email`: strings.

If you change the JSON like this:

```json
{
  "userId": "1",
  "name": "Ace",
  "email": "ace@example.com"
}
```

Then serialization fails because `"1"` is a string, not an `int`.

This is the core of schema control: **bad or unexpected data is rejected before hitting Kafka**.

---

### 7. Schema evolution – changing schemas safely

Over time, you might want to **evolve** the `User` schema. For example, adding a new field:

```json
{
  "name": "age",
  "type": "int",
  "default": 0
}
```

New schema:

```json
{
  "type": "record",
  "name": "User",
  "namespace": "com.example",
  "fields": [
    {"name": "userId", "type": "int"},
    {"name": "name", "type": "string"},
    {"name": "email", "type": "string"},
    {"name": "age", "type": "int", "default": 0}
  ]
}
```

If compatibility is **BACKWARD** (the common default):

- **Old consumers** (still using the old 3‑field schema) can keep reading:
  - They simply ignore the new `age` field.
- **New producers** can send the new 4‑field data.

Rules of thumb for safe evolution:

- **Safe changes** (usually allowed under backward compatibility):
  - Add a new field with a **default** value.
  - Make a field **optional** using a union with `"null"` and a default.
- **Dangerous changes** (often rejected by Schema Registry):
  - Removing fields without defaults.
  - Changing field types incompatibly (e.g., `int` → `string`).
  - Renaming fields without aliasing (advanced Avro feature).

If a new schema is incompatible with the existing one (based on the configured compatibility mode), **Schema Registry rejects it**, and your producer will fail to register/use it. This prevents silently breaking existing consumers.

---

### 8. Compatibility modes (high level)

Schema Registry supports several compatibility settings per subject:

- **BACKWARD**: New schema must be readable by old consumers.
- **FORWARD**: Old data must be readable by new consumers.
- **FULL**: Both backward and forward must hold.
- **NONE**: No compatibility checks (dangerous in production).

Typically:

- **Development / experiments**: You might temporarily use `NONE`.
- **Production**: Prefer `BACKWARD` or `FULL` to protect existing consumers.

You configure this per subject using the Schema Registry REST API or UI (if available).

---

### 9. How all pieces fit together in this project

- **You define the contract** in `user.avsc`.
- **Producer**:
  - Loads the schema.
  - Registers it with Schema Registry (or reuses an existing version).
  - Serializes each JSON user according to the schema.
  - Sends Avro‑encoded messages with schema IDs to `users-topic`.
- **Kafka**:
  - Stores the raw Avro binary payloads.
- **Consumers**:
  - Use the schema ID inside each message to fetch the correct schema from Schema Registry.
  - Decode messages safely, even as schemas evolve (within compatibility rules).

This is what “schema‑controlled Kafka streams” means in practice: **data is versioned, validated, and centrally governed by a schema**, not just free‑form JSON.

