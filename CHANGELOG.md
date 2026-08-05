# Changelog

All notable changes to JobHunter AI are documented here.

## [1.0.0] - Unreleased

### Added

- Automated company career-page discovery and ATS routing.
- Greenhouse, Lever, Workday, and SmartRecruiters job ingestion.
- Resume parsing for text, Markdown, DOCX, and PDF resumes.
- Weighted skill matching with required/preferred skill explanations.
- Target job preferences for titles, locations, work modes, desired keywords, and exclusions.
- Unified recommendation ranking using resume fit, preferences, freshness, application state, and lifecycle state.
- SQLite job lifecycle tracking, cross-source deduplication, active/expired state, saved jobs, and notes.
- Application status tracking and follow-up scheduling.
- Responsive Flask dashboard with filters, recommendation explanations, analytics, and tracking actions.
- Smart Email and Telegram alerts with priority/recommendation thresholds and duplicate suppression.
- Production runner with immediate scan, recurring scheduling, single-instance locking, JSONL run history, graceful shutdown, and cleanup.
- Centralized environment configuration and safe `.env.example` template.
- Startup validation for resume availability, source URLs, notification configuration, and runtime directories.
- Automated release-readiness regression checks.

### Release gate

Tag `v1.0.0` only after the full CI suite passes on the final release commit and the production smoke checklist in `docs/PRODUCTION.md` is completed with the intended resume, sources, database, and notification destination.

### Future

V3 is intentionally outside V1 scope. Its planned direction is resume-first automatic job discovery across broader platforms such as LinkedIn, Indeed, Naukri.com, Glassdoor, and additional sources, subject to each platform's supported access/integration model.
