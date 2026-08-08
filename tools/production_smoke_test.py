"""Read-only production smoke test for company career sources."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from crawler.career_finder import CareerFinder
from crawler.company_loader import CompanyLoader
from crawler.scraper_factory import ScraperFactory


def inspect_company(target, finder=None, factory=None):
    finder = finder or CareerFinder()
    factory = factory or ScraperFactory()
    company = target["company"]
    website = target.get("website")
    explicit = target.get("career_url")
    row = {
        "company": company,
        "website": website or "",
        "career_url": "",
        "platform": "",
        "scraper": "",
        "jobs_found": 0,
        "status": "failure",
        "error": "",
    }
    try:
        urls = [explicit] if explicit else (
            finder.find(website, discover=True) if website else []
        )
        if not urls:
            raise ValueError("No career URL available")
        last_error = ""
        for url in urls:
            try:
                platform = factory.detector.detect(url) or "unknown"
                scraper = factory.from_url(url)
                jobs = scraper.scrape(url, company=company)
                row.update(
                    career_url=url,
                    platform=platform,
                    scraper=type(scraper).__name__,
                    jobs_found=len(jobs),
                    status="success" if jobs else "zero_jobs",
                    error="",
                )
                if jobs:
                    return row
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"
        if row["career_url"]:
            row["error"] = last_error
        else:
            raise RuntimeError(last_error or "All career sources failed")
    except Exception as exc:
        row["error"] = f"{type(exc).__name__}: {exc}"
    return row


def run_smoke_test(excel_path, finder=None, factory=None, timeout=10):
    """Run the read-only source check with a diagnostic discovery timeout."""
    finder = finder or CareerFinder(timeout=timeout)
    targets = CompanyLoader().load_targets(excel_path)
    rows = []
    total = len(targets)
    for index, target in enumerate(targets, 1):
        print(f"[{index:02d}/{total:02d}] {target['company']} ...", flush=True)
        row = inspect_company(target, finder, factory)
        rows.append(row)
        print(
            f"[{index:02d}/{total:02d}] {target['company']}: "
            f"{row['status']} | {row['scraper'] or '-'} | "
            f"jobs={row['jobs_found']} | {row['career_url'] or row['error']}",
            flush=True,
        )
    return rows


def write_csv(rows, path):
    fields = [
        "company", "website", "career_url", "platform", "scraper",
        "jobs_found", "status", "error",
    ]
    with Path(path).open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(
        description="Read-only JobHunter production source smoke test"
    )
    parser.add_argument("excel", help="Company Excel workbook")
    parser.add_argument("--output", default="production-smoke-report.csv")
    parser.add_argument(
        "--timeout",
        type=float,
        default=10,
        help="HTTP timeout in seconds for career discovery (diagnostic only)",
    )
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be greater than zero")
    rows = run_smoke_test(args.excel, timeout=args.timeout)
    write_csv(rows, args.output)
    print(f"Report: {args.output}")


if __name__ == "__main__":
    main()
