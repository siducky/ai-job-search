#!/usr/bin/env python3
"""
Export Job Scraper Results to Google Sheets
============================================
Takes JSON output from job_scraper/scraper.py and exports to a Google Sheet.

Prerequisites (one-time):
  1. Enable the Google Sheets API:
       gcloud services enable sheets.googleapis.com
  2. Create an OAuth 2.0 Client ID in Google Cloud Console
     (Desktop app type), download the JSON, and save it as
     gcloud_client_secret.json in the repo root.

The script will auto-detect gcloud_client_secret.json and open a
browser to authenticate with the correct scopes on first run.

Usage:
    # Pipe scraper output directly:
    python3 job_scraper/scraper.py --query "data engineer" --site all | python3 tools/export_to_sheets.py

    # Or from a JSON file:
    python3 tools/export_to_sheets.py --input results.json

    # Overwrite (clear + rewrite) instead of merging:
    python3 tools/export_to_sheets.py --input results.json --overwrite

    # Use a specific sheet ID (overrides auto-detection):
    python3 tools/export_to_sheets.py --input results.json --sheet-id <sheet_id>

    # Use a service account key file instead of OAuth/ADC:
    python3 tools/export_to_sheets.py --input results.json --key service_account.json

The script remembers which sheet it last used (in .last_sheet_id) and will
merge new listings into it on subsequent runs, preserving manual edits to
the Fit, Status, First Seen, and Notes columns.
"""

import argparse
import json
import os
import sys
from datetime import datetime

# Optional: gspread
try:
    import gspread
    from gspread.exceptions import SpreadsheetNotFound
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
TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
LAST_SHEET_ID_FILE = os.path.join(TOOLS_DIR, ".last_sheet_id")


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


def _find_client_secret() -> str | None:
    """Look for a gcloud OAuth client secret in common locations."""
    candidates = [os.path.join(REPO_ROOT, "gcloud_client_secret.json")]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def _load_last_sheet_id() -> str | None:
    """Read the last-used sheet ID from the dotfile."""
    try:
        with open(LAST_SHEET_ID_FILE, encoding="utf-8") as f:
            sid = f.read().strip()
            return sid if sid else None
    except (FileNotFoundError, PermissionError):
        return None


def _save_last_sheet_id(sheet_id: str):
    """Write the sheet ID to the dotfile so next run remembers it."""
    try:
        with open(LAST_SHEET_ID_FILE, "w", encoding="utf-8") as f:
            f.write(sheet_id)
    except (PermissionError, OSError) as e:
        print(
            f"Warning: Could not save sheet ID to {LAST_SHEET_ID_FILE}: {e}",
            file=sys.stderr,
        )


def authorize_gspread(key_path: str = None):
    """Authorize gspread using a service account key, or OAuth client secret."""
    if key_path:
        creds = service_account.Credentials.from_service_account_file(
            key_path, scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        return gspread.authorize(creds)

    secret = _find_client_secret()
    if secret:
        try:
            gc = gspread.oauth(
                credentials_filename=secret,
                authorized_user_filename=os.path.join(
                    os.path.dirname(secret), "authorized_user.json"
                ),
            )
            return gc
        except Exception as e:
            print(f"OAuth flow failed: {e}", file=sys.stderr)
            print(
                "Try deleting authorized_user.json and re-running,"
                " or use --key with a service account.",
                file=sys.stderr,
            )
            sys.exit(1)

    try:
        creds, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
    except Exception as e:
        print(
            f"Error: Unable to obtain Application Default Credentials: {e}",
            file=sys.stderr,
        )
        sys.exit(1)

    return gspread.authorize(creds)


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

    jobs_list = data.get("jobs_list", [])
    seen = data.get("seen", {})

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
            "",
        ]
        rows.append(row)

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
                "",
            ]
            rows.append(row)

    return rows


def _check_auth_scope_error(e: Exception):
    """Check if the error is a 403 scope error and print actionable guidance."""
    msg = str(e)
    if "403" in msg and "insufficient authentication scopes" in msg.lower():
        print(
            "The authenticated credentials don't have the Google Sheets API scope.",
            file=sys.stderr,
        )
        print(file=sys.stderr)
        print("Fix options:", file=sys.stderr)
        print(
            "  1. Re-authenticate with the correct scope:",
            file=sys.stderr,
        )
        print(
            "       gcloud auth application-default login"
            " --scopes=https://www.googleapis.com/auth/spreadsheets",
            file=sys.stderr,
        )
        print(
            "  2. Or use a service account key file:",
            file=sys.stderr,
        )
        print(
            "       python3 tools/export_to_sheets.py --input results.json --key service_account.json",
            file=sys.stderr,
        )
        print(
            "  3. Or if using ADC with a service account, ensure it has"
            " the https://www.googleapis.com/auth/spreadsheets scope enabled.",
            file=sys.stderr,
        )
        return True
    return False


def read_existing_rows(worksheet) -> dict[str, list[str]]:
    """Read existing sheet rows keyed by URL (column E, index 4).

    Returns a dict: URL -> row list (excluding header). Returns empty dict
    if the sheet is empty or has only a header.
    """
    try:
        all_rows = worksheet.get_all_values()
    except Exception:
        return {}

    if len(all_rows) <= 1:
        return {}

    header = all_rows[0]
    if header != SHEET_COLUMNS:
        print(
            "Existing sheet has a different header — treating as empty for merge.",
            file=sys.stderr,
        )
        return {}

    existing: dict[str, list[str]] = {}
    for row in all_rows[1:]:
        if len(row) < len(SHEET_COLUMNS):
            row = row + [""] * (len(SHEET_COLUMNS) - len(row))
        url = row[4].strip()
        if url:
            existing[url] = row
    return existing


def merge_rows(new_rows: list[list], existing_rows: dict[str, list[str]]) -> list[list]:
    """Merge new scraper rows into existing sheet rows.

    For URLs already in the sheet: keep user-edited columns (Fit, Status,
    First Seen, Notes) at indices 6-9, update scraper columns (0-5) from
    new data. For new URLs: add as-is.
    """
    USER_COLS = {6, 7, 8, 9}  # Fit, Status, First Seen, Notes

    merged = [SHEET_COLUMNS]
    seen_in_new: set[str] = set()

    for row in new_rows[1:]:
        if len(row) < len(SHEET_COLUMNS):
            row = row + [""] * (len(SHEET_COLUMNS) - len(row))
        url = row[4].strip()
        seen_in_new.add(url)

        if url in existing_rows:
            existing = existing_rows[url][:]
            for i in range(len(SHEET_COLUMNS)):
                if i not in USER_COLS:
                    existing[i] = row[i] if row[i] else existing[i]
            merged.append(existing)
        else:
            merged.append(row)

    for url, existing_row in existing_rows.items():
        if url not in seen_in_new:
            merged.append(existing_row)

    return merged


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

    base_title = title or "Job Search Results"
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    sheet_title = f"{base_title} ({timestamp})"

    try:
        sh = gc.create(sheet_title)
        print(f"Created new sheet: {sheet_title}", file=sys.stderr)
        _save_last_sheet_id(sh.id)
        return sh
    except Exception as e:
        _check_auth_scope_error(e)
        print(f"Error creating sheet: {e}", file=sys.stderr)
        sys.exit(1)


def update_sheet(sh, rows: list[list], merge_existing: bool = False):
    """Write data to the first worksheet.

    If merge_existing is True, existing rows are read from the sheet and
    merged with new data: user-edited columns (Fit, Status, First Seen,
    Notes) are preserved, scraper columns are updated, and new listings
    are appended.
    """
    try:
        worksheet = None
        try:
            worksheet = sh.get_worksheet(0)
        except Exception:
            pass

        if not worksheet:
            worksheet = sh.add_worksheet(
                title="Jobs", rows=len(rows), cols=len(SHEET_COLUMNS)
            )
            merge_existing = False

        if merge_existing:
            existing_rows = read_existing_rows(worksheet)
            # ponytail: merge, not replace; preserves manual Status/Fit/Notes edits
            rows = merge_rows(rows, existing_rows)
            print(
                f"Merged with existing sheet ({len(existing_rows)} existing rows)",
                file=sys.stderr,
            )
        else:
            worksheet.clear()

        cell_range = f"A1:{chr(64 + len(SHEET_COLUMNS))}{len(rows)}"
        worksheet.update(rows, cell_range, value_input_option="USER_ENTERED")

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

        for i, col_name in enumerate(SHEET_COLUMNS):
            col_letter = chr(65 + i)
            hint = COLUMN_WIDTH_HINTS.get(col_name, 20)
            worksheet.format(
                f"{col_letter}:{col_letter}",
                {"textFormat": {"fontSize": 10}},
            )
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
                pass

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

        worksheet.freeze(rows=1)

        # ponytail: writes all rows each time (even on merge), which is O(n) — fine for <<10k rows
        print(f"Written {len(rows) - 1} jobs to sheet", file=sys.stderr)
        print(f"Sheet ID: {sh.id}", file=sys.stderr)
        print(
            f"Sheet URL: https://docs.google.com/spreadsheets/d/{sh.id}",
            file=sys.stderr,
        )

        return sh

    except Exception as e:
        _check_auth_scope_error(e)
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
        help="Sheet ID to use instead of auto-detecting from last run.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        default=False,
        help="Clear the sheet and rewrite from scratch instead of merging.",
    )
    parser.add_argument(
        "--key",
        type=str,
        default=None,
        help="Path to a Google service account JSON key file. If omitted, uses Application Default Credentials.",
    )

    args = parser.parse_args()

    if args.input:
        data = load_jobs_from_file(args.input)
    else:
        data = load_jobs_from_stdin()

    rows = flatten_jobs(data)
    if len(rows) <= 1:
        print("No jobs to export.", file=sys.stderr)
        return

    print(f"Loaded {len(rows) - 1} jobs for export", file=sys.stderr)

    gc = authorize_gspread(args.key)

    # Determine which sheet to use
    sheet_id = args.sheet_id
    if not sheet_id:
        sheet_id = _load_last_sheet_id()

    sh = create_or_get_sheet(gc, args.title, sheet_id)
    _save_last_sheet_id(sh.id)

    merge_existing = not args.overwrite
    update_sheet(sh, rows, merge_existing=merge_existing)


if __name__ == "__main__":
    main()
