# JobHunter AI

JobHunter AI is a **resume-first job discovery, matching, ranking, tracking, and alerting system**. The user's resume is the primary input. JobHunter AI analyzes the resume, discovers relevant jobs from configured/authorized job sources, compares jobs with the user's real skills and preferences, scores and ranks the opportunities, asks the user to validate application decisions, and provides resume-improvement guidance when recurring job requirements reveal gaps.

## Product concept — resume first

The user should **not have to provide career/ATS URLs as part of normal setup**. JobHunter AI should discover jobs from supported/authorized sources using the user's resume, detected roles, selected locations, work-mode preferences, and optional search preferences.

### User flow

```text
Upload Resume
     ↓
Parse Resume
     ↓
Build Candidate Profile
     ├── Skills
     ├── Experience
     ├── Projects
     ├── Technologies
     ├── Experience level
     └── Suggested target roles
     ↓
User reviews/edits target roles
     ↓
User selects one or more locations
     ↓
User selects work mode(s)
     ↓
Discover Jobs Now
     ↓
Resume ↔ Job Matching
     ↓
ATS / eligibility / recommendation scoring
     ↓
Ranked Job Results
     ↓
User validates each recommended application
     ↓
Apply only after explicit approval
```

### Setup requirements

- **Resume:** upload PDF, DOCX, TXT, or Markdown. The uploaded resume becomes the active resume for that user.
- **Target roles:** derive suggested roles from the resume; do not hard-code a default role list. The user can add, remove, or edit the detected roles.
- **Locations:** use a multi-select location control rather than a free-text location field. A user can select multiple cities/regions and `Remote` where supported.
- **Work mode:** provide selectable `On-site`, `Hybrid`, and `Remote` options; multiple selections are allowed.
- **Career URLs:** remove from the normal setup experience. Career/ATS URLs remain an internal/source capability where needed, not a user requirement for the product's core workflow.
- **Matching preferences:** optional minimum score, desired keywords, and excluded keywords may remain user-configurable.

## Automatic job discovery — every 24 hours

The automatic discovery feature runs **once every 24 hours** for each active user. It uses that user's active resume, detected/approved target roles, selected locations, work modes, and notification preferences.

```text
Active User Profile
       ↓
24-hour Scheduler
       ↓
Search supported/authorized job sources
       ↓
Normalize + deduplicate
       ↓
Resume/skill matching
       ↓
Preference filtering
       ↓
ATS/eligibility + recommendation scoring
       ↓
Compare with previously seen jobs
       ↓
Notify only about relevant/new actionable results
```

A failed scan for one user must not stop scans for other users. Scheduled scans need run history, locking/idempotency, bounded retries, and user-scoped notification delivery.

## Job validation and application workflow

A high score is a **recommendation**, not permission to apply automatically.

For a recommended job, the dashboard/notification should provide:

- Job title, company, location, work mode, and application link.
- Resume match score and recommendation/ATS score.
- Matched skills and missing/weak requirements.
- Explanation of why the job was recommended.
- A clear user decision such as **Review**, **Apply**, or **Don't Apply**.

Automatic application submission may proceed only after the user explicitly approves that specific application and the required information is complete. The system must never fabricate qualifications, experience, answers, or skills.

## Resume improvement intelligence

JobHunter AI should learn from the jobs it discovers without inventing experience for the user.

When relevant jobs repeatedly require skills or experience that are missing or weakly represented in the current resume, the system should create a **Resume Update Recommended** notification containing:

- Frequently requested skills/requirements.
- How often they appeared in relevant jobs.
- Which resume sections appear weak or missing.
- Concrete suggestions for improving the resume **only when supported by the user's actual experience**.
- A clear review step before any resume change becomes active.

The system must not silently rewrite, replace, or add false experience to a resume.

## Notifications

Supported notification destinations may include email and Telegram. Notifications are user-scoped and must never cross accounts.

Examples:

- New strong job matches found.
- A job requires user validation before application.
- A previously seen job changed meaningfully.
- Resume update recommendations are available.
- Required application information is missing.

## Multi-user architecture

JobHunter AI is planned as a **multi-user, multi-tenant application**, not a single-user VM application. The initial target is **30+ users**, with a clean path to substantially more users.

```text
Users / Browsers
       ↓
Authentication + Session Layer
       ↓
Web Application / API
       ├──────────────→ PostgreSQL / production relational DB
       │                    └── user_id scoped records
       │
       ├──────────────→ Persistent file/object storage
       │                    └── per-user resume files + versions
       │
       └──────────────→ Background workers / scheduler
                            └── per-user 24h discovery + notifications
```

Each account must have isolated:

- Login identity and securely hashed password credentials.
- Profile and job-search preferences.
- Active resume and historical resume versions.
- Resume analysis, detected roles, and skill-gap results.
- Discovered jobs and user-specific match/recommendation results.
- Saved jobs, notes, follow-ups, and application records.
- Application packages, approvals, submission state, and audit history.
- Email/Telegram notification configuration and notification history.
- Scheduled scan configuration and run history.

User-owned records must be scoped by authenticated `user_id` and protected at the application/service layer. One user must never read, modify, or receive another user's private data or notifications.

### Resume storage and lifecycle

A browser upload becomes the user's active resume without manual SSH/file copying. Resume files must be stored in persistent application storage with versioning and metadata. The active approved resume is used by future matching and scheduled scans. Previous versions remain available for controlled history/audit purposes.

### Database and credentials strategy

SQLite may remain useful for local/single-user development, but the multi-user production target should use **PostgreSQL or an equivalent production-grade relational database** with migrations, indexes, transactions, backups, and connection pooling.

User passwords must never be stored in plaintext. External-service credentials and secrets must be encrypted/protected and must not be committed to the repository. Application secrets should be supplied through secure deployment configuration or secret management.

### Scheduler and background processing

The production default for automatic job discovery is **24 hours** (`scheduler_hours = 24`). Scheduled work must execute using each user's own active resume and preferences. The worker/scheduler layer should support safe concurrency, retries, run history, locking/idempotency, and horizontal scaling.

## Current project status

**Milestone 14.12 is complete. V1 remains in release-validation/hardening.** The executor accepts only an explicitly approved, review-ready package, fingerprints the exact package, atomically reserves it before external interaction, and persists the outcome. Automatic application submission is **not yet complete**.

### Implemented

- Resume parsing for TXT, Markdown, PDF, and DOCX.
- Resume-to-job skill gap analysis and conservative resume improvement recommendations.
- Job preferences, weighted recommendation ranking, explanations, and lifecycle tracking.
- Multi-source discovery, authorized/opt-in integrations, ATS discovery, deduplication, and provenance.
- Source health/reliability monitoring, application tracking, saved jobs, notes, follow-ups, dashboard analytics, and production runner.
- Email/Telegram notification thresholds and review-ready application notifications.
- Safe application-preparation package with review-only resume modification guidance.
- Explicit application authorization: prepared applications start pending and require explicit user approval.
- Explicit submission gate: only an approved authorization with a valid approval ID can produce a submission permit tied to the exact prepared package.
- Safe submission executor foundation: stable package fingerprinting, adapter boundary, explicit result status, duplicate blocking, and retry-safe failure behavior.
- Persistent submission state: SQLite-backed package lifecycle, atomic pre-submission reservation, durable submitted/failed outcomes, and conservative crash recovery that blocks unresolved attempts.
- Missing-information gate: required application questions are tracked explicitly and block submission without inventing answers.
- Failure/retry handling: retryable adapter failures are explicitly classified and can be retried; non-retryable failures are recorded but are not retried through the retry API.
- Supported ATS adapter boundaries: Greenhouse, Lever, Workday, and SmartRecruiters adapters validate HTTPS ATS URLs and delegate only to a caller-provided authorized transport.
- End-to-end submission workflow: approved packages pass authorization, completeness, durable idempotency, and supported-ATS adapter validation before the caller-provided transport is reached.

## Core workflow — no career URL required

Career/ATS URLs can still exist inside source adapters, but they are **not required from the user for the core workflow**.

```text
Resume + User Preferences
        ↓
Detected / Approved Target Roles
        ↓
Selected Locations + Work Modes
        ↓
Multi-source Job Discovery
        ↓
Normalize + Deduplicate
        ↓
Resume / Skill Matching
        ↓
Preference Filtering
        ↓
ATS / Eligibility / Recommendation Ranking
        ↓
New/Relevant Job Notification
        ↓
User Validation
        ↓
Explicit Application Authorization
        ↓
Missing-Information Gate
        ↓
Safe Submission Executor
        ↓
Application Tracking + Alerts
        ↓
Resume Gap Analysis
        ↓
Resume Update Recommendation
```

## Safety boundary

JobHunter **does not automatically submit applications merely because a job has a high match score**. Application submission remains a separate, explicitly authorized workflow and must use supported application flows.

The system must never fabricate qualifications, experience, answers, documents, or skills. If required information is missing or cannot be safely determined, the workflow must pause for user input.

The resume-review workflow is **review-only**: it identifies recommended/required modifications but does not silently modify the user's resume.

Required application questions are modeled separately from supplied answers. Missing required answers are surfaced before durable state is claimed or an external adapter is called.

The submission executor reserves the exact package in durable state before calling an adapter. A previously submitted package can never be submitted again, even after restart. An unresolved in-progress attempt is blocked rather than retried automatically because its external outcome is unknown. Only an explicitly recorded failed attempt is eligible for the retry API, and only retryable adapter failures are intended to be retried.

ATS adapters validate the supported HTTPS host family and delegate to a caller-provided authorized transport. They do not automate browsers, bypass login controls, bypass CAPTCHAs, evade anti-bot controls, or override platform restrictions.

## Multi-user scalability milestones

| Area | Target |
| --- | --- |
| Authentication | Secure registration/login/session management |
| Authorization | User-level access control and data isolation |
| Database | PostgreSQL schema, migrations, indexes, transactions |
| Storage | Persistent per-user resume storage and versioning |
| Resume intelligence | Resume parsing, detected roles, skill gaps, review-only recommendations |
| Job discovery | Source-agnostic discovery without requiring user-entered career URLs |
| Preferences | Multi-select locations and work modes; user-editable detected roles |
| Scheduler | Per-user automatic discovery every 24 hours |
| Jobs | User-scoped discovery, matching, tracking, and deduplication |
| Applications | User-scoped authorization, packages, submission state, and audit trail |
| Notifications | User-scoped email/Telegram configuration and delivery |
| Operations | Backups, logging, health checks, monitoring, and recovery |
| Capacity | Validate 30+ users, then scale workers/database/storage independently |

**Until this foundation is implemented and validated, the existing single-user SQLite/VM configuration should not be represented as the final architecture for a 30+ user service.**

## Development and release gate

Run the full automated suite with:

```bash
pytest
```

The release gate requires green CI plus the production smoke checklist. Automatic application submission must not be marked complete until authorization, durable duplicate prevention, missing-information handling, notification delivery, supported-flow behavior, and safe failure paths have dedicated automated coverage.

See `docs/PRODUCTION.md` for configuration and operations. See `docs/RELEASE_CHECKLIST.md` for the final release gate. See `CHANGELOG.md` for release notes.
