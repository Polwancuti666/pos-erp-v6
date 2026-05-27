# Developer Guide

## POS-ERP Integration Engine V6

---

## 1. Getting Started

### Prerequisites

- Python 3.11+
- pip or poetry
- Docker & Docker Compose (for PostgreSQL)
- Git

### Setup

```bash
# Clone repository
git clone <repository-url>
cd pos-erp-v6

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -e ".[dev]"

# Install pre-commit hooks (if configured)
pre-commit install

# Run tests
pytest

# Start development server
uvicorn pos_erp.fastapi_app:app --reload --port 8000
```

### Development with Docker

```bash
# Start PostgreSQL
docker compose up -d postgres

# Set environment variables
export PG_HOST=localhost
export PG_PORT=5432
export PG_DATABASE=pos_erp
export PG_USER=pos_erp
export PG_PASSWORD=dev_password

# Run application
uvicorn pos_erp.fastapi_app:app --reload
```

---

## 2. Project Structure

```
pos-erp-v6/
├── src/
│   └── pos_erp/
│       ├── __init__.py
│       ├── fastapi_app.py      # FastAPI application and routes
│       ├── api.py              # AppService (application layer)
│       ├── config.py           # AppConfig.from_env()
│       │
│       ├── # Core Domain Modules
│       ├── checkout.py         # Transaction processing
│       ├── payment.py          # Payment intent lifecycle
│       ├── payment_providers.py # BCA VA, Midtrans adapters
│       ├── inventory.py        # Stock movement tracking
│       ├── treatment.py        # Service management
│       │
│       ├── # ERP Modules
│       ├── accounting.py       # Journal posting, COA mapping
│       ├── reconciliation.py   # Shift closing, variance
│       ├── document_finalization.py
│       ├── document_numbering.py
│       ├── period_lock.py      # Accounting period protection
│       ├── correction.py       # Correction action decisions
│       │
│       ├── # Auth & Security
│       ├── auth.py             # ERP authentication
│       ├── pos_auth.py         # POS staff PIN auth
│       ├── permissions.py      # RBAC (5 roles, 11 actions)
│       ├── security.py         # Encryption, HMAC
│       ├── staff_lock.py       # Resource locking
│       │
│       ├── # Sync & Integration
│       ├── sync.py             # Outbox queue, retry
│       ├── sync_control.py     # Connectivity, approval
│       ├── adapters.py         # External service adapters
│       │
│       ├── # Infrastructure
│       ├── persistence.py      # InMemoryRepository
│       ├── postgresql.py       # PostgreSQL config
│       ├── migrations.py       # Schema migrations
│       ├── deployment.py       # Deployment manifest
│       │
│       ├── # Observability & UI
│       ├── dashboard.py        # Owner dashboard
│       ├── observability.py    # Health checks, metrics
│       ├── exception_queue.py  # Error handling with SLA
│       └── beauty_ui.py        # HTML dashboard renderer
│
├── tests/
│   ├── __init__.py
│   ├── test_checkout.py
│   ├── test_payment.py
│   ├── test_inventory.py
│   ├── test_accounting.py
│   ├── test_reconciliation.py
│   ├── test_sync.py
│   └── ...
│
├── docs/
│   ├── business-process.md
│   ├── system-architecture.md
│   ├── database-design.md
│   ├── api-reference.md
│   ├── module-pos.md
│   ├── module-erp.md
│   ├── module-inventory.md
│   ├── deployment-guide.md
│   └── developer-guide.md
│
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── README.md
└── .env.example
```

---

## 3. Architecture Principles

### Clean Architecture

The project follows clean architecture with clear layer boundaries:

```
FastAPI Gateway (routes)
      │
      ▼
Application Service (api.py - AppService)
      │
      ▼
Domain Logic (checkout, payment, inventory, etc.)
      │
      ▼
Persistence (repository interface → implementation)
```

### Dependency Rule

- Inner layers do NOT depend on outer layers
- Domain logic has no knowledge of FastAPI or database
- Adapters implement interfaces defined by domain

### Module Responsibilities

Each module has a single responsibility and exposes a clean public API:

```python
# Example: inventory.py
class InventoryService:
    def record_movement(self, product_id, movement_type, reason, 
                       quantity, reference_id, staff_id) -> StockMovement:
        """Single entry point for stock movements."""
        ...
```

---

## 4. Adding New Modules

### Step-by-Step Guide

1. **Create module file** in `src/pos_erp/`:
```python
# src/pos_erp/new_module.py
from dataclasses import dataclass
from enum import Enum
from uuid import UUID, uuid4
from datetime import datetime

class NewStatus(Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

@dataclass
class NewEntity:
    id: UUID
    name: str
    status: NewStatus
    created_at: datetime

class NewService:
    def create(self, name: str) -> NewEntity:
        """Create a new entity."""
        ...
    
    def get(self, id: UUID) -> NewEntity:
        """Retrieve entity by ID."""
        ...
```

2. **Add to Application Service** (`api.py`):
```python
from pos_erp.new_module import NewService

class AppService:
    def __init__(self):
        self.new_service = NewService()
    
    async def handle_new_action(self, name: str):
        return self.new_service.create(name)
```

3. **Add API route** (`fastapi_app.py`):
```python
@app.post("/new-endpoint")
async def new_endpoint(data: NewRequest):
    return app_service.handle_new_action(data.name)
```

4. **Write tests** (`tests/test_new_module.py`):
```python
import pytest
from pos_erp.new_module import NewService, NewStatus

class TestNewService:
    def test_create(self):
        service = NewService()
        entity = service.create("test")
        assert entity.name == "test"
        assert entity.status == NewStatus.ACTIVE
    
    def test_get(self):
        service = NewService()
        entity = service.create("test")
        retrieved = service.get(entity.id)
        assert retrieved.id == entity.id
```

5. **Update documentation**:
- Add to relevant module doc
- Update architecture diagram if needed
- Document API endpoints in api-reference.md

---

## 5. Testing Conventions

### Test Structure

```
tests/
├── test_checkout.py      # Unit tests for checkout module
├── test_payment.py       # Unit tests for payment module
├── test_integration.py   # Integration tests
└── conftest.py           # Shared fixtures
```

### Writing Tests

```python
import pytest
from uuid import uuid4
from decimal import Decimal
from pos_erp.checkout import OfflineTransaction, PaymentType

class TestOfflineTransaction:
    """Unit tests for OfflineTransaction."""
    
    def test_create_cash_transaction(self):
        """Test creating a cash transaction."""
        txn = OfflineTransaction(
            id=uuid4(),
            staff_id="KSR001",
            payment_type=PaymentType.CASH,
            items=[{"product_id": "P001", "quantity": 1, "price": Decimal("100000")}],
            total_amount=Decimal("100000")
        )
        assert txn.payment_type == PaymentType.CASH
        assert txn.total_amount == Decimal("100000")
    
    def test_cash_transaction_immediate_confirm(self):
        """Test that cash transactions are immediately confirmed."""
        # Test implementation
        ...

class TestCheckoutIntegration:
    """Integration tests for checkout flow."""
    
    @pytest.fixture
    def checkout_service(self):
        """Create checkout service with in-memory repository."""
        from pos_erp.api import AppService
        return AppService()
    
    async def test_complete_cash_checkout(self, checkout_service):
        """Test complete cash checkout flow."""
        result = await checkout_service.complete_offline_checkout(
            staff_id="KSR001",
            payment_type=PaymentType.CASH,
            items=[...],
            total=Decimal("250000")
        )
        assert result.status == TransactionStatus.CONFIRMED
```

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_checkout.py

# Run specific test class
pytest tests/test_checkout.py::TestOfflineTransaction

# Run with coverage
pytest --cov=pos_erp

# Run only unit tests (exclude integration)
pytest -m "not integration"
```

### Test Markers

```python
import pytest

@pytest.mark.integration
def test_database_integration():
    """Integration test requiring database."""
    ...

@pytest.mark.slow
def test_large_dataset():
    """Test that takes a long time."""
    ...
```

### Fixtures

Common fixtures in `conftest.py`:

```python
import pytest
from pos_erp.persistence import InMemoryRepository
from pos_erp.api import AppService

@pytest.fixture
def repository():
    """Fresh in-memory repository for each test."""
    return InMemoryRepository()

@pytest.fixture
def app_service(repository):
    """AppService with test repository."""
    return AppService(repository=repository)

@pytest.fixture
def sample_transaction():
    """Sample transaction data."""
    return {
        "staff_id": "KSR001",
        "payment_type": "CASH",
        "items": [...],
        "total_amount": Decimal("250000")
    }
```

---

## 6. Code Style

### Python Style Guide

- Follow PEP 8
- Use type hints for all function signatures
- Use dataclasses for data models
- Use Enums for fixed sets of values

### Naming Conventions

| Element | Convention | Example |
|---|---|---|
| Module | snake_case | `checkout.py` |
| Class | PascalCase | `OfflineTransaction` |
| Function | snake_case | `record_movement()` |
| Constant | UPPER_SNAKE | `MAX_RETRIES = 3` |
| Variable | snake_case | `staff_id` |
| Private | _prefix | `_internal_method()` |

### Type Hints

```python
from typing import Optional, List
from decimal import Decimal
from uuid import UUID

def get_transaction(id: UUID) -> Optional[dict]:
    """Retrieve transaction by ID."""
    ...

def list_transactions(staff_id: str, limit: int = 100) -> List[dict]:
    """List transactions for a staff member."""
    ...
```

### Docstrings

Use Google-style docstrings:

```python
def record_movement(
    product_id: str,
    movement_type: MovementType,
    reason: MovementReason,
    quantity: Decimal,
    reference_id: str,
    staff_id: str
) -> StockMovement:
    """Record a stock movement.
    
    Args:
        product_id: Product being moved.
        movement_type: IN or OUT.
        reason: Reason for the movement.
        quantity: Quantity to move (must be positive).
        reference_id: Related transaction or document ID.
        staff_id: Staff recording the movement.
    
    Returns:
        The created StockMovement record.
    
    Raises:
        ValueError: If quantity is not positive.
        InsufficientStockError: If stock would go negative 
            and policy blocks it.
    """
    ...
```

### Imports

```python
# Standard library
from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4
from dataclasses import dataclass
from typing import Optional, List

# Third-party
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Local
from pos_erp.config import AppConfig
from pos_erp.persistence import InMemoryRepository
```

---

## 7. Common Development Tasks

### Adding a New API Endpoint

1. Define request/response models in `fastapi_app.py`
2. Add handler function in `api.py` (AppService)
3. Implement domain logic in appropriate module
4. Add route decorator in `fastapi_app.py`
5. Write tests
6. Update `api-reference.md`

### Adding a New Database Entity

1. Define dataclass in appropriate module
2. Add repository methods in `persistence.py`
3. Add PostgreSQL queries (when implementing PostgreSQL)
4. Create migration in `migrations.py`
5. Update `database-design.md`

### Adding a New Payment Provider

1. Create adapter class in `payment_providers.py`
2. Implement required methods (create, verify, etc.)
3. Register in provider registry
4. Add configuration variables
5. Write tests with mock responses
6. Update documentation

### Debugging Tips

```bash
# Enable debug logging
export APP_DEBUG=true

# Run with Python debugger
python -m pdb -m pos_erp.fastapi_app

# Interactive debugging with ipdb
pip install ipdb
# Add: import ipdb; ipdb.set_trace() in code

# View application logs
docker compose logs -f api
```

---

## 8. Contributing

### Workflow

1. Create feature branch from `main`
2. Make changes with tests
3. Run test suite: `pytest`
4. Update documentation if needed
5. Submit pull request
6. Code review
7. Merge to `main`

### Commit Messages

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Examples:
```
feat(checkout): add QRIS payment support
fix(sync): handle network timeout gracefully
docs(api-reference): add payment callback documentation
test(inventory): add negative stock escalation tests
```

---

## 9. Resources

- [Business Process Documentation](business-process.md)
- [System Architecture](system-architecture.md)
- [API Reference](api-reference.md)
- [Database Design](database-design.md)
- [Deployment Guide](deployment-guide.md)
