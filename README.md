# JobHunter AI

JobHunter AI is an automated job discovery, matching, ranking, tracking, and alerting system. It parses a resume, applies target-job preferences, discovers jobs from supported sources, compares opportunities with the candidate profile, ranks the best matches, stores job history, and sends smart alerts for relevant openings.

## Product direction

The project is moving away from an **Excel-first company discovery workflow**. Excel is no longer intended to be a required input to the core application.

The core JobHunter workflow is:

```text
Resume + Job Preferences
          ↓
   Job Source Manager
          ↓
 ┌──────────────────────────────┐
 │ Authorized / supported       │
 │ job platforms and sources    │
 │                              │
 │ • Job APIs / feeds           │
 │ • Company career pages       │
 │ • Supported ATS platforms    │
 │ • Additional integrations    │
 └──────────────┬───────────────┘
                ↓
       Normalize job listings
                ↓
        Deduplicate jobs
                ↓
      Resume + preference match
                ↓
      Recommendation ranking
                ↓
       Dashboard + alerts
```

The goal is to discover relevant jobs automatically instead of requiring the user to prepare and maintain a company spreadsheet.

## Multi-source job discovery

The next major development milestone is a **Multi-Source Job Discovery Engine**. It will introduce a common `JobSource` abstraction and a source manager so different job providers can feed the same matching and recommendation pipeline.

Planned source categories include:

- Job-search APIs and public feeds
- Company career pages
- Greenhouse
- Lever
- Workday
- SmartRecruiters
- Other supported ATS platforms
- Authorized integrations for major job platforms
- Search-page actions for platforms where direct automated access is not available

Target platforms include services such as **LinkedIn, Indeed, Naukri.com, Foundit, Glassdoor, Wellfound, Internshala, Shine, Cutshort, and other relevant job sources**, subject to each platform's available APIs, feeds, integrations, and access terms.

JobHunter AI will not make unauthorized scraping a requirement for these platforms. Each source will use an appropriate supported access method, while the normalized job model keeps the rest of the application source-independent.

## Core workflow

The intended user experience is:

1. Provide a resume.
2. Configure or confirm target job preferences.
3. Start JobHunter AI without requiring an Excel company list.
4. Discover jobs across configured and supported sources.
5. Normalize and deduplicate listings from different sources.
6. Parse the resume and match jobs against its skills.
7. Apply target titles, locations, work modes, desired/excluded keywords, and minimum match score.
8. Rank opportunities using the recommendation engine.
9. Save matching jobs and their source/application URLs.
10. Track applications, saved jobs, notes, and follow-ups from the dashboard.
11. Send Email/Telegram alerts when notification settings are configured.

Excel import/export may remain as an **optional utility** for users who want to supply or export company/job data, but it is not part of the required production workflow.

## Automated production runner

The production runner performs an immediate scan, schedules recurring scans, prevents duplicate runner instances with a lock, records JSONL run history, handles run failures, and cleans up on SIGINT/SIGTERM.

For notifications, configure either Email or Telegram. The minimum alert priority and recommendation score can also be configured.

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
| 7 | Multi-Source Job Discovery | 📋 Planned |

## V1 capabilities

JobHunter AI currently provides company career-page and ATS discovery, Greenhouse/Lever/Workday/SmartRecruiters scraping, resume parsing, weighted skill matching, job preferences, unified recommendation ranking, lifecycle detection, cross-source deduplication, application tracking, saved jobs and notes, follow-up reminders, dashboard analytics, and smart Email/Telegram alerts.

Recommendation ranking combines resume fit, target preferences, freshness, application state, and active lifecycle state. The dashboard exposes recommendation scores and explanations and supports search/filtering, saved jobs, tracking, follow-ups, active/expired jobs, analytics, and mobile-friendly interaction.

See `docs/PRODUCTION.md` for configuration, operations, notifications, and the release validation checklist. See `CHANGELOG.md` for the prepared `1.0.0` release notes.

## Project structure

```text
JobHunter-Ai/
├── config/          # Runtime configuration
├── crawler/         # Career discovery and ATS/job scrapers
├── dashboard/       # Flask dashboard and API
├── database/        # SQLite persistence and migrations
├── matcher/         # Skill, preference, priority and recommendation logic
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

All six V1 implementation milestones are built. The remaining release gate is final green CI plus the production smoke checklist. After both pass, the repository can be tagged `v1.0.0`.

The multi-source discovery engine is intentionally planned as the next major development phase rather than being represented as completed V1 functionality.
