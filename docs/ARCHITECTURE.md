# JobHunter-AI Architecture

## Overview
JobHunter-AI automates job discovery, resume matching, and notifications.

## Data Flow
1. Load companies from Excel.
2. Find official websites.
3. Discover careers pages.
4. Detect ATS platform.
5. Scrape jobs.
6. Store jobs in SQLite.
7. Parse resume.
8. Match jobs to skills.
9. Send email/Telegram notifications.

## Core Modules
- Company Loader
- Website Finder
- Career Finder
- ATS Detector
- Job Scraper
- Database
- Resume Parser
- Skill Matcher
- Scheduler
- Notifier
- Dashboard

## Future Enhancements
- AI-based resume optimization
- Multi-database support
- Cloud deployment
- REST API
- Analytics dashboard
