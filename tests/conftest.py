"""Test fixtures and configuration."""

import pytest


@pytest.fixture
def sample_customer_data():
    """Sample customer data for testing."""
    return [
        {
            "customer_id": "CUST001",
            "email": "john.doe@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "age": 35,
            "status": "active",
            "registration_date": "2024-01-15T10:30:00Z",
            "preferences": {
                "newsletter": True,
                "notifications": False,
            },
            "tags": ["premium", "loyal"],
        },
        {
            "customer_id": "CUST002",
            "email": "jane.smith@example.com",
            "first_name": "Jane",
            "last_name": "Smith",
            "age": 28,
            "status": "active",
            "registration_date": "2024-02-20T14:45:00Z",
            "preferences": {
                "newsletter": False,
                "notifications": True,
            },
            "tags": ["new"],
        },
    ]


@pytest.fixture
def sample_event_data():
    """Sample event data for testing."""
    return [
        {
            "event_id": "EVT001",
            "event_type": "page_view",
            "timestamp": "2024-03-01T12:00:00Z",
            "user_id": "USER123",
            "properties": {
                "page_url": "https://example.com/products",
                "referrer": "https://google.com",
            },
        },
        {
            "event_id": "EVT002",
            "event_type": "purchase",
            "timestamp": "2024-03-01T12:15:00Z",
            "user_id": "USER123",
            "properties": {
                "product_id": "PROD456",
                "amount": 99.99,
                "currency": "USD",
            },
        },
    ]
