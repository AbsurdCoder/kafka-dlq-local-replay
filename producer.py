"""
Kafka Producer for Error Messages
Generates and publishes mock error messages to the error_logs topic.
"""

import json
import logging
import sys
import time
from datetime import datetime, timedelta
from typing import Callable, Optional
from uuid import uuid4

from confluent_kafka import Producer
from confluent_kafka.error import KafkaError

from schema import ErrorMessage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ErrorProducer:
    """Produces error messages to Kafka."""
    
    def __init__(self, bootstrap_servers: str = "localhost:9092"):
        """
        Initialize the error producer.
        
        Args:
            bootstrap_servers: Kafka bootstrap servers address
        """
        self.bootstrap_servers = bootstrap_servers
        self.topic = "error_logs"
        
        # Configure producer
        producer_config = {
            "bootstrap.servers": bootstrap_servers,
            "client.id": "dlq-producer",
            "acks": "all",
            "retries": 3,
            "max.in.flight.requests.per.connection": 1,
        }
        
        self.producer = Producer(producer_config)
        logger.info(f"Initialized producer for {bootstrap_servers}")
    
    def delivery_report(self, err: Optional[KafkaError], msg) -> None:
        """
        Delivery report callback.
        
        Args:
            err: Error object if delivery failed
            msg: Message object
        """
        if err is not None:
            logger.error(f"Message delivery failed: {err}")
        else:
            logger.info(
                f"Message delivered to {msg.topic()} "
                f"[{msg.partition()}] at offset {msg.offset()}"
            )
    
    def produce_error(self, error_message: ErrorMessage) -> bool:
        """
        Produce an error message to Kafka.
        
        Args:
            error_message: ErrorMessage object to produce
            
        Returns:
            True if successful, False otherwise
        """
        try:
            message_json = error_message.to_json()
            
            self.producer.produce(
                topic=self.topic,
                key=error_message.error_id.encode("utf-8"),
                value=message_json.encode("utf-8"),
                callback=self.delivery_report
            )
            
            # Trigger any pending callbacks
            self.producer.poll(0)
            return True
        
        except Exception as e:
            logger.error(f"Error producing message: {e}")
            return False
    
    def flush(self, timeout: int = 10) -> None:
        """
        Flush pending messages.
        
        Args:
            timeout: Timeout in seconds
        """
        remaining = self.producer.flush(timeout)
        if remaining > 0:
            logger.warning(f"{remaining} messages were not delivered")


def create_mock_errors() -> list:
    """
    Create 10 mock error messages for testing.
    
    Returns:
        List of ErrorMessage objects
    """
    base_time = datetime.utcnow()
    
    mock_errors = [
        {
            "source_service": "payment-service",
            "error_message": "Failed to process payment: insufficient funds",
            "payload": json.dumps({
                "transaction_id": "txn_001",
                "amount": 99.99,
                "user_id": "usr_123",
                "card_last_four": "4242"
            }),
            "severity": "ERROR",
            "timestamp": (base_time - timedelta(minutes=10)).isoformat() + "Z"
        },
        {
            "source_service": "user-service",
            "error_message": "User authentication failed: invalid credentials",
            "payload": json.dumps({
                "username": "john.doe@example.com",
                "attempt_count": 3,
                "ip_address": "192.168.1.100"
            }),
            "severity": "WARNING",
            "timestamp": (base_time - timedelta(minutes=9)).isoformat() + "Z"
        },
        {
            "source_service": "order-service",
            "error_message": "Order processing timeout: database connection lost",
            "payload": json.dumps({
                "order_id": "ord_456",
                "database": "orders_db",
                "connection_time_ms": 5000
            }),
            "severity": "CRITICAL",
            "timestamp": (base_time - timedelta(minutes=8)).isoformat() + "Z"
        },
        {
            "source_service": "notification-service",
            "error_message": "Email delivery failed: SMTP server unreachable",
            "payload": json.dumps({
                "recipient": "user@example.com",
                "email_type": "order_confirmation",
                "smtp_server": "mail.example.com",
                "retry_count": 2
            }),
            "severity": "ERROR",
            "timestamp": (base_time - timedelta(minutes=7)).isoformat() + "Z"
        },
        {
            "source_service": "inventory-service",
            "error_message": "Stock update failed: concurrent modification detected",
            "payload": json.dumps({
                "product_id": "prod_789",
                "warehouse_id": "wh_01",
                "requested_quantity": 50,
                "available_quantity": 45
            }),
            "severity": "ERROR",
            "timestamp": (base_time - timedelta(minutes=6)).isoformat() + "Z"
        },
        {
            "source_service": "analytics-service",
            "error_message": "Data aggregation job failed: memory limit exceeded",
            "payload": json.dumps({
                "job_id": "job_analytics_001",
                "data_points": 1000000,
                "memory_used_mb": 2048,
                "memory_limit_mb": 1024
            }),
            "severity": "CRITICAL",
            "timestamp": (base_time - timedelta(minutes=5)).isoformat() + "Z"
        },
        {
            "source_service": "shipping-service",
            "error_message": "Shipment tracking update failed: external API timeout",
            "payload": json.dumps({
                "shipment_id": "ship_123",
                "carrier": "FedEx",
                "tracking_number": "794644906",
                "api_response_time_ms": 30000
            }),
            "severity": "WARNING",
            "timestamp": (base_time - timedelta(minutes=4)).isoformat() + "Z"
        },
        {
            "source_service": "recommendation-engine",
            "error_message": "ML model inference failed: model version mismatch",
            "payload": json.dumps({
                "user_id": "usr_456",
                "model_version": "v2.1",
                "expected_version": "v2.2",
                "inference_type": "product_recommendation"
            }),
            "severity": "ERROR",
            "timestamp": (base_time - timedelta(minutes=3)).isoformat() + "Z"
        },
        {
            "source_service": "cache-service",
            "error_message": "Redis connection failed: authentication error",
            "payload": json.dumps({
                "redis_host": "cache.internal",
                "redis_port": 6379,
                "error_code": "WRONGPASS",
                "operation": "SET"
            }),
            "severity": "CRITICAL",
            "timestamp": (base_time - timedelta(minutes=2)).isoformat() + "Z"
        },
        {
            "source_service": "reporting-service",
            "error_message": "Report generation failed: invalid query syntax",
            "payload": json.dumps({
                "report_id": "rpt_monthly_sales",
                "query": "SELECT * FROM sales WHERE date > ?",
                "error_line": 1,
                "error_column": 45
            }),
            "severity": "ERROR",
            "timestamp": (base_time - timedelta(minutes=1)).isoformat() + "Z"
        }
    ]
    
    errors = []
    for error_data in mock_errors:
        error = ErrorMessage(**error_data)
        errors.append(error)
    
    return errors


def produce_errors(
    bootstrap_servers: str = "localhost:9092",
    errors: Optional[list] = None,
    delay_between_messages: float = 0.5
) -> bool:
    """
    Produce error messages to Kafka.
    
    Args:
        bootstrap_servers: Kafka bootstrap servers
        errors: List of ErrorMessage objects (uses mock if None)
        delay_between_messages: Delay in seconds between messages
        
    Returns:
        True if all messages produced successfully
    """
    if errors is None:
        errors = create_mock_errors()
    
    producer = ErrorProducer(bootstrap_servers)
    
    logger.info(f"Starting to produce {len(errors)} error messages...")
    
    all_success = True
    for i, error in enumerate(errors, 1):
        logger.info(f"Producing message {i}/{len(errors)}: {error.error_message}")
        success = producer.produce_error(error)
        all_success = all_success and success
        
        if i < len(errors):
            time.sleep(delay_between_messages)
    
    # Flush remaining messages
    logger.info("Flushing remaining messages...")
    producer.flush()
    
    if all_success:
        logger.info(f"Successfully produced {len(errors)} error messages")
    else:
        logger.error("Some messages failed to produce")
    
    return all_success


if __name__ == "__main__":
    # Allow bootstrap servers to be passed as command-line argument
    bootstrap_servers = sys.argv[1] if len(sys.argv) > 1 else "localhost:9092"
    
    logger.info(f"Using bootstrap servers: {bootstrap_servers}")
    
    try:
        success = produce_errors(bootstrap_servers)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("Producer interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
