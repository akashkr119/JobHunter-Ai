# JobHunter AI

JobHunter AI is an automated job discovery, matching, ranking, tracking, and alerting system. It monitors configured company career sources, compares jobs with resume skills and target-job preferences, ranks opportunities, stores job history, and sends smart alerts for the most relevant openings.

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

## Automated production runner

V1 can run unattended:

```bash
python main.py --scheduled --companies companies.xlsx
```

The production runner performs an immediate scan, schedules recurring scans, prevents duplicate runner instances with a lock, records JSONL run history, handles run failures, and cleans up on SIGINT/SIGTERM.

Important production settings include:

```text
JOBHUNTER_DATABASE_PATH
JOBHUNTER_RESUME_PATH
JOBHUNTER_MIN_MATCH_SCORE
JOBHUNTER_SCHEDULER_HOURS
JOBHUNTER_LOG_LEVEL
JOBHUNTER_RUN_HISTORY_PATH
JOBHUNTER_RUN_LOCK_PATH
JOBHUNTER_NOTIFICATION_MIN_PRIORITY
JOBHUNTER_NOTIFICATION_MIN_RECOMMENDATION_SCORE
```

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
