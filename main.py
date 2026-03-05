"""
FastAPI Backend with Kafka Consumer
Provides REST endpoints for error monitoring and dead letter queue management.
"""

import json
import logging
import threading
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, List, Optional

from confluent_kafka import Consumer, KafkaError
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from schema import ErrorMessage, ErrorCountResponse, ErrorResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ErrorStore:
    """Thread-safe in-memory store for error messages."""
    
    def __init__(self, max_size: int = 10000):
        """
        Initialize error store.
        
        Args:
            max_size: Maximum number of errors to store
        """
        self.max_size = max_size
        self.errors: List[ErrorMessage] = []
        self.lock = threading.RLock()
        self.stats = {
            "total_received": 0,
            "by_severity": defaultdict(int),
            "by_service": defaultdict(int)
        }
    
    def add_error(self, error: ErrorMessage) -> None:
        """
        Add an error to the store.
        
        Args:
            error: ErrorMessage object to add
        """
        with self.lock:
            self.errors.append(error)
            
            # Maintain max size by removing oldest errors
            if len(self.errors) > self.max_size:
                self.errors = self.errors[-self.max_size:]
            
            # Update statistics
            self.stats["total_received"] += 1
            self.stats["by_severity"][error.severity] += 1
            self.stats["by_service"][error.source_service] += 1
    
    def get_errors(self, limit: int = 10) -> List[ErrorMessage]:
        """
        Get most recent errors.
        
        Args:
            limit: Maximum number of errors to return
            
        Returns:
            List of ErrorMessage objects (most recent first)
        """
        with self.lock:
            return list(reversed(self.errors[-limit:]))
    
    def get_count(self) -> int:
        """
        Get total number of errors in store.
        
        Returns:
            Total error count
        """
        with self.lock:
            return len(self.errors)
    
    def get_stats(self) -> dict:
        """
        Get error statistics.
        
        Returns:
            Dictionary with error statistics
        """
        with self.lock:
            return {
                "total_count": len(self.errors),
                "total_received": self.stats["total_received"],
                "by_severity": dict(self.stats["by_severity"]),
                "by_service": dict(self.stats["by_service"])
            }
    
    def clear(self) -> None:
        """Clear all errors from store."""
        with self.lock:
            self.errors.clear()


class KafkaConsumerThread(threading.Thread):
    """Background thread for consuming Kafka messages."""
    
    def __init__(self, error_store: ErrorStore, bootstrap_servers: str = "localhost:9092"):
        """
        Initialize consumer thread.
        
        Args:
            error_store: ErrorStore instance to write to
            bootstrap_servers: Kafka bootstrap servers
        """
        super().__init__(daemon=True)
        self.error_store = error_store
        self.bootstrap_servers = bootstrap_servers
        self.running = False
        self.consumer = None
    
    def run(self) -> None:
        """Main consumer loop."""
        try:
            consumer_config = {
                "bootstrap.servers": self.bootstrap_servers,
                "group.id": "dlq-consumer-group",
                "auto.offset.reset": "earliest",
                "enable.auto.commit": True,
                "session.timeout.ms": 6000,
                "client.id": "dlq-consumer"
            }
            
            self.consumer = Consumer(consumer_config)
            self.consumer.subscribe(["error_logs"])
            
            logger.info("Kafka consumer started, listening to error_logs topic")
            self.running = True
            
            while self.running:
                msg = self.consumer.poll(timeout=1.0)
                
                if msg is None:
                    continue
                
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        logger.debug("Reached end of partition")
                    else:
                        logger.error(f"Consumer error: {msg.error()}")
                    continue
                
                try:
                    # Decode message
                    message_value = msg.value().decode("utf-8")
                    
                    # Parse error message
                    error = ErrorMessage.from_json(message_value)
                    
                    # Add to store
                    self.error_store.add_error(error)
                    
                    logger.info(
                        f"Received error from {error.source_service}: {error.error_message}"
                    )
                
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode message JSON: {e}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
        
        except Exception as e:
            logger.error(f"Consumer thread error: {e}", exc_info=True)
        
        finally:
            if self.consumer:
                self.consumer.close()
            logger.info("Kafka consumer stopped")
    
    def stop(self) -> None:
        """Stop the consumer thread."""
        self.running = False


# Global error store
error_store = ErrorStore()
consumer_thread: Optional[KafkaConsumerThread] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    global consumer_thread
    
    # Startup
    logger.info("Starting FastAPI application")
    consumer_thread = KafkaConsumerThread(error_store)
    consumer_thread.start()
    
    # Give consumer time to connect
    time.sleep(2)
    
    yield
    
    # Shutdown
    logger.info("Shutting down FastAPI application")
    if consumer_thread:
        consumer_thread.stop()
        consumer_thread.join(timeout=5)


# Create FastAPI app
app = FastAPI(
    title="Kafka DLQ Error Monitoring System",
    description="REST API for monitoring and managing Kafka Dead Letter Queue errors",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Response models
class ErrorDetailResponse(BaseModel):
    """Response model for error details."""
    error_id: str
    source_service: str
    error_message: str
    payload: dict
    timestamp: str
    retry_count: int
    severity: str


class ErrorListResponse(BaseModel):
    """Response model for error list."""
    count: int
    errors: List[ErrorDetailResponse]


class ErrorStatsResponse(BaseModel):
    """Response model for error statistics."""
    total_count: int
    total_received: int
    by_severity: Dict[str, int]
    by_service: Dict[str, int]


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "consumer_running": consumer_thread is not None and consumer_thread.is_alive()
    }


# Error count endpoint
@app.get("/errors/count", response_model=Dict, tags=["Errors"])
async def get_error_count():
    """
    Get total number of errors captured.
    
    Returns:
        Total error count
    """
    count = error_store.get_count()
    return {
        "count": count,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


# Error details endpoint
@app.get("/errors/details", response_model=ErrorListResponse, tags=["Errors"])
async def get_error_details(limit: int = Query(10, ge=1, le=1000)):
    """
    Get most recent errors.
    
    Args:
        limit: Maximum number of errors to return (default: 10, max: 1000)
        
    Returns:
        List of error details
    """
    errors = error_store.get_errors(limit)
    
    error_responses = []
    for error in errors:
        try:
            payload = json.loads(error.payload)
        except json.JSONDecodeError:
            payload = {}
        
        error_responses.append(
            ErrorDetailResponse(
                error_id=error.error_id,
                source_service=error.source_service,
                error_message=error.error_message,
                payload=payload,
                timestamp=error.timestamp,
                retry_count=error.retry_count,
                severity=error.severity
            )
        )
    
    return ErrorListResponse(
        count=len(error_responses),
        errors=error_responses
    )


# Error statistics endpoint
@app.get("/errors/stats", response_model=ErrorStatsResponse, tags=["Errors"])
async def get_error_stats():
    """
    Get error statistics.
    
    Returns:
        Error statistics including counts by severity and service
    """
    stats = error_store.get_stats()
    return ErrorStatsResponse(**stats)


# Error by service endpoint
@app.get("/errors/by-service/{service_name}", response_model=ErrorListResponse, tags=["Errors"])
async def get_errors_by_service(
    service_name: str,
    limit: int = Query(10, ge=1, le=1000)
):
    """
    Get errors from a specific service.
    
    Args:
        service_name: Name of the service to filter by
        limit: Maximum number of errors to return
        
    Returns:
        List of errors from the specified service
    """
    all_errors = error_store.get_errors(limit=10000)
    filtered_errors = [
        e for e in all_errors
        if e.source_service.lower() == service_name.lower()
    ][-limit:]
    
    error_responses = []
    for error in filtered_errors:
        try:
            payload = json.loads(error.payload)
        except json.JSONDecodeError:
            payload = {}
        
        error_responses.append(
            ErrorDetailResponse(
                error_id=error.error_id,
                source_service=error.source_service,
                error_message=error.error_message,
                payload=payload,
                timestamp=error.timestamp,
                retry_count=error.retry_count,
                severity=error.severity
            )
        )
    
    return ErrorListResponse(
        count=len(error_responses),
        errors=error_responses
    )


# Error by severity endpoint
@app.get("/errors/by-severity/{severity}", response_model=ErrorListResponse, tags=["Errors"])
async def get_errors_by_severity(
    severity: str,
    limit: int = Query(10, ge=1, le=1000)
):
    """
    Get errors by severity level.
    
    Args:
        severity: Severity level (INFO, WARNING, ERROR, CRITICAL)
        limit: Maximum number of errors to return
        
    Returns:
        List of errors with the specified severity
    """
    valid_severities = {"INFO", "WARNING", "ERROR", "CRITICAL"}
    if severity.upper() not in valid_severities:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid severity. Must be one of {valid_severities}"
        )
    
    all_errors = error_store.get_errors(limit=10000)
    filtered_errors = [
        e for e in all_errors
        if e.severity.upper() == severity.upper()
    ][-limit:]
    
    error_responses = []
    for error in filtered_errors:
        try:
            payload = json.loads(error.payload)
        except json.JSONDecodeError:
            payload = {}
        
        error_responses.append(
            ErrorDetailResponse(
                error_id=error.error_id,
                source_service=error.source_service,
                error_message=error.error_message,
                payload=payload,
                timestamp=error.timestamp,
                retry_count=error.retry_count,
                severity=error.severity
            )
        )
    
    return ErrorListResponse(
        count=len(error_responses),
        errors=error_responses
    )


# Clear errors endpoint (for testing)
@app.post("/errors/clear", tags=["Errors"])
async def clear_errors():
    """
    Clear all errors from store (for testing purposes).
    
    Returns:
        Confirmation message
    """
    error_store.clear()
    return {
        "message": "All errors cleared",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
