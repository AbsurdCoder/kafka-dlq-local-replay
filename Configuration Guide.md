# Configuration Guide - Using Existing Kafka Cluster

This guide explains how to configure the Kafka DLQ Error Monitoring System to use your existing Zookeeper and Kafka brokers.

## Current Configuration

The system is configured to use your existing local Kafka cluster:

- **Bootstrap Servers**: `broker1:9092,broker2:9092`
- **Zookeeper**: `zookeeper:2181`

## Setup Steps

### 1. Skip Docker (Optional)

Since you have Kafka and Zookeeper already running, you can skip the `docker-compose up` step. However, keep `docker-compose.yml` for reference.

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Initialize Kafka Topics

Run the setup script to create the required topics:

```bash
python setup.py
```

This will create:
- `error_logs` topic (1 partition, replication factor 1, 7-day retention)
- `error_logs_dlq` topic (1 partition, replication factor 1, 30-day retention)

**Output should show:**
```
2024-01-15 10:30:45 - __main__ - INFO - Using bootstrap servers: broker1:9092,broker2:9092
2024-01-15 10:30:46 - __main__ - INFO - Topic 'error_logs' created successfully
2024-01-15 10:30:46 - __main__ - INFO - Topic 'error_logs_dlq' created successfully
```

### 4. Start FastAPI Backend

```bash
python main.py
```

The API will be available at `http://localhost:8000`

### 5. Start Flask UI

In another terminal:

```bash
python ui.py
```

The dashboard will be available at `http://localhost:5000`

### 6. Produce Test Data

In another terminal:

```bash
python producer.py
```

This will send 10 mock error messages to your Kafka cluster.

## Changing Bootstrap Servers

If you need to use different bootstrap servers, you have two options:

### Option 1: Pass as Command-Line Argument

```bash
# For setup.py
python setup.py broker1:9092,broker2:9092,broker3:9092

# For producer.py
python producer.py broker1:9092,broker2:9092,broker3:9092
```

### Option 2: Edit Configuration Files

Edit the default values in each file:

**setup.py (line 195):**
```python
bootstrap_servers = sys.argv[1] if len(sys.argv) > 1 else "your-broker1:9092,your-broker2:9092"
```

**producer.py (line 292):**
```python
bootstrap_servers = sys.argv[1] if len(sys.argv) > 1 else "your-broker1:9092,your-broker2:9092"
```

**main.py (line 115):**
```python
def __init__(self, error_store: ErrorStore, bootstrap_servers: str = "your-broker1:9092,your-broker2:9092"):
```

## Verifying Connection

To verify your Kafka cluster is properly configured:

1. **Check topic creation:**
   ```bash
   python setup.py
   ```

2. **Check producer connectivity:**
   ```bash
   python producer.py
   ```

3. **Check consumer connectivity:**
   ```bash
   python main.py
   ```

All should connect without errors.

## Troubleshooting

### Connection Refused

If you get "Connection refused" errors:

1. Verify Kafka brokers are running:
   ```bash
   # On your Kafka broker machine
   jps | grep Kafka
   ```

2. Verify Zookeeper is running:
   ```bash
   # On your Zookeeper machine
   jps | grep QuorumPeerMain
   ```

3. Check network connectivity:
   ```bash
   telnet broker1 9092
   telnet broker2 9092
   ```

### Topic Creation Fails

If topic creation fails:

1. Check if topics already exist:
   ```bash
   # Using kafka-topics.sh on your broker
   kafka-topics.sh --bootstrap-server broker1:9092,broker2:9092 --list
   ```

2. If topics exist, the setup script will skip creation

3. If you need to delete and recreate:
   ```bash
   kafka-topics.sh --bootstrap-server broker1:9092,broker2:9092 --delete --topic error_logs
   kafka-topics.sh --bootstrap-server broker1:9092,broker2:9092 --delete --topic error_logs_dlq
   python setup.py
   ```

### Consumer Not Receiving Messages

1. Verify messages are in the topic:
   ```bash
   kafka-console-consumer.sh --bootstrap-server broker1:9092,broker2:9092 --topic error_logs --from-beginning
   ```

2. Check consumer group status:
   ```bash
   kafka-consumer-groups.sh --bootstrap-server broker1:9092,broker2:9092 --group dlq-consumer-group --describe
   ```

## Performance Tuning

For your 2-broker setup, consider these configurations:

### Increase Partitions (Optional)

For better throughput, increase partitions:

```bash
kafka-topics.sh --bootstrap-server broker1:9092,broker2:9092 --alter --topic error_logs --partitions 2
```

Then update `setup.py` to reflect this:

```python
{
    "name": "error_logs",
    "partitions": 2,  # Changed from 1
    "replication_factor": 2,  # Changed from 1
    "config": {
        "retention.ms": "604800000",
        "cleanup.policy": "delete"
    }
}
```

### Increase Replication Factor

For better reliability:

```bash
kafka-topics.sh --bootstrap-server broker1:9092,broker2:9092 --alter --topic error_logs --replication-factor 2
```

## Docker Compose Reference

The `docker-compose.yml` file is kept for reference. If you ever want to spin up a local Kafka cluster for testing:

```bash
docker-compose up -d
```

This will start:
- Zookeeper on port 2181
- Kafka broker on port 9092
- Kafka UI on port 8080

To stop:

```bash
docker-compose down
```

## Next Steps

1. Monitor errors in the Flask dashboard at `http://localhost:5000`
2. Query the FastAPI endpoints at `http://localhost:8000/docs`
3. Extend the system with custom error producers for your services
4. Add persistent storage for long-term error history
5. Implement alerting for critical errors
