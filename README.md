# Kafka DLQ Error Monitoring System

A complete, modular Kafka Dead Letter Queue (DLQ) / Error Monitoring system built with Python, FastAPI, and Confluent Kafka.

## Features

- **Kafka Integration:** Uses `confluent-kafka` for robust Kafka interactions.
- **REST API:** A FastAPI backend provides endpoints for monitoring error counts and details.
- **Real-time Consumer:** A background thread consumes messages from the `error_logs` topic.
- **Data Validation:** Pydantic models ensure data integrity.
- **Dockerized Infrastructure:** A `docker-compose.yml` file for easy setup of Kafka, Zookeeper, and a Kafka UI.
- **Web UI:** A simple Flask-based UI to visualize the errors.

## Tech Stack

- **Python 3.10+**
- **confluent-kafka**: For Kafka producer and consumer.
- **FastAPI**: For the REST API.
- **uvicorn**: As the ASGI server for FastAPI.
- **pydantic**: For data validation.
- **Docker**: For containerizing the infrastructure.
- **Flask**: For the web UI.

## Project Structure

```
/home/ubuntu/kafka-dlq-system
├── docker-compose.yml
├── main.py
├── producer.py
├── README.md
├── requirements.txt
├── schema.py
├── setup.py
└── ui.py
```

## Setup and Usage

### 1. Start the Infrastructure

Open a terminal and navigate to the project directory. Run the following command to start the Kafka broker, Zookeeper, and Kafka UI:

```bash
docker-compose up -d
```

### 2. Install Dependencies

In a new terminal, install the required Python packages:

```bash
pip install -r requirements.txt
```

### 3. Create Kafka Topics

Run the `setup.py` script to create the `error_logs` topic in Kafka:

```bash
python setup.py
```

### 4. Start the FastAPI Backend

Start the FastAPI server:

```bash
python main.py
```

The API will be available at `http://localhost:8000`.

### 5. Start the Flask UI

In another terminal, start the Flask UI:

```bash
python ui.py
```

The UI will be available at `http://localhost:5000`.

### 6. Produce Test Data

To test the system, run the `producer.py` script to send 10 mock error messages to the `error_logs` topic:

```bash
python producer.py
```

You should see the errors appear in the Flask UI.

## API Endpoints

The following endpoints are available on the FastAPI backend at `http://localhost:8000`:

- `GET /errors/count`: Returns the total number of errors captured.
- `GET /errors/details?limit=10`: Returns the most recent errors up to the specified limit.
