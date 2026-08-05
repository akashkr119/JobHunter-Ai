# JobHunter AI

JobHunter AI is an automated job discovery, matching, ranking, tracking, and alerting system. It monitors configured company career sources, compares jobs with resume skills and target-job preferences, ranks opportunities, stores job history, and sends smart alerts for the most relevant openings.

## V1 goal

V1 (`v1.0.0`) is focused on building a reliable end-to-end job monitoring system before expanding the project to broader job-platform discovery in later versions.

The V1 roadmap is frozen to six milestones:

| Milestone | Scope | Status |
| --- | --- | --- |
| 1 | Application Follow-up System | ✅ Complete |
| 2 | Job Preferences / Target Profile | ✅ Complete |
| 3 | Recommendation Ranking Engine | ✅ Complete |
| 4 | Dashboard Finalization | ⏳ Next |
| 5 | Automated Production Runner | ⏳ Planned |
| 6 | V1 Hardening & Release | ⏳ Planned |

## Current V1 capabilities

### Job discovery

- Discover company career pages and ATS links.
- Supported scraper routing includes Greenhouse, Lever, Workday, and SmartRecruiters.
- Continue processing other sources when one source fails.
- Detect jobs that disappear from a successfully scraped source and mark them inactive.
- Reactivate jobs when they appear again.
- Deduplicate jobs while preserving application tracking data.

### Resume and skill matching

- Parse TXT, Markdown, DOCX, and PDF resumes.
- Extract technical and automotive-related skills.
- Match resume skills against job descriptions.
- Distinguish required and preferred skills.
- Give missing required skills a stronger penalty.
- Persist match explanations including matched and missing skills.

### Application tracking and follow-up

- Track application states such as new, viewed, applied, interview, offer, and rejected.
- Save jobs and personal notes.
- Automatically schedule follow-up after applying.
- Detect overdue follow-ups.
- Configure or complete follow-ups through the dashboard API.
- Preserve tracking state when jobs are scraped again.

### Target job preferences

Jobs can be evaluated against a target profile containing:

- Target job titles
- Preferred locations
- Remote, hybrid, or onsite work mode
- Desired keywords
- Excluded keywords

The system stores `preference_score`, `preference_match`, and a detailed explanation of the preference evaluation. Jobs containing excluded keywords can be filtered from the saved recommendation pipeline while still being counted as seen for job-lifecycle handling.

### Unified recommendation ranking

V1 combines the major relevance signals into one recommendation score:

| Signal | Weight |
| --- | ---: |
| Resume / skill match | 50% |
| Target preference match | 25% |
| Job freshness | 10% |
| Application state | 10% |
| Active lifecycle state | 5% |

Every dashboard job can expose:

- `recommendation_score` — 0 to 100
- `recommendation_label` — `top_pick`, `strong_match`, `good_match`, or `consider`
- `recommendation_breakdown` — raw values, weights, and weighted contribution

Jobs are ranked by the unified recommendation score rather than resume match alone. A failed target-preference match is prevented from becoming a high recommendation.

### Smart alerts

- Email and Telegram notification support.
- Priority-based alert thresholds remain supported.
- Optional `minimum_recommendation_score` from 0–100.
- Duplicate smart alerts are suppressed unless the opportunity meaningfully escalates.
- Applied jobs are prevented from repeatedly generating new-job alerts.
- Notification messages include recommendation score and recommendation label.

### Dashboard and API

The Flask dashboard currently provides:

- Search and filtering
- Match and priority information
- Saved jobs and notes
- Application status tracking
- Active/expired job lifecycle state
- Follow-up status and overdue follow-ups
- Analytics
- Job detail descriptions
- Preference results
- Unified recommendation score, label, and score breakdown

Milestone 4 will finalize the V1 dashboard experience around these capabilities.

## Project structure

```text
JobHunter-Ai/
├── config/          # Runtime configuration
├── crawler/         # Career discovery and ATS/job scrapers
├── dashboard/       # Flask dashboard and API
├── database/        # SQLite persistence and migrations
├── matcher/         # Skill, preference, priority and recommendation logic
├── notifier/        # Email and Telegram notifications
├── scheduler/       # Pipeline orchestration and scheduled execution
├── tests/           # Automated test suite
├── app.py
├── requirements.txt
└── pytest.ini
```

## Quality status

Milestones 1–3 are implemented and CI-green. The current automated suite contains **209 passing tests** covering discovery, scraping, resume parsing, matching, preferences, persistence, lifecycle management, follow-ups, recommendation ranking, dashboard/API behavior, scheduling, and smart notifications.

## V1 remaining work

### Milestone 4 — Dashboard Finalization

Finalize the dashboard presentation and interaction layer for the functionality already implemented in Milestones 1–3.

### Milestone 5 — Automated Production Runner

Make the completed pipeline practical for unattended recurring execution with production-oriented runtime behavior.

### Milestone 6 — V1 Hardening & Release

Complete final regression testing, reliability cleanup, documentation/configuration validation, and release preparation for `v1.0.0`.

## Future direction — V3

V3 is planned around a much simpler user experience: **upload a resume and let JobHunter AI automatically determine relevant skills/job titles and generate job alerts across broader job platforms**. The intended direction includes sources such as LinkedIn, Indeed, Naukri.com, Glassdoor, and additional job platforms, while retaining the matching, ranking, tracking, and smart-alert concepts developed in V1.

Platform access methods and integrations for V3 will be designed separately; they are intentionally outside the frozen V1 scope.

## Development

Run the automated tests with:

```bash
pytest
```

The project should remain CI-green as each V1 milestone is completed.
