# Data Persistence Layer

Public guide for the `shared/` package — the data layer used by all JobHunter engines.

> **Version:** 0.3.0 | **Phase:** 1

---

## What This Package Does

`shared/` provides three things to every engine in the system:

1. **Data models** — validated, serialisable Python dataclasses for jobs, resume variants, applications, companies, and career page jobs.
2. **Registry interfaces** — abstract base classes that define a consistent read/write contract.
3. **Storage implementations** — JSON-backed registries for Phase 0/alpha, with PostgreSQL repositories for production.

No engine imports from another engine. They all depend only on `shared/`.

---

## Package Layout

```
shared/
├── __init__.py
├── models/
│   ├── job_record.py           # JobRecord — scraped job listing (Naukri/Indeed)
│   ├── variant_record.py       # VariantRecord — AI-generated resume variant
│   ├── application_record.py   # ApplicationRecord — sent application tracking
│   ├── company_record.py       # CompanyRecord — discovered and enriched company
│   ├── career_job_record.py    # CareerJobRecord — job from a company career page
│   └── exceptions.py           # All custom exceptions
├── registries/
│   ├── base.py                 # Abstract interfaces for all registries
│   ├── job_registry.py         # JSON implementation → registries/jobs.json
│   ├── variant_registry.py     # JSON implementation → registries/variants.json
│   ├── application_log.py      # JSON implementation → registries/applications.json
│   ├── company_registry.py     # JSON implementation → registries/companies.json
│   └── career_jobs_registry.py # JSON implementation → registries/career_jobs.json
├── repositories/
│   ├── postgres_job_repository.py          # PostgreSQL — jobs table
│   ├── postgres_variant_repository.py      # PostgreSQL — resume_variants table
│   ├── postgres_application_repository.py  # PostgreSQL — application_log table
│   ├── postgres_company_repository.py      # PostgreSQL — companies table
│   └── postgres_career_jobs_repository.py  # PostgreSQL — career_jobs table
├── tests/                      # Full pytest suite
├── requirements.txt
└── pyproject.toml
```

---

## Models

### JobRecord (`models/job_record.py`)

Immutable (`frozen=True`) dataclass representing one scraped job listing from Naukri or Indeed.

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

Mutable dataclass for an AI-generated resume variant awaiting user approval.

Key fields: `variant_id`, `user_id`, `job_id`, `master_resume_id`, `pdf_key`, `docx_key`, `cover_letter_key`, `local_pdf_path`, `s3_upload_failed`, `curated_json`, `gaps_identified`, `approval_status` (`"pending"` / `"approved"` / `"rejected"`), `approval_token`, `approved_at`, `prompt_version`.

**Methods:** `from_dict(data)`, `to_dict()`, `validate()`, `is_approved()`, `is_pending()`

### ApplicationRecord (`models/application_record.py`)

Mutable dataclass tracking a single sent job application.

Key fields: `application_id`, `user_id`, `job_id`, `resume_variant_id`, `cover_letter_id`, `status` (`"sent"` / `"replied"` / `"interview_scheduled"` / `"rejected"` / `"ghosted"`), `sent_at`, `reply_count`, `thread_id`, `email_subject`, `notes`.

**Methods:** `from_dict(data)`, `to_dict()`, `validate()`, `get_days_since_sent()`

### CompanyRecord (`models/company_record.py`)

Immutable (`frozen=True`) dataclass representing a discovered and enriched company
from Module 1 (Company Discovery Scraper).

| Field | Type | Constraints |
|---|---|---|
| `company_id` | `uuid.UUID` | Required |
| `apex_domain` | `str` | Required — canonical dedup key (e.g. `acme.com`) |
| `source` | `str` | `"bootstrap_dataset"`, `"govt_registry"`, `"vc_portfolio"`, `"github_org"`, `"directory"`, `"search_discovery"`, `"recursive"` |
| `dedup_fingerprint` | `str` | MD5 of `normalized_name + apex_domain` |
| `company_name` | `str \| None` | Raw extracted name |
| `normalized_name` | `str \| None` | Legal suffixes stripped, lowercase, non-alphanumeric removed |
| `subdomains` | `list[str]` | All discovered subdomains |
| `career_page_url` | `str \| None` | Resolved career section URL |
| `career_emails` | `list[str]` | Emails classified as HR/career-related |
| `contact_emails` | `list[str]` | All other extracted emails |
| `email_trust` | `str` | `"unverified"`, `"low_trust"` |
| `ats_platform` | `str` | `"greenhouse"`, `"lever"`, `"ashby"`, `"workday"`, `"smartrecruiters"`, `"bamboohr"`, `"teamtailor"`, `"recruitee"`, `"jazzhr"`, `"workable"`, `"custom"`, `"none"` |
| `crawl_status` | `str` | `"pending"`, `"enriched"`, `"failed"`, `"robots_blocked"`, `"access_denied"`, `"name_only"` |
| `robots_txt_allowed` | `bool \| None` | Whether enrichment scraping was permitted |
| `discovery_date` | `datetime` | When first added |
| `last_enriched_at` | `datetime \| None` | Last full enrichment run |
| `email_last_crawled_at` | `datetime \| None` | Drives monthly email refresh |
| `related_company_id` | `uuid.UUID \| None` | FK to related company (multi-domain same entity) |

**Module-level helpers:**
- `normalize_company_name(name)` — strips legal suffixes, lowercases, removes non-alphanumeric
- `build_dedup_fingerprint(normalized_name, apex_domain)` — MD5 hex digest

**Methods:** `from_dict(data)`, `to_dict()`

### CareerJobRecord (`models/career_job_record.py`)

Immutable (`frozen=True`) dataclass representing a job listing scraped from a company
career page by Module 2 (Career Page Job Scraper).

| Field | Type | Constraints |
|---|---|---|
| `career_job_id` | `uuid.UUID` | Required |
| `company_id` | `uuid.UUID` | FK to parent company |
| `job_title` | `str` | Required |
| `job_url` | `str` | Direct URL to job listing |
| `url_hash` | `str` | MD5 of normalised job URL — primary dedup key |
| `content_hash` | `str` | MD5 of title + description — change detection key |
| `extraction_method` | `str` | `"ats_api"`, `"json_ld"`, `"sitemap"`, `"api_reverse"`, `"html_parse"`, `"playwright_render"` |
| `status` | `str` | `"active"`, `"closed"`, `"raw"` |
| `source_channel` | `str` | Always `"career_page"` |
| `remote_type` | `str \| None` | `"onsite"`, `"hybrid"`, `"remote"` |
| `job_type` | `str \| None` | `"fulltime"`, `"parttime"`, `"contract"`, `"internship"`, `"freelance"` |
| `salary_min/max` | `int \| None` | INR |
| `experience_min/max` | `int \| None` | Years |
| `apply_email` | `str \| None` | Job-specific email or carried from company |
| `apply_url` | `str \| None` | Direct apply URL |
| `ats_platform` | `str \| None` | Inherited from company record |
| `posted_at` | `datetime \| None` | Posting date if extractable |
| `scraped_at / last_seen_at` | `datetime` | Tracking timestamps |

**Module-level helpers:**
- `normalize_job_url(url)` — lowercase, strip tracking params, strip trailing slash
- `compute_url_hash(normalized_url)` — MD5 hex digest
- `compute_content_hash(job_title, description)` — MD5 of normalised title + description

**Methods:** `from_dict(data)`, `to_dict()`

### Exceptions (`models/exceptions.py`)

| Exception | Raised when |
|---|---|
| `JobNotFoundError` | `JobRegistry.get()` finds no match |
| `VariantNotFoundError` | `VariantRegistry.get()` finds no match |
| `ApplicationNotFoundError` | `ApplicationLog.get()` finds no match |
| `ApprovalRequiredError` | An unapproved variant is used |
| `RegistryError` | Registry constraint violated |
| `DeserializationError` | `from_dict()` receives invalid data |

All inherit from `SharedLayerError(Exception)` and accept `(message, context: dict)`.

---

## Registries

All registry methods are `async`. JSON implementations are production-ready for Phase 0/alpha volumes.

### JobRegistry

```python
from shared.registries.job_registry import JobRegistry

registry = JobRegistry(file_path="registries/jobs.json")

await registry.save(jobs)                         # upsert list of JobRecords by job_id
job   = await registry.get(job_id)                # raises JobNotFoundError if missing
jobs  = await registry.get_many([id1, id2])
jobs  = await registry.get_all_with_email()
jobs  = await registry.get_by_source("naukri")
jobs  = await registry.get_by_status("raw")
found = await registry.exists(job_id)
n     = await registry.count()
n     = await registry.delete_by_source("indeed")
```

### VariantRegistry

```python
from shared.registries.variant_registry import VariantRegistry

registry = VariantRegistry(file_path="registries/variants.json")

await registry.save(variant)
v  = await registry.get(variant_id)
vs = await registry.get_for_job(job_id)
v  = await registry.get_approved_for_job(job_id, user_id)
vs = await registry.get_pending_for_user(user_id)
await registry.update_approval_status(variant_id, "approved")
await registry.update_approval_token(variant_id, token)
n  = await registry.count_by_user(user_id)
```

**Constraints enforced on `save()`:** one variant per `(user_id, job_id)`, max 50 per user.

### ApplicationLog

```python
from shared.registries.application_log import ApplicationLog

log = ApplicationLog(file_path="registries/applications.json")

await log.record_send(record)
app  = await log.get(application_id)
apps = await log.get_by_user(user_id)
dup  = await log.has_user_applied_to_job(user_id, job_id)
apps = await log.get_applications_sent_today(user_id)
await log.update_status(application_id, "replied")
await log.update_reply_count(application_id, 3)
```

### CompanyRegistry

```python
from shared.registries.company_registry import CompanyRegistry

registry = CompanyRegistry(file_path="registries/companies.json")

await registry.save(company)                          # upsert on apex_domain
await registry.save_many(companies)                   # upsert with array field merge
company = await registry.get(company_id)
company = await registry.get_by_apex_domain("acme.com")  # None if not found
companies = await registry.get_by_crawl_status("enriched")
companies = await registry.get_pending_email_refresh(older_than_days=30)
exists  = await registry.apex_domain_exists("acme.com")
domains = await registry.get_known_domains_set()      # set[str] — for queue dedup
await registry.update_crawl_status(company_id, "enriched")
await registry.update_enrichment(company_id, career_page_url="...", ats_platform="greenhouse")
n       = await registry.count()
counts  = await registry.count_by_crawl_status()     # {"enriched": 800, "pending": 200}
counts  = await registry.count_by_ats_platform()     # {"greenhouse": 120, "lever": 80, ...}
```

**Key behaviour:**
- `save_many()` merges `career_emails`, `contact_emails`, and `subdomains` arrays on conflict — never discards data.
- `update_enrichment()` only writes non-None values — never overwrites existing data with None.
- `get_known_domains_set()` returns all apex domains as a Python `set` for O(1) queue-level dedup.

### CareerJobsRegistry

```python
from shared.registries.career_jobs_registry import CareerJobsRegistry

registry = CareerJobsRegistry(file_path="registries/career_jobs.json")

await registry.save(job)                              # upsert on (company_id, url_hash)
await registry.save_many(jobs)
job  = await registry.get(career_job_id)
jobs = await registry.get_by_company(company_id)
jobs = await registry.get_active(limit=100, offset=0)
exists = await registry.url_hash_exists(company_id, url_hash)
hash_  = await registry.get_content_hash(company_id, url_hash)  # for change detection
await registry.update_last_seen(career_job_id)        # unchanged job — update timestamp only
await registry.update_content(career_job_id, content_hash="...", description="...")
await registry.mark_closed(career_job_id)
n = await registry.mark_missing_jobs_closed(company_id, seen_url_hashes)  # returns count
n = await registry.count()
n = await registry.count_by_company(company_id)
counts = await registry.count_active_by_company()    # {company_id_str: active_count}
```

**Key behaviour:**
- `mark_missing_jobs_closed()` takes the set of `url_hash` values seen in the latest crawl and closes everything else for that company — the primary closed-job detection mechanism.
- `get_content_hash()` retrieves only the hash without loading the full record — used for efficient change detection before deciding whether to re-parse.

---

## Concurrency and File Safety

- All file I/O runs in a `ThreadPoolExecutor` — never blocks the event loop.
- `asyncio.Lock` serialises concurrent writes within the same process.
- All writes are atomic: written to a temp file, then `os.replace()` over the target.
- File-level locking: `fcntl.flock` on Unix, `msvcrt.locking` on Windows.

---

## Phase 0 → PostgreSQL Migration

The abstract base classes are the stable contract. Swap the concrete class at the injection point — no model or interface changes required.

```python
# Phase 0 — JSON
from shared.registries.company_registry import CompanyRegistry
registry = CompanyRegistry()

# Production — PostgreSQL
from shared.repositories.postgres_company_repository import PostgresCompanyRepository
registry = PostgresCompanyRepository(session=async_session)
```

The same pattern applies to all five registries.

---

## Engine Integration

### Scraper → JobRegistry

Enable with `USE_REGISTRY=true` in `scraper/.env`. Jobs are written via `RegistryOutput` after the full pipeline. Registry file defaults to `registries/jobs.json`.

### Company Discovery → CompanyRegistry

The enrichment pipeline writes `CompanyRecord` objects via `CompanyRegistry.save_many()` after each batch. Dedup check uses `get_known_domains_set()` in-memory before enqueuing domains.

### Career Page Scraper → CareerJobsRegistry

On each crawl pass: `get_content_hash()` to check for changes, `update_last_seen()` for unchanged jobs, `save()` for new or changed jobs, `mark_missing_jobs_closed()` after the full company pass.

### AI Engine → JobRegistry + VariantRegistry

Reads `"raw"` jobs from `JobRegistry`, generates variants, saves to `VariantRegistry`. Enable with `USE_SHARED_REGISTRY=true` in `ai_engine/.env`.

### Mail Engine → VariantRegistry + ApplicationLog

Reads approved variants via `get_approved_for_job()`, checks `has_user_applied_to_job()`, then calls `record_send()`.

---

## Installing

```bash
# From git tag (production)
pip install jobhunter-dpl @ git+https://github.com/Alpha-Jolt/JobHunter-DPL.git@v0.3.0

# Editable local install (development)
pip install -e /path/to/JobHunter-DPL
```

---

## Running Tests

```bash
cd JobHunter-DPL
pip install -e ".[dev]"
pytest shared/tests/ -v --cov=shared --cov-report=term-missing
```

---

## Troubleshooting

**`DeserializationError` on `from_dict()`** — A required field is missing or an enum value is invalid. Check the `context` dict on the exception.

**`RegistryError: Variant already exists`** — One variant per `(user_id, job_id)`. Call `get_for_job()` before saving.

**`RegistryError: User has already applied`** — Call `has_user_applied_to_job()` before `record_send()`.

**`KeyError` on `registry.get()`** — Record does not exist. Use `exists()` or `apex_domain_exists()` to check first.

**JSON file missing or empty** — Registries self-initialise on first write. The `registries/` directory is created automatically.
