# Quick Start Guide

Get the Kafka DLQ Error Monitoring System up and running in 5 minutes.

## Prerequisites

- Docker and Docker Compose installed
- Python 3.10 or higher
- pip package manager

## Step 1: Start Docker Infrastructure (1 minute)

```bash
cd /home/ubuntu/kafka-dlq-system
docker-compose up -d
```

Wait for containers to be healthy:

```bash
docker-compose ps
```

You should see:
- `zookeeper` running on port 2181
- `kafka` running on port 9092
- `kafka-ui` running on port 8080

## Step 2: Install Python Dependencies (1 minute)

```bash
pip install -r requirements.txt
```

## Step 3: Initialize Kafka Topics (30 seconds)

```bash
python setup.py
```

Expected output:
```
2024-01-15 10:30:45 - __main__ - INFO - Initialized AdminClient for localhost:9092
2024-01-15 10:30:46 - __main__ - INFO - Topic 'error_logs' created successfully
2024-01-15 10:30:46 - __main__ - INFO - Topic 'error_logs_dlq' created successfully
```

## Step 4: Start FastAPI Backend (30 seconds)

Open a new terminal and run:

```bash
python main.py
```

Expected output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

The API is now available at `http://localhost:8000`

## Step 5: Start Flask UI (30 seconds)

Open another terminal and run:

```bash
python ui.py
```

Expected output:
```
INFO:     Starting Flask UI on http://0.0.0.0:5000
```

The UI is now available at `http://localhost:5000`

## Step 6: Produce Test Data (30 seconds)

Open yet another terminal and run:

```bash
python producer.py
```

Expected output:
```
2024-01-15 10:35:00 - producer - INFO - Starting to produce 10 error messages...
2024-01-15 10:35:00 - producer - INFO - Producing message 1/10: Failed to process payment: insufficient funds
2024-01-15 10:35:00 - producer - INFO - Message delivered to error_logs [0] at offset 0
...
2024-01-15 10:35:05 - producer - INFO - Successfully produced 10 error messages
```

## Step 7: View Results

Open your browser and navigate to:

- **Dashboard**: http://localhost:5000
- **API Docs**: http://localhost:8000/docs
- **Kafka UI**: http://localhost:8080

You should see:
- 10 errors displayed in the dashboard
- Error statistics by severity and service
- Real-time updates every 5 seconds

## Testing the API

### Get Error Count

```bash
curl http://localhost:8000/errors/count
```

Response:
```json
{
  "count": 10,
  "timestamp": "2024-01-15T10:35:10.123456Z"
}
```

### Get Error Details

```bash
curl "http://localhost:8000/errors/details?limit=5"
```

### Get Error Statistics

```bash
curl http://localhost:8000/errors/stats
```

### Get Errors by Service

```bash
curl http://localhost:8000/errors/by-service/payment-service
```

### Get Errors by Severity

```bash
curl http://localhost:8000/errors/by-severity/CRITICAL
```

## Troubleshooting

### Kafka Connection Issues

If you get "Connection refused" errors:

1. Check if Docker containers are running:
   ```bash
   docker-compose ps
   ```

2. Check Kafka logs:
   ```bash
   docker-compose logs kafka
   ```

3. Restart containers:
   ```bash
   docker-compose restart
   ```

### Python Import Errors

If you get import errors:

1. Verify Python version:
   ```bash
   python --version
   ```

2. Reinstall dependencies:
   ```bash
   pip install --upgrade -r requirements.txt
   ```

### Port Already in Use

If ports are already in use, modify `docker-compose.yml` or the Python scripts:

- Kafka: Change port 9092
- FastAPI: Change port 8000 in `main.py`
- Flask: Change port 5000 in `ui.py`

## Stopping the System

To stop all services:

```bash
# Stop FastAPI (Ctrl+C in terminal)
# Stop Flask (Ctrl+C in terminal)
# Stop Docker containers
docker-compose down
```

## Next Steps

1. Read the [Architecture Documentation](ARCHITECTURE.md)
2. Explore the [Full README](README.md)
3. Modify the schema in `schema.py` for your error types
4. Create custom error producers for your services
5. Deploy to production with persistent storage

## Support

For issues or questions, refer to:
- [Confluent Kafka Documentation](https://docs.confluent.io/kafka-clients/python/current/overview.html)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Flask Documentation](https://flask.palletsprojects.com/)
