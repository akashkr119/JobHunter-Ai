# JobHunter AI

JobHunter AI is an automated job discovery, matching, ranking, tracking, and alerting system. The target experience is resume-first: the user provides a resume and job preferences, JobHunter discovers relevant opportunities across supported job sources, compares each job with the resume, recommends the strongest matches, tracks applications, and sends smart alerts.

## Core workflow — no Excel required

Excel is **not required for the core workflow**. It may remain an optional import/export utility, but JobHunter's primary workflow is:

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
Auto-Apply / Apply Assistance
        ↓
Dashboard + Email / Telegram Alerts
```

The system should discover opportunities from multiple legitimate/authorized sources and integrations. Planned sources include LinkedIn, Indeed, Naukri.com, Foundit, Glassdoor, Wellfound, Internshala, Shine, Cutshort, Adzuna, and company career/ATS pages. Access methods must respect each platform's API, integration, feed, and automation terms; where direct automated access is not authorized, JobHunter should provide a search/apply link or supported integration instead of bypassing platform controls.

## Resume-first matching

JobHunter parses the user's resume and evaluates each discovered job against:

- Required and preferred skills
- Relevant experience
- Job title / role alignment
- Location and work mode
- User target-profile preferences
- Desired and excluded keywords
- Job freshness and lifecycle state

The existing recommendation engine combines these signals into a job recommendation score.

## Auto-apply threshold — planned feature

A core future capability is **automatic application for strong matches**.

- When a job's validated resume/skill match is **above 60%**, the job becomes eligible for automatic application.
- The system must still verify that the job passes the user's preference filters and safety/eligibility checks before applying.
- Auto-apply must use the user's configured resume and application information and must never fabricate qualifications, experience, answers, or documents.
- If an application requires information that JobHunter does not have or cannot safely determine, it should pause and request user input rather than guessing.
- Every automatic application must be recorded with the job URL, source, timestamp, resume version, match score, and application result.
- Duplicate applications must be prevented.

The 60% value is a **user-configurable threshold**, with 60% as the initial default target. The implementation must not automatically submit applications merely because a scraper reports a high score; application submission requires a supported and authorized application flow.

## Resume improvement / modification alerts — planned feature

Before applying, JobHunter should compare the job requirements with the current resume and determine whether the resume should be improved for that particular role.

When meaningful resume modifications could improve the application, JobHunter should:

1. Identify the missing or weak skills, keywords, experience evidence, or project details.
2. Explain exactly what should be improved.
3. Generate a resume-improvement recommendation without inventing experience.
4. Send an **Email and/or Telegram notification** telling the user that the resume needs modification.
5. Include the job title, company/source, match score, missing requirements, suggested changes, and application status.
6. Allow the user to approve/update the resume before an application is submitted when the modification is important.

Example notification:

```text
Resume Modification Required

Job: Senior QA Automation Engineer
Match: 67%
Source: Job Platform

Recommended resume changes:
• Highlight Selenium automation experience
• Add Python/pytest projects if they accurately reflect your experience
• Make API testing experience more visible
• Add relevant automotive testing keywords where truthful

Action: Update resume before applying
```

JobHunter must distinguish between **"resume improvement recommended"** and **"resume modification required"**. A strong match can still be auto-applied when no material modification is needed; otherwise the configured workflow should pause and notify the user.

## Multi-source job discovery

The discovery architecture is source-adapter based:

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
       Deduplication
             ↓
       Matching + Ranking
```

Each source should normalize its results into the same job model so LinkedIn, Indeed, Naukri.com, company ATS pages, and other sources can participate in the same ranking, tracking, notification, and application workflow.

## Automated production runner

The production runner performs scheduled scans, prevents duplicate runner instances with a lock, records run history, handles failures, and cleans up on shutdown.

For notifications, configure Email and/or Telegram. Notification thresholds can be configured independently from the auto-apply threshold.

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
| 7 | Multi-Source Job Discovery | 🚧 Planned |
| 8 | Resume Review & Modification Alerts | 🚧 Planned |
| 9 | Safe Auto-Apply Workflow | 🚧 Planned |

## Current capabilities

JobHunter AI provides career-page and ATS discovery, Greenhouse/Lever/Workday/SmartRecruiters scraping, resume parsing, weighted skill matching, job preferences, recommendation ranking, lifecycle detection, cross-source deduplication, application tracking, saved jobs and notes, follow-up reminders, dashboard analytics, and smart Email/Telegram alerts.

Auto-apply and resume-modification detection are planned capabilities and are **not claimed as implemented until their application-flow and safety tests pass**.

See `docs/PRODUCTION.md` for configuration, operations, notifications, and release validation. See `CHANGELOG.md` for release notes.

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

The release gate requires green CI plus the production smoke checklist. After both pass, the repository can be tagged `v1.0.0`.

New auto-apply and resume-review functionality must also have dedicated tests covering authorization, duplicate prevention, missing information, notification delivery, and safe failure behavior before being marked complete.
