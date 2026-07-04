---
name: clean-code
description: Apply and review code against Clean Code principles (naming, SRP, DRY, type hints, error handling, testing). Use for code review, refactoring, and PR preparation.
license: MIT
metadata:
  author: opencode
  version: "2.0"
---

# Clean Code Skill

Apply the following Clean Code principles when writing, reviewing, or refactoring code in this project. Each section has concrete **rules to follow**, **anti-patterns to avoid**, and **checks** that can be automated with the existing tooling (Ruff, ESLint, pytest).

---

## 1. DRY (Don't Repeat Yourself)

### Rules
- If the same 3+ line pattern appears in ≥3 places, extract a helper function.
- If the same `try/except` pattern appears in ≥3 endpoints, create a wrapper (like `require_role_in_district()` in `permissions.py`).
- If two functions compute the same intermediate values, extract a shared helper (like `_expected_times()` in `matrix_service.py`).

### Project-specific patterns known to repeat
| Pattern | Occurrences | Fix |
|---------|-------------|-----|
| `try: assert_has_role_in_district(...); except PermissionError as e: raise HTTPException(status_code=403, detail=str(e))` | ~55× | Use `require_role_in_district()` from `app.adapters.auth.permissions` |
| `datetime.now(UTC)` being recomputed per field | ~15× | Compute `now = datetime.now(UTC)` once, reuse |
| `if not await SqlDistrictRepository(db).get(...): raise HTTPException(404, "...")` | ~8× | Could extract `_ensure_district_exists(db, district_id)` |
| Long manual field-mapping in `_to_response()` / `_leader_response()` helpers | ~10 files | Consider Pydantic `model_validate` or a shared mixin |

### How to check
```bash
# Count try/except PermissionError occurrences (target: 0 for new endpoints)
grep -rn "except PermissionError" app/adapters/api/routers/ | wc -l

# Count raw assert_has_role_in_district (should now be rare)
grep -rn "assert_has_role_in_district" app/adapters/api/routers/ | wc -l

# Find repeated datetime.now(UTC) within a single function
grep -rn "datetime.now(UTC)" app/
```

---

## 2. Single Responsibility Principle (SRP)

### Rules
- A **function** should do one thing. If you need "and" to describe it, split it.
- A **class** should have one reason to change.
- FastAPI **endpoint handlers** should: (1) parse/validate input, (2) call a service, (3) format response — no business logic.

### Anti-patterns
- `approve_registration()`-style megafunctions that validate, create entities, provision external systems — all in one function.
- Routers that contain SQL queries directly instead of calling repositories.
- Services that mix HTTP concern (status codes) with domain logic.

### How to check
```bash
# Find functions with > 50 lines (likely violating SRP)
grep -rn "^\s*async def\|^\s*def " app/ --include="*.py" | while IFS=: read -r file line func; do
  lines=$(sed -n "$line,\$p" "$file" | awk '/^async def|^def |^class |^$/{if(NR>1)exit} {count++} END{print count}')
  # (manual review — too heuristic to automate fully)
done
```

---

## 3. Naming

### Rules
| Artifact | Style | Example |
|----------|-------|---------|
| Classes/Models | PascalCase | `LeaderRegistration`, `PlanningSeriesGenerator` |
| Functions/Methods | snake_case | `approve_registration()`, `calculate_deviation_minutes()` |
| Private helpers | `_` prefix | `_to_response()`, `_validate_registration_pending()` |
| Constants (module-level) | `_` prefix + UPPER | `_DEFAULT_EVENT_DURATION`, `_SYNTHESIZED_EVENT_DURATION` |
| Type variables | PascalCase | `AuthContext`, `DbSession` |
| Boolean variables | should start with `is_`, `has_`, `can_` | `is_active`, `has_deviation` |

### Anti-patterns
- Single-letter names (except loop vars): `x`, `tmp`, `data`
- Abbreviated names: `reg_repo` → `registration_repo` (unless very common like `repo`, `db`)
- Names that don't convey *why*: avoid `process_data()`, `handle_request()`, `do_work()`
- Boolean methods without `is_`/`has_`/`can_` prefix: `deviation(slot, instance)` → `has_deviation(slot, instance)`

### How to check
```bash
# Find single-letter top-level names (excluding loop vars)
ruff check --select N801,N802,N803,N806,N807 app/

# N801: class names should use PascalCase
# N802: function names should use snake_case
# N803: argument names should use snake_case
# N806: variable in function should be snake_case
```

---

## 4. Type Hints

### Rules
- Every function **must** have type hints for all parameters and the return value.
- Use `| None` (Python 3.10+) instead of `Optional[Type]`.
- Use `from __future__ import annotations` at the top of every file.
- Prefer `list[...]`, `dict[...]`, `set[...]`, `tuple[...]` over `typing.List`, etc.

### Anti-patterns
```python
# ❌ Bad — missing return type, missing parameter type
def _to_response(reg):
    return RegistrationResponse(...)

# ✅ Good
def _to_response(reg: LeaderRegistration) -> RegistrationResponse:
    """Map domain model to response schema."""
    return RegistrationResponse(...)
```

### How to check
```bash
# Find functions missing return type hints
ruff check --select ANN app/ --ignore ANN001,ANN201

# ANN001: missing type for function argument
# ANN201: missing return type for public function
# ANN202: missing return type for private function
```

---

## 5. Error Handling

### Rules
- **Never** use bare `except:`. Always specify the exception type.
- **Never** use `except: pass` silently.
- **Never** log exception objects with `%s` formatting that calls `str()` — use `exc_info=True` or `%s` with `e`.
- Always chain exceptions with `from exc` to preserve context.
- HTTPException in routers: use the right status codes (404 for not found, 409 for conflict, 422 for validation, 403 for auth).
- **Domain layer** (`domain/`) must never raise `HTTPException`. Raise `PermissionError`, `ValidationError`, etc. and let the adapter layer convert.

### Anti-patterns
```python
# ❌ Bad — bare except
try:
    result = await provisioner.provision_user(...)
except:
    pass

# ✅ Good
try:
    result = await provisioner.provision_user(...)
except IdpProvisioningError as exc:
    reg.idp_provision_status = "FAILED"
    reg.idp_provision_error = str(exc)
```

### How to check
```bash
# Find bare except clauses
ruff check --select E722 app/

# Find except: pass (silent failures)
grep -rn "except.*:" app/ --include="*.py" | grep -v "as e\|as exc" | grep -v "Exception\|Error\|Http404"

# Verify domain layer has no framework imports
grep -rn "HTTPException\|fastapi" app/domain/ --include="*.py"
# Expected: empty — domain must not depend on FastAPI
```

---

## 6. Project-Specific Rules

### Hexagonal Architecture
- `domain/` → pure Python, zero framework imports (no FastAPI, no SQLAlchemy, no aiohttp)
- `application/` → orchestration, depends only on domain ports
- `adapters/api/` → FastAPI concerns only (routing, HTTP, auth)
- `adapters/db/` → SQLAlchemy implementation of repository interfaces

**Violation check:**
```bash
grep -rn "HTTPException\|fastapi\|from sqlalchemy" app/domain/ --include="*.py"
# Must return empty
```

### Formatting & Linting
The project uses Ruff with `line-length = 100`. The following rules are active:
- `E`, `F`, `W` — pycodestyle, pyflakes, pycodestyle warnings
- `I` — import sorting (isort)
- `N` — naming conventions (pep8-naming)
- `UP` — pyupgrade (Python 3.11+ idioms)
- `B` — flake8-bugbear
- `C4` — flake8-comprehensions
- `D` — pydocstyle (docstrings)
- `RUF` — Ruff-specific rules

```bash
# Run all checks before committing
ruff check app/ tests/
ruff format --check app/ tests/
```

### i18n / Locale
German error messages use `ß` consistently (not `ss`). When writing user-facing strings:
- `"Nicht gefunden"` (not "nicht gefunden")
- Use domain-consistent terms: `Bezirk`, `Gemeinde`, `Amtstragende`

---

## 7. Testing

### Rules
- Every endpoint handler should have at least one positive and one negative test.
- Tests should assert on the **response** (status code, body shape), not on internal implementation details.
- Use `pytest` with `pytest-asyncio` for async endpoints.
- Mock external services (IDP, calendar connectors) — don't call them in unit tests.

### Coverage targets
| Layer | Coverage target | How to run |
|-------|----------------|------------|
| domain/ | ≥90% | `pytest tests/unit/test_domain/` |
| application/ | ≥80% | `pytest tests/unit/test_application/` |
| adapters/api/ | ≥80% | `pytest tests/unit/test_api/` |
| adapters/db/ | ≥60% (integration) | `pytest tests/integration/` |

---

## 8. Quick Reference: Decision Tree

```text
Änderung schreiben oder reviewen?
│
├── Neue Datei?
│   ├── Type Hints vorhanden? → Nein → ANN-Regeln prüfen
│   └── from __future__ import annotations? → Nein → hinzufügen
│
├── Neuer Endpoint?
│   ├── Permission-Check mit require_role_in_district()? → Nein → ersetzen
│   └── Existiert der District-Check als Helfer? → Nein → extrahieren
│
├── Neue Funktion?
│   ├── Name erklärt "was" UND "warum"? → Nein → umbenennen
│   ├── Macht sie genau eine Sache? → Nein → SRP aufteilen
│   └── > 30 Zeilen? → Nein → aufteilen erwägen
│
├── Refactoring?
│   ├── Pattern ≥3x wiederholt? → Helfer extrahieren
│   ├── Magic Number/String? → Konstante benennen
│   └── Zeitberechnung Duplikat? → _expected_times() / _actual_times() nutzen
│
└── Bugfix?
    ├── except: pass? → expliziten Typ verwenden
    └── chain with from exc? → hinzufügen
```
