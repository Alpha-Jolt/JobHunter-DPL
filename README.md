# Data Persistence Layer

Public guide for the `shared/` package — the data layer used by all three JobHunter Phase 0 engines.

---

## What This Package Does

`shared/` provides three things to every engine in the system:

1. **Data models** — validated, serialisable Python dataclasses for jobs, resume variants, and applications.
2. **Registry interfaces** — abstract base classes that define a consistent read/write contract.
3. **Storage implementations** — JSON-backed registries for Phase 0, with PostgreSQL stubs ready for Phase 0+.

No engine imports from another engine. They all depend only on `shared/`.

---

## Package Layout

```
shared/
├── __init__.py
├── models/
│   ├── job_record.py          # JobRecord — immutable scraped job listing
│   ├── variant_record.py      # VariantRecord — AI-generated resume variant
│   ├── application_record.py  # ApplicationRecord — sent application tracking
│   └── exceptions.py          # All custom exceptions
├── registries/
│   ├── base.py                # Abstract interfaces (JobRegistryBase, etc.)
│   ├── job_registry.py        # JSON implementation → registries/jobs.json
│   ├── variant_registry.py    # JSON implementation → registries/variants.json
│   └── application_log.py     # JSON implementation → registries/applications.json
├── repositories/
│   ├── postgres_job_repository.py          # PostgreSQL stub (Phase 0+)
│   ├── postgres_variant_repository.py      # PostgreSQL stub (Phase 0+)
│   └── postgres_application_repository.py  # PostgreSQL stub (Phase 0+)
├── tests/                     # Full pytest suite (128 tests, 89% coverage)
├── requirements.txt
└── pyproject.toml
```

---

## Models

### JobRecord (`models/job_record.py`)

Immutable (`frozen=True`) dataclass representing one scraped job listing.

| Field | Type | Constraints |
|---|---|---|
| `job_id` | `uuid.UUID` | Required |
| `source` | `str` | `"linkedin"`, `"naukri"`, `"indeed"` |
| `external_id` | `str` | Required |
| `title` | `str` | Required |
| `company_name` | `str` | Required |
| `company_domain` | `str \| None` | — |
| `location` | `str \| None` | — |
| `remote_type` | `str \| None` | `"onsite"`, `"hybrid"`, `"remote"`, `None` |
| `salary_min/max` | `float \| None` | — |
| `experience_min/max` | `int \| None` | — |
| `description` | `str` | Required |
| `skills_required` | `list[str]` | Defaults to `[]` |
| `job_type` | `str` | `"fulltime"`, `"parttime"`, `"contract"`, `"internship"` |
| `apply_email` | `str \| None` | — |
| `email_trust` | `str` | `"unknown"`, `"verified"`, `"low"` |
| `apply_url` | `str \| None` | — |
| `posted_at / scraped_at / last_seen_at` | `datetime \| None` | ISO 8601 in JSON |
| `status` | `str` | `"raw"`, `"reviewed"`, `"applied"`, `"closed"` |

**Methods:** `from_dict(data)`, `to_dict()`, `validate()`

### VariantRecord (`models/variant_record.py`)

Mutable dataclass representing an AI-generated resume variant awaiting user approval.

Key fields: `variant_id`, `user_id`, `job_id`, `master_resume_id`, `pdf_key`, `docx_key`, `curated_json`, `gaps_identified`, `approval_status` (`"pending"` / `"approved"` / `"rejected"`), `approval_token`, `approved_at`, `prompt_version`.

**Methods:** `from_dict(data)`, `to_dict()`, `validate()`, `is_approved()`, `is_pending()`

### ApplicationRecord (`models/application_record.py`)

Mutable dataclass tracking a single sent job application.

Key fields: `application_id`, `user_id`, `job_id`, `resume_variant_id`, `cover_letter_id`, `status` (`"sent"` / `"replied"` / `"interview_scheduled"` / `"rejected"` / `"ghosted"`), `sent_at` (defaults to UTC now), `reply_count` (defaults to 0), `thread_id`, `email_subject`, `notes`.

**Methods:** `from_dict(data)`, `to_dict()`, `validate()`, `get_days_since_sent()`

### Exceptions (`models/exceptions.py`)

| Exception | Raised when |
|---|---|
| `JobNotFoundError` | `JobRegistry.get()` finds no match |
| `VariantNotFoundError` | `VariantRegistry.get()` finds no match |
| `ApplicationNotFoundError` | `ApplicationLog.get()` finds no match |
| `ApprovalRequiredError` | An unapproved variant is used |
| `RegistryError` | Registry constraint violated (duplicate, budget) |
| `DeserializationError` | `from_dict()` receives invalid data |

All inherit from `SharedLayerError(Exception)` and accept `(message, context: dict)`.

---

## Registries

All registry methods are `async`. The JSON implementations are production-ready for Phase 0.

### JobRegistry

```python
from shared.registries.job_registry import JobRegistry

registry = JobRegistry(file_path="registries/jobs.json")  # default path

await registry.save(jobs)                        # upsert list of JobRecords by job_id
job   = await registry.get(job_id)               # raises JobNotFoundError if missing
jobs  = await registry.get_many([id1, id2])
jobs  = await registry.get_all_with_email()      # only jobs with apply_email set
jobs  = await registry.get_by_source("linkedin")
jobs  = await registry.get_by_status("raw")
found = await registry.exists(job_id)            # bool
n     = await registry.count()
n     = await registry.delete_by_source("naukri")  # returns count deleted
```

### VariantRegistry

```python
from shared.registries.variant_registry import VariantRegistry

registry = VariantRegistry(file_path="registries/variants.json")

await registry.save(variant)          # raises RegistryError on duplicate (user_id, job_id)
v  = await registry.get(variant_id)
vs = await registry.get_for_job(job_id)
v  = await registry.get_approved_for_job(job_id, user_id)  # None if not approved
vs = await registry.get_for_user(user_id)
vs = await registry.get_pending_for_user(user_id)
await registry.update_approval_status(variant_id, "approved")
await registry.update_approval_token(variant_id, token)
found = await registry.exists(variant_id)
n     = await registry.count_by_user(user_id)
```

**Constraints enforced on `save()`:**
- One variant per `(user_id, job_id)` pair — raises `RegistryError` on duplicate.
- Max 50 variants per user per session — raises `RegistryError` when exceeded.

### ApplicationLog

```python
from shared.registries.application_log import ApplicationLog

log = ApplicationLog(file_path="registries/applications.json")

await log.record_send(record)          # raises RegistryError if user already applied to job
app  = await log.get(application_id)
apps = await log.get_by_user(user_id)
apps = await log.get_by_job(job_id)
dup  = await log.has_user_applied_to_job(user_id, job_id)  # bool
apps = await log.get_applications_sent_today(user_id)       # last 24 hours
await log.update_status(application_id, "replied")
await log.update_reply_count(application_id, 3)
n    = await log.count_by_user(user_id)
await log.clear_old_records(days=90)   # archive utility
```

---

## Concurrency and File Safety

- All file I/O runs in a `ThreadPoolExecutor` — never blocks the event loop.
- `JobRegistry.save()` holds an `asyncio.Lock` — concurrent async saves are serialised.
- All writes are atomic: written to a temp file, then `os.replace()` over the target.
- File-level locking: `fcntl.flock` on Unix, `msvcrt.locking` on Windows.

---

## Phase 0 → Phase 0+ Migration

The abstract base classes (`JobRegistryBase`, `VariantRegistryBase`, `ApplicationLogBase`) are the stable contract. The JSON implementations satisfy them today. PostgreSQL implementations in `repositories/` are stubbed and ready to be filled in.

To migrate: replace the concrete class at the injection point. No model or interface changes required.

```python
# Phase 0
from shared.registries.job_registry import JobRegistry
registry = JobRegistry()

# Phase 0+
from shared.repositories.postgres_job_repository import PostgresJobRepository
registry = PostgresJobRepository(session=db_session)
```

---

## Engine Integration

### Scraper → JobRegistry

The scraper writes deduplicated jobs via `RegistryOutput`, a `BaseOutput` adapter.
Enable it with `USE_REGISTRY=true` in `scraper/.env` or `Config(use_registry=True)` in code.
The registry file defaults to `registries/jobs.json` (configurable via `REGISTRY_PATH`).

```python
# scraper/scraper/output/registry_output.py
from shared.registries.job_registry import JobRegistry
registry = JobRegistry()  # reads/writes registries/jobs.json
await registry.save(job_records)  # called automatically by the pipeline
```

### AI Engine → JobRegistry + VariantRegistry

Reads `"raw"` jobs from `JobRegistry` via `registry_reader.py`, generates variants,
and saves them to `VariantRegistry` via `SharedVariantRegistry` adapter.
Enable with `USE_SHARED_REGISTRY=true` in `ai_engine/.env`.

### Mail Engine → VariantRegistry + ApplicationLog _(Phase 0+)_

Reads approved variants via `get_approved_for_job()`, checks `has_user_applied_to_job()`, then calls `record_send()`.

---

## Troubleshooting

**`DeserializationError` on `from_dict()`** — A required field is missing or a UUID/enum value is invalid. Check the `context` dict on the exception for the offending data.

**`RegistryError: Variant already exists`** — One variant per `(user_id, job_id)` is enforced. Call `get_for_job()` to inspect existing variants before saving.

**`RegistryError: User has already applied`** — Call `has_user_applied_to_job()` before `record_send()`.

**`JobNotFoundError` / `VariantNotFoundError` / `ApplicationNotFoundError`** — The record does not exist. Use `exists()` to check before calling `get()`.

**JSON file missing or empty** — Registries self-initialise on first access. The `registries/` directory is created automatically.
