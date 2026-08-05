# JobHunter AI V1 — Release Checklist

Use this checklist on the machine/environment that will actually run JobHunter AI. Do not put real resume data, tokens, passwords, chat IDs, or other secrets into GitHub.

## A. Automated gate

- [x] Full GitHub Actions / pytest suite passes on the release candidate.
- [ ] Confirm the latest release-candidate commit is the one being tested in production.

## B. Production configuration

1. Copy `.env.example` to a local `.env` file.
2. Set `JOBHUNTER_RESUME_PATH` to the real local resume.
3. Set a persistent `JOBHUNTER_DATABASE_PATH`.
4. Set `JOBHUNTER_RUN_HISTORY_PATH` and `JOBHUNTER_RUN_LOCK_PATH` to writable persistent locations.
5. Configure target titles, locations, work modes, desired keywords, and exclusions.
6. Configure Email or Telegram credentials only if alerts are required for the smoke test.

Validate that `.env`, the real resume, database, history, and credentials remain uncommitted.

## C. One-shot smoke test

Run against at least one real supported career/ATS source:

```bash
python main.py --env-file .env https://REAL-SUPPORTED-CAREER-URL
```

Pass criteria:

- [ ] Process starts without a configuration error.
- [ ] Resume is parsed successfully.
- [ ] Source is scraped without an unexpected run-level crash.
- [ ] Pipeline prints its completion summary.
- [ ] Jobs discovered above configured filters are persisted.
- [ ] Re-running does not create duplicate logical jobs.

A source legitimately returning zero matching jobs is not itself a failure; inspect the pipeline summary/errors and database state.

## D. Dashboard/database smoke test

Start the dashboard using the same persistent database configuration used by the runner.

Pass criteria:

- [ ] Dashboard health endpoint responds successfully.
- [ ] Stored jobs are visible.
- [ ] Recommendation score/explanation is visible for ranked jobs.
- [ ] Save/notes and application-status actions persist after refresh.
- [ ] Active/expired and relevant filters work.

## E. Scheduled runner smoke test

Start:

```bash
python main.py --scheduled --env-file .env https://REAL-SUPPORTED-CAREER-URL
```

Pass criteria:

- [ ] Runner performs an immediate scan.
- [ ] Run-history JSONL contains `runner_started`, `run_started`, and `run_completed` for a successful scan.
- [ ] Starting a second runner with the same lock path is rejected.
- [ ] Ctrl+C/SIGTERM stops the runner cleanly.
- [ ] Lock file is removed after clean shutdown.
- [ ] Run history records `runner_stopped`.

You do not need to wait the full production interval during release validation if the immediate scheduled-run behavior and scheduler registration are already covered by the green automated tests.

## F. Notification smoke test

Only perform this section when notifications are enabled.

Temporarily choose thresholds that allow one known matching test job to alert, without weakening the committed defaults.

Pass criteria:

- [ ] Alert arrives at the intended Telegram chat or email inbox.
- [ ] Alert contains the expected job/recommendation information.
- [ ] Re-running the same unchanged job does not send a duplicate alert.
- [ ] Restore intended production thresholds after the test.

## G. Release decision

V1 may be finalized only when all applicable checks above pass.

Record only non-sensitive evidence, for example:

```text
Release candidate commit: <sha>
CI: PASS
One-shot runner: PASS
Dashboard/database: PASS
Scheduled runner: PASS
Notification: PASS / NOT ENABLED
Validated on: YYYY-MM-DD
```

After validation, update `CHANGELOG.md` from `Unreleased` to the release date, mark Milestone 6 complete in `README.md`, run CI one final time, and then create/tag `v1.0.0`.
