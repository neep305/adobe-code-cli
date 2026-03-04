# Backend Tests

## Setup

1. Install test dependencies:
```bash
pip install -r requirements.txt
```

2. Make sure PostgreSQL test database exists:
```bash
# Connect to PostgreSQL
psql -U aep_user -h localhost

# Create test database
CREATE DATABASE aep_web_test;
```

3. Set environment variables in `.env` file (see `.env.example`)

## Running Tests

### Run all tests
```bash
cd web/backend
pytest tests/ -v
```

### Run auth tests only
```bash
pytest tests/test_auth_api.py -v
```

### Run with coverage
```bash
pytest tests/ --cov=app --cov-report=html
```

### Run specific test
```bash
pytest tests/test_auth_api.py::test_register_success -v
```

## Test Structure

```
tests/
├── __init__.py
├── conftest.py           # Pytest fixtures and configuration
└── test_auth_api.py      # Authentication API tests
```

## Key Test Cases

### Authentication Tests (`test_auth_api.py`)
- ✅ Register new user successfully
- ✅ Handle duplicate email registration
- ✅ Validate email format
- ✅ Enforce password length (min 8 chars)
- ✅ Login after registration
- ✅ Login with wrong password fails
- ✅ Access protected endpoints with token
- ✅ Reject invalid tokens
- ✅ Check authentication status

## CI/CD Integration

Tests run automatically on:
- Every pull request
- Pushes to main branch

See `.github/workflows/test-auth.yml` for CI configuration.

## Troubleshooting

### Database connection error
Make sure PostgreSQL is running and test database exists:
```bash
docker ps | grep postgres
```

### Import errors
Make sure you're in the correct directory:
```bash
cd web/backend
```

### Async test warnings
Make sure pytest-asyncio is installed:
```bash
pip install pytest-asyncio
```
