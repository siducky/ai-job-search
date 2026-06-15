#!/usr/bin/env python3
"""
Export Job Scraper Results to Google Sheets
============================================
Takes JSON output from job_scraper/scraper.py and exports to a Google Sheet.

Prerequisites (one-time):
  1. gcloud auth application-default login
  2. Enable the Google Sheets API:
       gcloud services enable sheets.googleapis.com

Usage:
    # Pipe scraper output directly:
    python3 job_scraper/scraper.py --query "data engineer" --site all | python3 tools/export_to_sheets.py

    # Or from a JSON file:
    python3 tools/export_to_sheets.py --input results.json

    # Specify a custom sheet name:
    python3 tools/export_to_sheets.py --input results.json --title "AI Jobs June 2026"

    # Overwrite the existing sheet (instead of creating a new one each time):
    python3 tools/export_to_sheets.py --input results.json --sheet-id <sheet_id>

    # Use a service account key file instead of ADC:
    python3 tools/export_to_sheets.py --input results.json --key service_account.json
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime

# Optional: gspread
try:
    import gspread
    from gspread.exceptions import SpreadsheetNotFound, WorksheetNotFound
except ImportError:
    print("Error: gspread is required. Install: pip install gspread", file=sys.stderr)
    sys.exit(1)

# Optional: google-auth for ADC or service accounts
try:
    from google.oauth2 import service_account
    import google.auth
except ImportError:
    print(
        "Error: google-auth is required. Install: pip install google-auth",
        file=sys.stderr,
    )
    sys.exit(1)


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SHEET_COLUMNS = [
    "Title",
    "Company",
    "Location",
    "Date Posted",
    "URL",
    "Source",
    "Fit",
    "Status",
    "First Seen",
    "Notes",
]

# Maximum column widths (characters)
COLUMN_WIDTH_HINTS = {
    "Title": 60,
    "Company": 35,
    "Location": 25,
    "Date Posted": 14,
    "URL": 40,
    "Source": 22,
    "Fit": 12,
    "Status": 12,
    "First Seen": 14,
    "Notes": 40,
}


def authorize_gspread(key_path: str = None):
    """Authorize gspread using ADC or a service account key file."""
    if key_path:
        creds = service_account.Credentials.from_service_account_file(
            key_path, scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        return gspread.authorize(creds)
    else:
        # Use Application Default Credentials
        return gspread.service_account()  # Falls back to ADC


def load_jobs_from_stdin():
    """Read JSON from stdin."""
    raw = sys.stdin.read()
    if not raw.strip():
        print(
            "Error: No input received. Pipe scraper output or use --input.",
            file=sys.stderr,
        )
        sys.exit(1)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)
    return data


def load_jobs_from_file(path: str):
    """Read JSON from a file."""
    if not os.path.exists(path):
        print(f"Error: File not found: {path}", file=sys.stderr)
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in {path}: {e}", file=sys.stderr)
            sys.exit(1)
    return data


def flatten_jobs(data: dict) -> list[list]:
    """Convert the scraper JSON into a flat list of rows (header + data)."""
    rows = [SHEET_COLUMNS]

    # Get jobs from either jobs_list or the seen dict
    jobs_list = data.get("jobs_list", [])
    seen = data.get("seen", {})

    # Merge both sources, preferring jobs_list order
    processed_urls = set()

    for job in jobs_list:
        url = job.get("url", "")
        processed_urls.add(url)
        seen_entry = seen.get(url, {})

        row = [
            job.get("title", ""),
            job.get("company", ""),
            job.get("location", ""),
            job.get("date", ""),
            url,
            job.get("source", seen_entry.get("source", "unknown")),
            seen_entry.get("fit", "unknown"),
            seen_entry.get("status", "new"),
            seen_entry.get("first_seen", job.get("date", "")),
            "",  # Notes (always empty for new exports)
        ]
        rows.append(row)

    # Add any jobs from 'seen' that weren't in jobs_list
    for url, entry in seen.items():
        if url not in processed_urls:
            row = [
                entry.get("title", ""),
                entry.get("company", ""),
                entry.get("location", ""),
                entry.get("first_seen", ""),
                url,
                entry.get("source", "unknown"),
                entry.get("fit", "unknown"),
                entry.get("status", "new"),
                entry.get("first_seen", ""),
                "",  # Notes
            ]
            rows.append(row)

    return rows


def create_or_get_sheet(gc, title: str, sheet_id: str = None):
    """Create a new sheet or open an existing one by ID."""
    if sheet_id:
        try:
            sh = gc.open_by_key(sheet_id)
            print(f"Opened existing sheet: {sh.title} ({sheet_id})", file=sys.stderr)
            return sh
        except SpreadsheetNotFound:
            print(f"Error: Sheet with ID '{sheet_id}' not found.", file=sys.stderr)
            sys.exit(1)

    # Create a new sheet with a unique name
    base_title = title or "Job Search Results"
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    sheet_title = f"{base_title} ({timestamp})"

    try:
        sh = gc.create(sheet_title)
        print(f"Created new sheet: {sheet_title}", file=sys.stderr)
        # Share with the owner (the authenticated account already has access)
        return sh
    except Exception as e:
        print(f"Error creating sheet: {e}", file=sys.stderr)
        sys.exit(1)


def update_sheet(sh, rows: list[list]):
    """Write data to the first worksheet."""
    try:
        # Get or create the first worksheet
        try:
            worksheet = sh.get_worksheet(0)
            if worksheet:
                # Clear existing content
                worksheet.clear()
        except Exception:
            pass

        # If no worksheet exists, add one
        if not worksheet:
            worksheet = sh.add_worksheet(
                title="Jobs", rows=len(rows), cols=len(SHEET_COLUMNS)
            )

        # Update the entire range at once
        cell_range = f"A1:{chr(64 + len(SHEET_COLUMNS))}{len(rows)}"
        worksheet.update(cell_range, rows, value_input_option="USER_ENTERED")

        # Format the header row
        worksheet.format(
            "A1:J1",
            {
                "backgroundColor": {"red": 0.2, "green": 0.2, "blue": 0.2},
                "textFormat": {
                    "foregroundColor": {"red": 1, "green": 1, "blue": 1},
                    "bold": True,
                },
            },
        )

        # Auto-resize columns based on content
        for i, col_name in enumerate(SHEET_COLUMNS):
            col_letter = chr(65 + i)  # A, B, C, ...
            hint = COLUMN_WIDTH_HINTS.get(col_name, 20)
            worksheet.format(
                f"{col_letter}:{col_letter}",
                {
                    "textFormat": {"fontSize": 10},
                },
            )
            # Set column width via Google Sheets API
            try:
                sh.batch_update(
                    {
                        "requests": [
                            {
                                "updateDimensionProperties": {
                                    "range": {
                                        "sheetId": worksheet.id,
                                        "dimension": "COLUMNS",
                                        "startIndex": i,
                                        "endIndex": i + 1,
                                    },
                                    "properties": {"pixelSize": min(hint * 8, 500)},
                                    "fields": "pixelSize",
                                }
                            }
                        ]
                    }
                )
            except Exception:
                pass  # Column sizing is optional

        # URL column should be hyperlinked
        url_col_idx = SHEET_COLUMNS.index("URL")
        url_col_letter = chr(65 + url_col_idx)
        for row_num in range(2, len(rows) + 1):
            url_value = rows[row_num - 1][url_col_idx]
            if url_value:
                try:
                    worksheet.format(
                        f"{url_col_letter}{row_num}",
                        {
                            "textFormat": {
                                "foregroundColor": {
                                    "red": 0.1,
                                    "green": 0.3,
                                    "blue": 0.9,
                                },
                                "underline": True,
                            },
                            "hyperlinkDisplayType": "LINKED",
                        },
                    )
                except Exception:
                    pass

        # Freeze header row
        worksheet.freeze(rows=1)

        print(f"Written {len(rows) - 1} jobs to sheet", file=sys.stderr)
        print(
            f"Sheet URL: https://docs.google.com/spreadsheets/d/{sh.id}",
            file=sys.stderr,
        )

        return sh

    except Exception as e:
        print(f"Error updating sheet: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Export job scraper results to Google Sheets"
    )
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        default=None,
        help="Input JSON file (from scraper output). If omitted, reads from stdin.",
    )
    parser.add_argument(
        "--title",
        "-t",
        type=str,
        default="Job Search Results",
        help="Title for the Google Sheet (timestamp is appended). Default: 'Job Search Results'",
    )
    parser.add_argument(
        "--sheet-id",
        type=str,
        default=None,
        help="Existing Google Sheet ID to overwrite. If omitted, creates a new sheet.",
    )
    parser.add_argument(
        "--key",
        type=str,
        default=None,
        help="Path to a Google service account JSON key file. If omitted, uses Application Default Credentials.",
    )

    args = parser.parse_args()

    # Load jobs data
    if args.input:
        data = load_jobs_from_file(args.input)
    else:
        data = load_jobs_from_stdin()

    # Flatten into rows
    rows = flatten_jobs(data)
    if len(rows) <= 1:
        print("No jobs to export.", file=sys.stderr)
        return

    print(f"Loaded {len(rows) - 1} jobs for export", file=sys.stderr)

    # Authorize and create/open sheet
    gc = authorize_gspread(args.key)
    sh = create_or_get_sheet(gc, args.title, args.sheet_id)

    # Write data
    update_sheet(sh, rows)


if __name__ == "__main__":
    main()
