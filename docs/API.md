# JobHunter-AI API

## Base URL
`/api/v1`

## Planned Endpoints

### Health
- GET /health

### Companies
- GET /companies
- POST /companies

### Jobs
- GET /jobs
- GET /jobs/{id}
- POST /jobs/scrape

### Resume
- POST /resume/upload
- POST /resume/match

### Scheduler
- POST /scheduler/start
- POST /scheduler/stop
- GET /scheduler/status

### Notifications
- POST /notifications/test

### Dashboard
- GET /dashboard/stats
- GET /dashboard/recent-jobs

## Response Format
All endpoints return JSON with status, message, and data fields.
