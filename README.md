# JobHunter AI

JobHunter AI is a resume-first job discovery, matching, ranking, tracking, and alerting system. It discovers relevant opportunities across supported job sources, compares jobs with the resume, recommends strong matches, tracks applications, and sends smart alerts.

## Current project status

**Milestone 14.12 is complete. V1 remains in the final production release-validation phase.** The executor accepts only an explicitly approved, review-ready package, fingerprints the exact package, atomically reserves it before external interaction, and persists the outcome. Automatic application submission is **not yet complete**.

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

## Safety boundary

JobHunter **does not automatically submit applications merely because a job has a high match score**. Application submission remains a separate, explicitly authorized workflow and must use supported application flows.

The system must never fabricate qualifications, experience, answers, documents, or skills. If required information is missing or cannot be safely determined, the workflow must pause for user input.

The resume-review workflow is **review-only**: it identifies recommended/required modifications but does not silently modify the user's resume.

Required application questions are modeled separately from supplied answers. Missing required answers are surfaced before durable state is claimed or an external adapter is called.

The submission executor reserves the exact package in durable state before calling an adapter. A previously submitted package can never be submitted again, even after restart. An unresolved in-progress attempt is blocked rather than retried automatically because its external outcome is unknown. Only an explicitly recorded failed attempt is eligible for the retry API, and only retryable adapter failures are intended to be retried.

ATS adapters validate the supported HTTPS host family and delegate to a caller-provided authorized transport. They do not automate browsers, bypass login controls, bypass CAPTCHAs, evade anti-bot controls, or override platform restrictions.

## Milestone 14 roadmap

| Stage | Scope | Status |
| --- | --- | --- |
| 14.1 | Resume skill-gap analysis | ✅ Complete |
| 14.2 | Conservative resume improvement recommendations | ✅ Complete |
| 14.3 | Safe application preparation | ✅ Complete |
| 14.4 | Resume review alerts and decision | ✅ Complete |
| 14.5 | Application approval notifications | ✅ Complete |
| 14.6 | Explicit application authorization | ✅ Complete |
| 14.7 | Submission-authorization gate | ✅ Complete |
| 14.8 | Safe submission executor foundation | ✅ Complete |
| 14.9 | Persistent duplicate prevention / submission state | ✅ Complete |
| 14.10 | Missing-information and failure/retry handling | ✅ Complete |
| 14.11 | Supported ATS submission adapters | ✅ Complete |
| 14.12 | End-to-end submission validation | ✅ Complete |

### Current position: V1 release validation

Milestone 14.12 validates the complete safe submission path across all four supported ATS adapter boundaries. Integration coverage verifies that explicit approval and complete information are required, unsupported or blocked flows never reach the transport, successful submissions are persisted, and duplicate submissions are rejected.

## Core workflow — no Excel required

Excel is **not required for the core workflow**. It may remain an optional import/export utility.

```text
Resume + Preferences
        ↓
Multi-source Job Discovery
        ↓
Normalize + Deduplicate
        ↓
Resume / Skill Matching
        ↓
Preference Filtering
        ↓
Recommendation Ranking
        ↓
Resume Review / Application Preparation
        ↓
Explicit User Authorization
        ↓
Submission Permit
        ↓
Missing-Information Gate
        ↓
Safe Submission Executor
        ↓
Persistent Submission State
        ↓
Supported ATS Submission Adapter
        ↓
End-to-End Submission Validation
        ↓
Application Tracking + Alerts
```

## Development and release gate

Run the full automated suite with:

```bash
pytest
```

The release gate requires green CI plus the production smoke checklist. Automatic application submission must not be marked complete until authorization, durable duplicate prevention, missing-information handling, notification delivery, supported-flow behavior, and safe failure paths have dedicated automated coverage.

### V1 release milestones

| # | Milestone | Status |
| --- | --- | --- |
| 1 | Job Discovery & Matching | ✅ Complete |
| 2 | Recommendation & Tracking | ✅ Complete |
| 3 | Notifications & Dashboard | ✅ Complete |
| 4 | Production Readiness | ✅ Complete |
| 5 | Automated Production Runner | ✅ Complete |
| 6 | V1 Hardening & Release | 🧪 Release validation |

After both pass, the repository can be tagged `v1.0.0`.

See `docs/PRODUCTION.md` for configuration and operations. See `docs/RELEASE_CHECKLIST.md` for the final release gate. See `CHANGELOG.md` for release notes.
