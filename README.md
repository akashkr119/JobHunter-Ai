# JobHunter AI

JobHunter AI is a resume-first job discovery, matching, ranking, tracking, and alerting system. It discovers relevant opportunities across supported job sources, compares jobs with the resume, recommends strong matches, tracks applications, and sends smart alerts.

## Current project status

**V1 remains in the hardening/release-validation phase. Milestone 14 has completed its current safety foundations through the explicit application-submission authorization gate.** The remaining work is the supported submission-flow implementation and its duplicate-prevention, missing-information, notification-delivery, and failure-path validation. Automatic application submission is **not yet complete**.

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

## Safety boundary

JobHunter **does not automatically submit applications merely because a job has a high match score**. Application submission remains a separate, explicitly authorized workflow and must use supported application flows.

The system must never fabricate qualifications, experience, answers, documents, or skills. If required information is missing or cannot be safely determined, the workflow must pause for user input.

The resume-review workflow is **review-only**: it identifies recommended/required modifications but does not silently modify the user's resume.

The submission gate itself does **not** contact or submit to any external website.

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
| 14.8 | Safe submission executor foundation | 🚧 Next |
| 14.9 | Duplicate prevention / submission state persistence | 🚧 Pending |
| 14.10 | Missing-information and failure/retry handling | 🚧 Pending |
| 14.11 | Supported ATS submission adapters | 🚧 Pending |
| 14.12 | End-to-end submission validation | 🚧 Pending |

### Current position: Milestone 14.8

The next implementation step is the **safe submission executor foundation**. It will accept only a valid `SubmissionPermit`, identify the exact application package by a stable fingerprint, block duplicate execution, return explicit success/failure results, and keep the external interaction behind a supported adapter interface.

No login bypass, CAPTCHA bypass, protected-page scraping, or automatic submission should be introduced without an explicit supported integration and dedicated safety tests.

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
Supported Submission Adapter
        ↓
Application Tracking + Alerts
```

## Development and release gate

Run the full automated suite with:

```bash
pytest
```

The release gate requires green CI plus the production smoke checklist. Automatic application submission must not be marked complete until authorization, duplicate prevention, missing-information handling, notification delivery, supported-flow behavior, and safe failure paths have dedicated automated coverage.

See `docs/PRODUCTION.md` for configuration and operations. See `CHANGELOG.md` for release notes.
