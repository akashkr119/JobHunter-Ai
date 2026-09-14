# JobHunter AI

JobHunter AI is a resume-first job discovery, matching, ranking, tracking, and alerting system. It discovers relevant opportunities across supported job sources, compares jobs with the resume, recommends strong matches, tracks applications, and sends smart alerts.

## Core workflow — no Excel required

Excel is **not required for the core workflow**. It may remain an optional import/export utility. The primary workflow is:

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
Dashboard + Email / Telegram Alerts
```

The system is source-adapter based and is designed to use legitimate/authorized APIs, feeds, company career/ATS pages, or supported search/apply links. It must not bypass login controls, CAPTCHAs, or platform restrictions.

## Current project status

**V1 is in the hardening/release-validation phase, with the roadmap's major foundation milestones implemented.** The current work is focused on making the remaining application-preparation and resume-review workflow safe, deterministic, tested, and production-ready before any feature is marked complete.

### Implemented

- Resume parsing for TXT, Markdown, PDF, and DOCX.
- Resume-to-job skill gap analysis with matched/missing skills and match ratio.
- Conservative resume improvement recommendations that never invent qualifications.
- Job preferences / target-profile filtering.
- Weighted recommendation ranking with explanation/breakdown.
- Multi-source discovery architecture with source adapters.
- Authorized/opt-in source integrations including Adzuna, LinkedIn, Indeed, and Naukri adapters.
- Greenhouse, Lever, Workday, and SmartRecruiters ATS discovery.
- Cross-source job deduplication and provenance tracking.
- Source configuration, freshness, failure history, health, reliability metrics, and alerts.
- Application tracking, saved jobs, notes, follow-up reminders, and dashboard analytics.
- Responsive dashboard with loading/empty/error states and safe action tracking.
- Production runner with scheduling, locking, run history, failure handling, and cleanup.
- Configurable Email/Telegram notification thresholds.
- Safe application-preparation package: structured job/resume/application information can be prepared for review without submitting an application.
- Resume review alerts and a deterministic review decision helper. Explicitly confirmed skills can make modification required; missing skills are never treated as evidence or added automatically.
- Explicit application authorization state: every prepared application starts pending and can become submittable only after an explicit user approval decision.

## Safety boundary

JobHunter **does not automatically submit applications merely because a job has a high match score**. Application submission remains a separate, explicitly authorized workflow and must use supported application flows.

The system must never fabricate qualifications, experience, answers, documents, or skills. If required information is missing or cannot be safely determined, the workflow must pause for user input.

The resume-review workflow is currently **review-only**: it can identify and explain recommended/required modifications, but it does not silently modify the user's resume or submit applications.

Application authorization is also explicit: a pending approval request cannot submit, a rejection cannot submit, and only an approved application package may proceed to a future supported submission step.

## Recommendation ranking

The recommendation engine combines multiple signals into a unified 0–100 score. The current weighting is:

- Resume / skill match — 50%
- Target preference alignment — 25%
- Freshness — 10%
- Application state — 10%
- Priority / lifecycle — 5%

Recommendations include an explanation/breakdown and labels such as **Top Pick**, **Strong Match**, **Good Match**, and **Consider**.

## Resume review and application preparation

Before applying, JobHunter can compare the job requirements with the current resume and identify meaningful gaps or improvement opportunities.

The review workflow distinguishes between:

- **Resume improvement recommended** — useful changes are suggested, but the application does not necessarily need to pause.
- **Resume modification required** — the available evidence indicates that an important truthful change should be reviewed before proceeding.

Application preparation creates a structured, reviewable package containing the job, resume path, cover letter, and optional application answers. It intentionally has **no automatic submission operation**.

Application authorization creates a pending approval request for that package. The system records the request and explicit decision timestamps, and exposes `can_submit` only for an approved package. Notification delivery and the eventual supported submission action remain separate workflow steps.

## Multi-source job discovery

```text
JobSource Manager
├── Authorized API integrations
├── Permitted feeds
├── Company career / ATS sources
├── Search/link providers
└── Future authorized integrations
             ↓
       Unified JobListing
             ↓
       Deduplication + Provenance
             ↓
       Matching + Ranking
             ↓
       Review / Tracking / Alerts
```

Each source normalizes results into the common job model so supported sources can participate in the same ranking, tracking, notification, and review workflow.

## Automated production runner

The production runner performs scheduled scans, prevents duplicate runner instances with a lock, records run history, handles failures, and cleans up on shutdown.

Important production settings include:

```text
JOBHUNTER_DATABASE_PATH
JOBHUNTER_RESUME_PATH
JOBHUNTER_MIN_MATCH_SCORE
JOBHUNTER_SCHEDULER_HOURS
JOBHUNTER_LOG_LEVEL
JOBHUNTER_RUN_HISTORY_PATH
JOBHUNTER_RUN_LOCK_PATH
JOBHUNTER_NOTIFICATION_CHANNEL
JOBHUNTER_NOTIFICATION_MIN_PRIORITY
JOBHUNTER_NOTIFICATION_MIN_RECOMMENDATION_SCORE
JOBHUNTER_AUTO_APPLY_ENABLED
JOBHUNTER_AUTO_APPLY_MIN_MATCH_SCORE
JOBHUNTER_RESUME_REVIEW_ENABLED
JOBHUNTER_SMTP_HOST
JOBHUNTER_SMTP_PORT
JOBHUNTER_SMTP_USERNAME
JOBHUNTER_SMTP_PASSWORD
JOBHUNTER_SMTP_SENDER
JOBHUNTER_EMAIL_RECIPIENT
JOBHUNTER_TELEGRAM_BOT_TOKEN
JOBHUNTER_TELEGRAM_CHAT_ID
```

## V1 roadmap

| Milestone | Scope | Status |
| --- | --- | --- |
| 1 | Application Follow-up System | ✅ Complete |
| 2 | Job Preferences / Target Profile | ✅ Complete |
| 3 | Recommendation Ranking Engine | ✅ Complete |
| 4 | Dashboard Finalization | ✅ Complete |
| 5 | Automated Production Runner | ✅ Complete |
| 6 | V1 Hardening & Release | 🧪 Release validation |
| 7 | Multi-Source Job Discovery | ✅ Implemented |
| 8 | Resume Review & Modification Alerts | ✅ Implemented — review-only |
| 9 | Safe Auto-Apply Workflow | 🚧 Not yet complete |

### Current position: Milestone 14

Milestone 14 has progressed through four focused foundations:

1. **Resume skill-gap analysis** — implemented and tested.
2. **Conservative resume improvement recommendations** — implemented and tested.
3. **Safe application preparation + resume review alerts/decision logic** — implemented and tested; review-only, with no automatic submission or silent resume modification.
4. **Explicit application authorization** — implemented and tested; prepared applications start pending and require an explicit approval decision before a future submission step can proceed.

The next work should focus on completing the remaining safe application-flow pieces and their duplicate-prevention, missing-information, notification-delivery, and failure-path tests. Only after those gates pass should the auto-apply milestone be marked complete.

## Current capabilities

JobHunter AI currently provides career-page and ATS discovery, multi-source adapters, resume parsing, skill-gap analysis, conservative resume improvement guidance, weighted recommendation ranking, preference filtering, lifecycle detection, cross-source deduplication/provenance, application tracking, saved jobs and notes, follow-up reminders, dashboard analytics, production execution, source health/reliability monitoring, and smart Email/Telegram alerts.

Automatic application submission is **not claimed as complete**. The current application-preparation, authorization, and resume-review work is intentionally review-first and safety constrained.

See `docs/PRODUCTION.md` for configuration, operations, notifications, and release validation. See `CHANGELOG.md` for release notes.

## Project structure

```text
JobHunter-Ai/
├── config/          # Runtime configuration
├── crawler/         # Career discovery and ATS/job scrapers
├── dashboard/       # Flask dashboard and API
├── database/        # SQLite persistence and migrations
├── matcher/         # Skill, preference, priority, gap and recommendation logic
├── notifier/        # Email and Telegram notifications
├── runner/          # Production lifecycle runner
├── scheduler/       # Pipeline orchestration and scheduling
├── docs/            # Production/deployment documentation
├── tests/           # Automated test suite
├── app.py
├── main.py
├── requirements.txt
└── pytest.ini
```

## Development and release gate

Run the full automated suite with:

```bash
pytest
```

The release gate requires green CI plus the production smoke checklist. After both pass, the repository can be tagged `v1.0.0`.

Application-preparation, resume-review, and future auto-apply functionality must have dedicated tests covering authorization, duplicate prevention, missing information, notification delivery, and safe failure behavior before being marked complete.
