"""
Kafka Topic Setup and Initialization
Automatically creates required topics if they don't exist.
"""

import logging
import sys
from typing import List

from confluent_kafka.admin import AdminClient, ConfigResource, ConfigSource, NewTopic

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class KafkaTopicManager:
    """Manages Kafka topic creation and configuration."""
    
    def __init__(self, bootstrap_servers: str = "localhost:9092"):
        """
        Initialize the topic manager.
        
        Args:
            bootstrap_servers: Kafka bootstrap servers address
        """
        self.bootstrap_servers = bootstrap_servers
        self.admin_client = AdminClient({
            "bootstrap.servers": bootstrap_servers,
            "client.id": "dlq-setup-client"
        })
        logger.info(f"Initialized AdminClient for {bootstrap_servers}")
    
    def topic_exists(self, topic_name: str) -> bool:
        """
        Check if a topic exists.
        
        Args:
            topic_name: Name of the topic to check
            
        Returns:
            True if topic exists, False otherwise
        """
        try:
            metadata = self.admin_client.list_topics(timeout=10)
            return topic_name in metadata.topics
        except Exception as e:
            logger.error(f"Error checking topic existence: {e}")
            return False
    
    def create_topic(
        self,
        topic_name: str,
        num_partitions: int = 1,
        replication_factor: int = 1,
        config: dict = None
    ) -> bool:
        """
        Create a Kafka topic.
        
        Args:
            topic_name: Name of the topic
            num_partitions: Number of partitions
            replication_factor: Replication factor
            config: Additional topic configuration
            
        Returns:
            True if successful, False otherwise
        """
        if self.topic_exists(topic_name):
            logger.info(f"Topic '{topic_name}' already exists")
            return True
        
        try:
            topic_config = config or {}
            new_topic = NewTopic(
                topic=topic_name,
                num_partitions=num_partitions,
                replication_factor=replication_factor,
                config=topic_config
            )
            
            fs = self.admin_client.create_topics([new_topic], validate_only=False)
            
            for topic, f in fs.items():
                try:
                    f.result()  # The result itself is None
                    logger.info(f"Topic '{topic}' created successfully")
                except Exception as e:
                    logger.error(f"Failed to create topic '{topic}': {e}")
                    return False
            
            return True
        
        except Exception as e:
            logger.error(f"Error creating topic: {e}")
            return False
    
    def create_topics(self, topics: List[dict]) -> bool:
        """
        Create multiple topics.
        
        Args:
            topics: List of topic configurations
                   Each config should have: name, partitions, replication_factor
                   
        Returns:
            True if all topics created successfully
        """
        all_success = True
        
        for topic_config in topics:
            topic_name = topic_config.get("name")
            partitions = topic_config.get("partitions", 1)
            replication = topic_config.get("replication_factor", 1)
            config = topic_config.get("config", {})
            
            success = self.create_topic(
                topic_name,
                num_partitions=partitions,
                replication_factor=replication,
                config=config
            )
            
            all_success = all_success and success
        
        return all_success
    
    def list_topics(self) -> List[str]:
        """
        List all topics in the cluster.
        
        Returns:
            List of topic names
        """
        try:
            metadata = self.admin_client.list_topics(timeout=10)
            return list(metadata.topics.keys())
        except Exception as e:
            logger.error(f"Error listing topics: {e}")
            return []


def initialize_dlq_topics(bootstrap_servers: str = "localhost:9092") -> bool:
    """
    Initialize all required DLQ topics.
    
    Args:
        bootstrap_servers: Kafka bootstrap servers
        
    Returns:
        True if all topics initialized successfully
    """
    manager = KafkaTopicManager(bootstrap_servers)
    
    topics_to_create = [
        {
            "name": "error_logs",
            "partitions": 1,
            "replication_factor": 1,
            "config": {
                "retention.ms": "604800000",  # 7 days
                "cleanup.policy": "delete"
            }
        },
        {
            "name": "error_logs_dlq",
            "partitions": 1,
            "replication_factor": 1,
            "config": {
                "retention.ms": "2592000000",  # 30 days for DLQ
                "cleanup.policy": "delete"
            }
        }
    ]
    
    logger.info("Starting Kafka topic initialization...")
    success = manager.create_topics(topics_to_create)
    
    if success:
        logger.info("All topics initialized successfully")
        topics = manager.list_topics()
        logger.info(f"Available topics: {topics}")
    else:
        logger.error("Failed to initialize all topics")
    
    return success


if __name__ == "__main__":
    # Allow bootstrap servers to be passed as command-line argument
    bootstrap_servers = sys.argv[1] if len(sys.argv) > 1 else "localhost:9092"
    
    logger.info(f"Using bootstrap servers: {bootstrap_servers}")
    success = initialize_dlq_topics(bootstrap_servers)
    
    sys.exit(0 if success else 1)
