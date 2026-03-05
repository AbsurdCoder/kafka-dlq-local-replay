"""
Error Message Schema Definition
Defines the structure and validation for error messages in the DLQ system.
"""

import json
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class ErrorMessage(BaseModel):
    """
    Pydantic model for error messages.
    
    Attributes:
        error_id: Unique identifier for the error (UUID)
        source_service: Name of the service that generated the error
        error_message: Human-readable error description
        payload: Additional context data as JSON string
        timestamp: ISO 8601 formatted timestamp
        retry_count: Number of times this error has been retried (default: 0)
        severity: Error severity level (INFO, WARNING, ERROR, CRITICAL)
    """
    
    error_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique error identifier")
    source_service: str = Field(..., min_length=1, max_length=255, description="Service name that generated the error")
    error_message: str = Field(..., min_length=1, max_length=2048, description="Error description")
    payload: str = Field(default="{}", description="Additional context as JSON string")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z", description="ISO 8601 timestamp")
    retry_count: int = Field(default=0, ge=0, description="Number of retry attempts")
    severity: str = Field(default="ERROR", description="Error severity level")
    
    @field_validator("payload")
    @classmethod
    def validate_payload_json(cls, v: str) -> str:
        """Validate that payload is valid JSON string."""
        try:
            json.loads(v)
            return v
        except json.JSONDecodeError:
            raise ValueError("payload must be a valid JSON string")
    
    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        """Validate severity level."""
        valid_levels = {"INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f"severity must be one of {valid_levels}")
        return v.upper()
    
    @field_validator("error_id")
    @classmethod
    def validate_error_id(cls, v: str) -> str:
        """Validate error_id is a valid UUID."""
        try:
            UUID(v)
            return v
        except ValueError:
            raise ValueError("error_id must be a valid UUID")
    
    def to_json(self) -> str:
        """Convert model to JSON string."""
        return self.model_dump_json()
    
    @classmethod
    def from_json(cls, json_str: str) -> "ErrorMessage":
        """Create model from JSON string."""
        return cls.model_validate_json(json_str)


class ErrorResponse(BaseModel):
    """Response model for error details endpoint."""
    
    error_id: str
    source_service: str
    error_message: str
    payload: Dict[str, Any]
    timestamp: str
    retry_count: int
    severity: str


class ErrorCountResponse(BaseModel):
    """Response model for error count endpoint."""
    
    total_count: int
    by_severity: Dict[str, int]
    by_service: Dict[str, int]


# JSON Schema for error messages (for documentation)
ERROR_MESSAGE_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "error_id": {
            "type": "string",
            "description": "UUID format unique identifier",
            "example": "550e8400-e29b-41d4-a716-446655440000"
        },
        "source_service": {
            "type": "string",
            "description": "Service that generated the error",
            "example": "payment-service"
        },
        "error_message": {
            "type": "string",
            "description": "Human-readable error description",
            "example": "Failed to process payment: insufficient funds"
        },
        "payload": {
            "type": "string",
            "description": "Additional context as JSON string",
            "example": '{"transaction_id": "txn_123", "amount": 99.99}'
        },
        "timestamp": {
            "type": "string",
            "description": "ISO 8601 formatted timestamp",
            "example": "2024-01-15T10:30:45.123456Z"
        },
        "retry_count": {
            "type": "integer",
            "description": "Number of retry attempts",
            "example": 0
        },
        "severity": {
            "type": "string",
            "enum": ["INFO", "WARNING", "ERROR", "CRITICAL"],
            "description": "Error severity level",
            "example": "ERROR"
        }
    },
    "required": ["error_id", "source_service", "error_message", "timestamp"]
}
