# JobHunter AI — Production Runner

This guide covers unattended V1 execution using the production runner introduced in Milestone 5.

## 1. Install and validate

Create a Python 3.11 environment, install `requirements.txt`, then run:

```bash
pytest
```

Do not deploy a revision whose test suite is failing.

## 2. Required inputs

The runner needs:

- a resume configured with `JOBHUNTER_RESUME_PATH`
- at least one career URL on the command line, or a company workbook supplied with `--companies`
- a writable SQLite database location

Example:

```bash
python main.py --scheduled --companies companies.xlsx
```

You can also supply career sources directly:

```bash
python main.py --scheduled https://boards.greenhouse.io/example https://jobs.lever.co/example
```

## 3. Production environment variables

```dotenv
JOBHUNTER_DATABASE_PATH=database/jobs.db
JOBHUNTER_RESUME_PATH=resume.pdf
JOBHUNTER_MIN_MATCH_SCORE=60
JOBHUNTER_SCHEDULER_HOURS=6
JOBHUNTER_LOG_LEVEL=INFO
JOBHUNTER_RUN_HISTORY_PATH=logs/run_history.jsonl
JOBHUNTER_RUN_LOCK_PATH=database/jobhunter.lock

JOBHUNTER_TARGET_TITLES=QA Automation Engineer,SDET
JOBHUNTER_PREFERRED_LOCATIONS=Bengaluru,Remote
JOBHUNTER_WORK_MODES=remote,hybrid
JOBHUNTER_DESIRED_KEYWORDS=python,selenium,pytest
JOBHUNTER_EXCLUDED_KEYWORDS=intern

JOBHUNTER_NOTIFICATION_CHANNEL=telegram
JOBHUNTER_NOTIFICATION_MIN_PRIORITY=high
JOBHUNTER_NOTIFICATION_MIN_RECOMMENDATION_SCORE=75
JOBHUNTER_TELEGRAM_BOT_TOKEN=replace-with-secret
JOBHUNTER_TELEGRAM_CHAT_ID=replace-with-chat-id
```

Never commit real notification credentials or private resume data to the repository.

For email alerts, configure `JOBHUNTER_SMTP_HOST`, `JOBHUNTER_SMTP_PORT`, `JOBHUNTER_SMTP_USERNAME`, `JOBHUNTER_SMTP_PASSWORD`, `JOBHUNTER_SMTP_SENDER`, and `JOBHUNTER_EMAIL_RECIPIENT` and set the notification channel to `email`.

## 4. Runtime behavior

`--scheduled` starts the production lifecycle wrapper. It:

1. acquires a single-instance lock
2. records `runner_started`
3. performs an immediate scan
4. records success or failure in JSONL history
5. schedules future scans using `JOBHUNTER_SCHEDULER_HOURS`
6. responds to SIGINT/SIGTERM
7. closes the database and removes the lock during normal cleanup

A second runner using the same lock path is rejected to avoid duplicate scans and alerts.

## 5. Run history

Each line in `JOBHUNTER_RUN_HISTORY_PATH` is a JSON object. Important events are:

- `runner_started`
- `run_started`
- `run_completed`
- `run_failed`
- `runner_stopped`

Successful runs include the pipeline summary and duration. Failed runs include the exception message and duration.

## 6. Operations

Keep the process supervised by the host operating system or container platform. The supervisor should restart the process after an unexpected process-level failure. JobHunter itself isolates individual source failures inside the pipeline, while the production runner records run-level failures.

Persist the SQLite database and run-history file across restarts. Keep the lock file on the same host/runtime instance as the process.

For planned shutdown, send SIGTERM or use Ctrl+C. The runner requests scheduler shutdown and performs cleanup.

## 7. Pre-release production validation

Before V1 release, verify:

- the full pytest suite is green
- resume parsing succeeds with the intended production resume
- configured company/career sources resolve correctly
- one manual run completes successfully
- one scheduled startup performs its immediate scan
- run history contains the expected events
- a second simultaneous runner is rejected
- notification credentials are supplied through environment variables only
- a real test alert reaches the intended email/Telegram destination when notifications are enabled
- the dashboard reads the same persistent database used by the runner

Milestone 6 performs the final V1 hardening and release validation before tagging `v1.0.0`.
