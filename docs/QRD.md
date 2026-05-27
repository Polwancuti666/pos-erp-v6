# ✅ Quality Requirements Document (QRD)
## Beauty & Shine — POS-ERP Integration Engine V6

---

| Field | Value |
|---|---|
| **Project** | Beauty & Shine — Radiance & Refinement |
| **Document** | QRD v1.0 |
| **Author** | System Analyst |
| **Date** | 2026-05-27 |
| **Reference** | BRD v1.0, FRD v1.0, TRD v1.0, SRS v1.0 |
| **ISO Reference** | ISO/IEC 25010:2011 (System and Software Quality Models) |
| **Status** | DRAFT — Pending Stakeholder Approval |

---

## 1. Document Purpose

QRD mendefinisikan standar kualitas yang harus dipenuhi oleh sistem Beauty & Shine. Setiap quality requirement terukur dan dapat diverifikasi.

---

## 2. Quality Model (ISO/IEC 25010)

```
┌─────────────────────────────────────────────────────────────────┐
│                    QUALITY MODEL                                │
│                  ISO/IEC 25010:2011                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐  │
│  │FUNCTIONAL │  │PERFORMANCE│  │COMPATIBLE │  │USABILITY  │  │
│  │SUITABILITY│  │EFFICIENCY │  │           │  │           │  │
│  └───────────┘  └───────────┘  └───────────┘  └───────────┘  │
│                                                                 │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐  │
│  │RELIABILITY│  │SECURITY   │  │MAINTAIN-  │  │PORTABILITY│  │
│  │           │  │           │  │ABILITY    │  │           │  │
│  └───────────┘  └───────────┘  └───────────┘  └───────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Quality Characteristics

### 3.1 Functional Suitability

> Sistem memenuhi kebutuhan fungsional yang didefinisikan.

| # | Requirement | Metric | Target | Verification |
|---|---|---|---|---|
| QF-01 | Functional completeness | % FRD requirements implemented | 100% (P0), 80% (P1) | FRD traceability matrix |
| QF-02 | Functional correctness | Transaction accuracy | 99.99% | Automated tests |
| QF-03 | Functional appropriateness | Task completion rate | 95%+ | User acceptance test |
| QF-04 | Tax calculation accuracy | PPN 11% correct | 100% | Unit test + manual verify |
| QF-05 | Payment amount accuracy | Total = subtotal + tax - discount | 100% | Unit test |
| QF-06 | Receipt content accuracy | All fields match transaction data | 100% | Unit test + visual |
| QF-07 | Receipt print success | Thermal printer output readable | 99% | Manual test |
| QF-08 | WhatsApp delivery success | Message delivered to customer | 95% | Notification log |

**Test Cases:**
```python
# QS-04: Tax calculation
def test_ppn_11_percent():
    subtotal = Decimal("100000")
    tax = subtotal * Decimal("0.11")
    assert tax == Decimal("11000")

# QS-05: Total calculation
def test_total_with_discount():
    subtotal = Decimal("350000")
    discount = Decimal("50000")
    tax = (subtotal - discount) * Decimal("0.11")
    total = subtotal - discount + tax
    assert total == Decimal("333000")

# QF-06: Receipt content accuracy
def test_receipt_content_matches_transaction():
    txn = create_test_transaction(
        items=[("Facial Treatment", 1, 150000), ("Body Massage", 1, 200000)],
        payment_method="cash",
        amount_paid=400000,
    )
    receipt = generate_receipt(txn.id)
    assert "INV-" in receipt.invoice_number
    assert "Facial Treatment" in receipt.items_text
    assert "Body Massage" in receipt.items_text
    assert receipt.subtotal == Decimal("350000")
    assert receipt.tax == Decimal("38500")
    assert receipt.total == Decimal("388500")
    assert receipt.change == Decimal("11500")
    assert "Terima kasih" in receipt.footer

# QF-08: WhatsApp delivery
def test_whatsapp_receipt_delivery():
    result = send_receipt_whatsapp(
        phone="08123456789",
        invoice_number="INV-20260527-0001",
        receipt_text="Test receipt",
    )
    assert result["status"] is True
    # Check NOTIFICATION table
    notification = get_latest_notification(recipient_phone="628123456789")
    assert notification.channel == "whatsapp"
    assert notification.type == "payment_receipt"
    assert notification.status == "sent"
```

---

### 3.2 Performance Efficiency

> Sistem berkinerja sesuai target di bawah beban yang didefinisikan.

| # | Requirement | Metric | Target | Measurement |
|---|---|---|---|---|
| QE-01 | API response time | p50 latency | < 100ms | Application logs |
| QE-02 | API response time | p95 latency | < 200ms | Application logs |
| QE-03 | API response time | p99 latency | < 500ms | Application logs |
| QE-04 | Database query time | p95 latency | < 50ms | Slow query log |
| QE-05 | Page load time | First Contentful Paint | < 1.5s | Lighthouse |
| QE-06 | Page load time | Largest Contentful Paint | < 2.5s | Lighthouse |
| QE-07 | Time to Interactive | TTI | < 3.0s | Lighthouse |
| QE-08 | Transaction throughput | tx per minute | 100+ | Load test |
| QE-09 | Concurrent connections | simultaneous users | 50+ | Load test |
| QE-10 | Memory usage | steady state | < 512MB | System monitoring |
| QE-11 | CPU usage | steady state | < 30% | System monitoring |

**Load Test Scenarios:**
```
Scenario 1: Normal Load
- 10 concurrent users
- 5 transactions per user per minute
- Duration: 10 minutes
- Expected: All < 200ms response time

Scenario 2: Peak Load
- 50 concurrent users
- 3 transactions per user per minute
- Duration: 5 minutes
- Expected: p95 < 500ms, no errors

Scenario 3: Stress Test
- 100 concurrent users
- Duration: 5 minutes
- Expected: Graceful degradation, no crash
```

---

### 3.3 Compatibility

> Sistem kompatibel dengan environment dan sistem lain.

| # | Requirement | Target | Verification |
|---|---|---|---|
| QC-01 | Browser: Chrome (latest 2) | Full functionality | Manual test |
| QC-02 | Browser: Safari (latest 2) | Full functionality | Manual test |
| QC-03 | Browser: Firefox (latest 2) | Full functionality | Manual test |
| QC-04 | Browser: Edge (latest 2) | Full functionality | Manual test |
| QC-05 | Screen: Desktop (1920x1080) | Optimal layout | Visual test |
| QC-06 | Screen: Tablet (768px) | Responsive layout | Visual test |
| QC-07 | Screen: Mobile (320px) | Functional layout | Visual test |
| QC-08 | OS: Windows, macOS, Linux | All browsers work | Cross-platform test |
| QC-09 | PostgreSQL 16 compatibility | Full ORM support | Integration test |
| QC-10 | Docker deployment | Container runs clean | Docker test |
| QC-11 | Android: Chrome Mobile | POS fully functional | Manual test on device |
| QC-12 | Android: PWA install | Install + launch from home screen | Manual test |
| QC-13 | Android: Tablet layout | 2-column split view (768px+) | Visual test |
| QC-14 | iPhone: Safari Mobile | POS fully functional | Manual test on device |
| QC-15 | iPhone: PWA install | Add to Home Screen works | Manual test |
| QC-16 | iPad: Safari | POS fully functional, landscape | Manual test |
| QC-17 | iPad: PWA install | Install + standalone mode | Manual test |
| QC-18 | Touch: Tap targets | Min 44x44px all interactive elements | Accessibility audit |
| QC-19 | Touch: Gesture support | Swipe to delete, pull to refresh | Manual test |
| QC-20 | Orientation: Portrait | Layout correct, no overflow | Visual test |
| QC-21 | Orientation: Landscape | Layout adapts correctly | Visual test |
| QC-22 | Network: Offline | Static assets cached (PWA) | Airplane mode test |
| QC-23 | Network: Slow 3G | Usable with loading indicators | Throttled test |

### Device Testing Matrix

| Device | Browser | Resolution | PWA | Orientation | Status |
|---|---|---|---|---|---|
| **Samsung Galaxy S24** | Chrome | 1080x2340 | ✅ Install | Portrait | P0 |
| **Samsung Galaxy Tab S9** | Chrome | 1600x2560 | ✅ Install | Both | P0 |
| **Pixel 8** | Chrome | 1080x2400 | ✅ Install | Portrait | P0 |
| **Xiaomi Redmi Note 12** | Chrome | 1080x2400 | ✅ Install | Portrait | P0 |
| **iPhone 15** | Safari | 1179x2556 | ✅ Add to HS | Portrait | P0 |
| **iPhone 15 Pro Max** | Safari | 1290x2796 | ✅ Add to HS | Both | P0 |
| **iPad Air M2** | Safari | 2048x2732 | ✅ Add to HS | Both | P1 |
| **iPad Pro 12.9"** | Safari | 2048x2732 | ✅ Add to HS | Both | P1 |
| **Desktop (Windows)** | Chrome/Edge | 1920x1080 | N/A | Landscape | P0 |
| **Desktop (macOS)** | Safari/Chrome | 2560x1600 | N/A | Landscape | P0 |

---

### 3.4 Usability

> Sistem mudah dipahami dan digunakan oleh user.

| # | Requirement | Metric | Target | Verification |
|---|---|---|---|---|
| QU-01 | Learnability: POS | Time to first transaction | < 5 minutes | User test |
| QU-02 | Learnability: Dashboard | Time to find key metric | < 10 seconds | User test |
| QU-03 | Efficiency: POS checkout | Clicks to complete sale | ≤ 5 clicks | Task analysis |
| QU-04 | Efficiency: Search customer | Search results appear | < 1 second | UI test |
| QU-05 | Error prevention: Input validation | Client-side validation | 100% of forms | Manual test |
| QU-06 | Error recovery: Clear messages | Error message understood | 90% of users | User test |
| QU-07 | Consistency: Brand identity | Design system followed | 100% of pages | Visual audit |
| QU-08 | Accessibility: Color contrast | WCAG AA ratio | ≥ 4.5:1 | Lighthouse |
| QU-09 | Accessibility: Keyboard nav | All actions accessible | 100% | Manual test |
| QU-10 | Language: Bahasa Indonesia | All UI text | 100% | Manual review |

**Usability Heuristics (Nielsen):**

| # | Heuristic | Implementation |
|---|---|---|
| 1 | Visibility of system status | Loading spinners, status badges |
| 2 | Match between system and real world | Beauty terminology, Rupiah format |
| 3 | User control and freedom | Undo cart changes, cancel booking |
| 4 | Consistency and standards | Consistent button styles, layouts |
| 5 | Error prevention | Input validation, confirmation dialogs |
| 6 | Recognition rather than recall | Cart shows item names, recent customers |
| 7 | Flexibility and efficiency | Quick-add products, keyboard shortcuts |
| 8 | Aesthetic and minimalist design | Clean UI, ivory/gold/charcoal palette |
| 9 | Help users recognize errors | Red error messages, inline validation |
| 10 | Help and documentation | API docs, tooltip hints |

---

### 3.5 Reliability

> Sistem beroperasi secara konsisten dan dapat dipulihkan.

| # | Requirement | Metric | Target | Verification |
|---|---|---|---|---|
| QR-01 | Availability | Uptime percentage | 99.5% | Monitoring |
| QR-02 | Mean Time Between Failures | MTBF | > 720 hours | Incident log |
| QR-03 | Mean Time To Recover | MTTR | < 4 hours | Incident log |
| QR-04 | Data durability | Data loss | Zero tolerance | Backup verification |
| QR-05 | Graceful degradation | Partial failure handling | Non-critical features fail gracefully | Chaos test |
| QR-06 | Error handling | Unhandled exceptions | 0 in production | Error log monitoring |
| QR-07 | Database integrity | Constraint violations | 0 orphan records | Integrity check script |
| QR-08 | Transaction atomicity | All-or-nothing | 100% of transactions | Integration test |
| QR-09 | Backup success rate | Successful backups | 100% | Backup verification |
| QR-10 | Recovery testing | Restore from backup | < 1 hour | Quarterly drill |

**Reliability Scenarios:**

| Scenario | Expected Behavior |
|---|---|
| Database connection lost | Return 503, retry with backoff, alert admin |
| Payment gateway timeout | Mark pending, retry in 5 min, notify kasir |
| Disk space < 10% | Alert admin, stop non-essential logging |
| Invalid API request | Return 400 with clear error message |
| Concurrent booking conflict | Return 409, suggest alternative slots |

---

### 3.6 Security

> Sistem melindungi data dan operasi dari akses tidak sah.

| # | Requirement | Metric | Target | Verification |
|---|---|---|---|---|
| QS-01 | Authentication | Brute force protection | Lock after 3 failed attempts | Security test |
| QS-02 | Authorization | RBAC enforcement | 100% of endpoints | Security test |
| QS-03 | Data encryption in transit | TLS version | TLS 1.3 | SSL test |
| QS-04 | Password security | Hash algorithm | bcrypt, 12 rounds | Code review |
| QS-05 | SQL injection | Vulnerability scan | 0 findings | bandit, manual test |
| QS-06 | XSS prevention | Input sanitization | 100% of inputs | Security scan |
| QS-07 | CSRF protection | Token validation | All state-changing requests | Security test |
| QS-08 | Rate limiting | Requests per IP | 100 req/min | Load test |
| QS-09 | Secret management | Hardcoded secrets | 0 findings | Code scan |
| QS-10 | Audit trail | Mutation logging | 100% of data changes | Audit log review |
| QS-11 | Session management | Token expiry | 30 min access, 7 day refresh | Code review |
| QS-12 | CORS | Allowed origins | Whitelist only | Config review |

**Security Test Cases:**
```
Test: SQL Injection
  Input: ' OR 1=1 --
  Expected: Input rejected, no data leak

Test: XSS Attack
  Input: <script>alert('xss')</script>
  Expected: Input sanitized, not rendered

Test: Unauthorized Access
  Request: GET /dashboard without token
  Expected: 401 Unauthorized

Test: Role Escalation
  Request: Kasir tries to access /staff (manager only)
  Expected: 403 Forbidden

Test: Brute Force
  Action: 4 failed login attempts
  Expected: Account locked for 15 minutes
```

---

### 3.7 Maintainability

> Sistem mudah dimodifikasi dan dipelihara.

| # | Requirement | Metric | Target | Verification |
|---|---|---|---|---|
| QM-01 | Code modularity | Module separation | Clean architecture | Code review |
| QM-02 | Code readability | Consistent style | PEP 8 compliant | Ruff/flake8 |
| QM-03 | Test coverage | Line coverage | ≥ 80% | pytest-cov |
| QM-04 | Documentation | API docs | 100% of endpoints | OpenAPI auto-gen |
| QM-05 | Database migrations | Version controlled | All schema changes | Alembic |
| QM-06 | Configuration management | Environment-based | All config via env vars | Config review |
| QM-07 | Logging | Structured logging | All critical operations | Log review |
| QM-08 | Error tracking | Error categorization | All errors logged with context | Error log |
| QM-09 | Dependency management | Pinned versions | All deps in requirements.txt | Dependency scan |
| QM-10 | Code duplication | DRY principle | < 5% duplication | Code analysis |

**Code Quality Standards:**

```python
# Naming Convention
# - Variables: snake_case
# - Classes: PascalCase
# - Constants: UPPER_SNAKE_CASE
# - Functions: snake_case
# - Private: _prefix

# Example:
class TransactionService:
    """Service for processing POS transactions."""
    
    TAX_RATE = Decimal("0.11")
    MAX_RETRY_COUNT = 3
    
    def __init__(self, db: AsyncSession):
        self._db = db
    
    async def create_transaction(
        self,
        shift_id: UUID,
        items: list[TransactionItem],
        payment_method: PaymentMethod,
    ) -> Transaction:
        """Create a new POS transaction.
        
        Args:
            shift_id: Active shift UUID
            items: List of items to transact
            payment_method: Payment method to use
            
        Returns:
            Created transaction
            
        Raises:
            ShiftNotFoundError: If shift not found or inactive
            InsufficientStockError: If product out of stock
        """
        ...
```

---

### 3.8 Portability

> Sistem dapat dipindahkan antar environment.

| # | Requirement | Metric | Target | Verification |
|---|---|---|---|---|
| QP-01 | Containerization | Docker image | Single image, all services | Docker build test |
| QP-02 | Environment independence | Config via env vars | Zero hardcoded config | Config audit |
| QP-03 | Database portability | ORM abstraction | No raw SQL (except optimization) | Code review |
| QP-04 | Platform independence | Linux/macOS/Windows | Docker runs on all | Cross-platform test |
| QP-05 | Cloud portability | No vendor lock-in | Replaceable components | Architecture review |

---

## 4. Quality Assurance Process

### 4.1 QA Workflow

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  PLAN    │────→│IMPLEMENT │────→│  VERIFY  │────→│  RELEASE │
│          │     │          │     │          │     │          │
│ - Define │     │ - Write  │     │ - Run    │     │ - Deploy │
│   tests  │     │   code   │     │   tests  │     │   to prod│
│ - Set    │     │ - Write  │     │ - Manual │     │ - Monitor│
│   criteria│    │   tests  │     │   verify │     │          │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
      ▲                                              │
      └──────────────────────────────────────────────┘
                      (Feedback Loop)
```

### 4.2 Testing Levels

| Level | When | Who | Tool | Coverage |
|---|---|---|---|---|
| Unit | During development | Developer | pytest | Every function |
| Integration | After module complete | Developer | pytest + httpx | Module interactions |
| System | After all modules | Developer | pytest + TestClient | End-to-end flows |
| Regression | After every change | Developer | pytest (full suite) | All existing tests |
| Performance | Before production | Developer | locust | Critical paths |
| Security | Before production | Developer | bandit, safety | All dependencies |
| Acceptance | Before go-live | Stakeholder | Manual scenarios | Business requirements |

### 4.3 Test Environment

| Environment | Purpose | Data | URL |
|---|---|---|---|
| Development | Local testing | Mock data | localhost:8000 |
| Staging | Pre-production test | Production-like | staging.beautynshine.web.id |
| Production | Live system | Real data | erp.beautynshine.web.id |

---

## 5. Quality Metrics & KPIs

### 5.1 Code Quality Metrics

| Metric | Tool | Target | Alert |
|---|---|---|---|
| Test coverage | pytest-cov | ≥ 80% | < 70% |
| Code style | ruff | 0 violations | Any violation |
| Type hints | mypy | 100% of public APIs | Missing hints |
| Security issues | bandit | 0 high/critical | Any high |
| Dependencies | safety | 0 known vulnerabilities | Any CVE |
| Duplication | pylint | < 5% | > 10% |

### 5.2 Runtime Quality Metrics

| Metric | Monitoring | Target | Alert |
|---|---|---|---|
| Error rate | Application logs | < 0.1% | > 0.5% |
| Response time p95 | Application logs | < 200ms | > 500ms |
| Uptime | Health check | 99.5% | < 99% |
| Database connections | PostgreSQL | < 80 active | > 90 |
| Disk usage | System | < 80% | > 90% |
| Memory usage | System | < 80% | > 90% |

### 5.3 Business Quality Metrics

| Metric | Source | Target | Review |
|---|---|---|---|
| Transaction success rate | POS logs | > 99% | Weekly |
| Payment success rate | Payment logs | > 98% | Weekly |
| Booking completion rate | Booking logs | > 90% | Weekly |
| Customer satisfaction | Feedback | > 4.5/5 | Monthly |
| System adoption rate | Usage logs | 100% staff | Monthly |

---

## 6. Defect Management

### 6.1 Defect Severity

| Severity | Definition | Response Time | Resolution Time |
|---|---|---|---|
| **Critical** | System down, data loss, payment failure | 15 minutes | 2 hours |
| **High** | Major feature broken, workaround exists | 1 hour | 24 hours |
| **Medium** | Minor feature issue, cosmetic impact | 4 hours | 1 week |
| **Low** | Enhancement, nice-to-have | Next sprint | Next release |

### 6.2 Defect Lifecycle

```
NEW → TRIAGED → IN PROGRESS → FIXED → VERIFIED → CLOSED
                        │
                        └→ WONTFIX / DUPLICATE / BY DESIGN
```

### 6.3 Defect Tracking Template

```markdown
## Bug Report

**ID:** BUG-XXX
**Title:** [Brief description]
**Severity:** Critical / High / Medium / Low
**Module:** [Module name]
**Steps to Reproduce:**
1. ...
2. ...
3. ...
**Expected Result:** ...
**Actual Result:** ...
**Environment:** [Browser, OS, URL]
**Screenshot:** [If applicable]
**Assigned To:** [Developer]
**Status:** NEW
```

---

## 7. Release Quality Criteria

### 7.1 Release Gate (MVP)

| Gate | Criteria | Status |
|---|---|---|
| Gate 1 | All P0 functional requirements implemented | ⬜ |
| Gate 2 | Test coverage ≥ 80% | ⬜ |
| Gate 3 | 0 critical/high bugs open | ⬜ |
| Gate 4 | Security scan clean | ⬜ |
| Gate 5 | Performance targets met | ⬜ |
| Gate 6 | UAT sign-off from stakeholder | ⬜ |
| Gate 7 | Backup/restore verified | ⬜ |
| Gate 8 | Documentation complete | ⬜ |

### 7.2 Definition of Done (DoD)

A feature dianggap "done" ketika:
- [ ] Code ditulis dan di-review
- [ ] Unit tests passing (coverage ≥ 80%)
- [ ] Integration tests passing
- [ ] API documentation updated
- [ ] No critical/high bugs
- [ ] Deployed ke staging
- [ ] Stakeholder reviewed

---

## 8. Continuous Improvement

### 8.1 Quality Review Cadence

| Review | Frequency | Participants | Focus |
|---|---|---|---|
| Code review | Every PR | Developer | Code quality |
| Sprint review | Bi-weekly | All | Feature demo |
| Quality audit | Monthly | System Analyst | Metrics review |
| Security scan | Monthly | Developer | Vulnerability check |
| Performance review | Monthly | Developer | Response time, resources |
| Retrospective | Bi-weekly | All | Process improvement |

---

## 9. Appendices

### 9.1 Testing Checklist

```
□ Unit tests for all services
□ Integration tests for all API endpoints
□ POS transaction end-to-end test
□ Payment flow test (mock gateway)
□ Booking flow test
□ Authentication/authorization test
□ Input validation test
□ Error handling test
□ Database migration test
□ Backup/restore test
□ Browser compatibility test
□ Mobile responsive test
□ Performance load test
□ Security vulnerability scan
```

### 9.2 Quality Tools

| Tool | Purpose | Integration |
|---|---|---|
| pytest | Unit + integration testing | CI/CD |
| pytest-cov | Coverage reporting | CI/CD |
| ruff | Code linting | Pre-commit |
| mypy | Type checking | CI/CD |
| bandit | Security linting | CI/CD |
| safety | Dependency vulnerability | CI/CD |
| locust | Load testing | Manual |
| Lighthouse | Web performance | Manual |

---

*Document ini harus di-review dan di-approve oleh stakeholder sebelum development phase dimulai.*
