# JobHunter AI

JobHunter AI is an automated job discovery, matching, ranking, tracking, and alerting system. It monitors configured company career sources, compares jobs with resume skills and target-job preferences, ranks opportunities, stores job history, and sends smart alerts for the most relevant openings.

## Company-name-only Excel workflow

The intended user workflow is now deliberately simple: **the Excel file only needs a list of company names**.

Example:

| S.No. | Company Name |
| ---: | --- |
| 1 | Tata Consultancy Services (TCS) |
| 2 | Infosys |
| 3 | Wipro |

Run:

```bash
python main.py --companies companies.xlsx
```

JobHunter AI will:

1. Read the company names.
2. Automatically search for each company's public career/jobs page or supported ATS page.
3. Write the discovered `Website`, `Career URL`, `Discovery Status`, and `Last Checked` columns back into **the same Excel file**.
4. Reuse the saved Career URL on future runs instead of searching again.
5. Scrape jobs from those company sources.
6. Parse the configured resume and match jobs against its skills.
7. Apply the user's target titles, locations, work modes, desired/excluded keywords, and minimum match score.
8. Save matching jobs and send Email/Telegram alerts when notification settings are configured.

A company with no discoverable career source is retained in the workbook with a `Not found` or `Low confidence` status instead of silently disappearing.

The discovery step is bounded and concurrent so one slow company does not block all other companies.

## Automated production runner

After the first successful discovery, the same workbook can be monitored continuously:

```bash
python main.py --scheduled --companies companies.xlsx
```

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

## V1 capabilities

JobHunter AI provides company career-page and ATS discovery, Greenhouse/Lever/Workday/SmartRecruiters scraping, resume parsing, weighted skill matching, job preferences, unified recommendation ranking, lifecycle detection, cross-source deduplication, application tracking, saved jobs and notes, follow-up reminders, dashboard analytics, and smart Email/Telegram alerts.

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

## Future direction — V3

V3 is planned around a simpler experience: upload a resume, automatically infer relevant skills/job titles, and generate matching alerts across broader job platforms. The intended direction includes LinkedIn, Indeed, Naukri.com, Glassdoor, and additional sources while retaining V1's matching, ranking, tracking, and smart-alert concepts.

Platform access methods and integrations for V3 will be designed separately and are intentionally outside the frozen V1 scope.
