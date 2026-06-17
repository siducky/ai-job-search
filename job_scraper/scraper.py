#!/usr/bin/env python3
"""
Multi-Site Job Scraper
======================
Scrapes job listings from Norwegian job portals using curl (stdlib, no Playwright).

Supported sites:
  - finn.no              : Server-rendered HTML (parsed with regex)
  - arbeidsplassen.nav.no: Next.js SPA (links in HTML, fetch detail pages)
  - jobbnorge.no         : Public REST API (JSON)

Output: JSON to stdout or file, matching the seen_jobs.json structure with source field.

Usage:
    python job_scraper/scraper.py --query "data engineer" --location Oslo --site all --pages 2
    python job_scraper/scraper.py --query "data engineer" --site finn --output results.json
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from typing import Optional

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------------------
# Finn.no configuration
# ---------------------------------------------------------------------------

FINN_LOCATION_CODES = {
    "norge": "0.20001",
    "oslo": "1.20001.20061",
    "tromsø": "1.20001.20019",
    "kristiansand": "1.20001.22042",
    "akershus": "1.20001.20003",
    "vestland": "1.20001.20046",
    "rogaland": "1.20001.20012",
    "trøndelag": "1.20001.20016",
    "nordland": "1.20001.20018",
    "møre og romsdal": "1.20001.20015",
    "vestfold": "1.20001.20009",
    "telemark": "1.20001.20009",
    "buskerud": "1.20001.20007",
    "innlandet": "1.20001.22034",
    "østfold": "1.20001.20054",
    "finnmark": "1.20001.20020",
    "agder": "1.20001.22042",
}

USER_AGENT = "Mozilla/5.0 (compatible; AgentJobSearch/1.0)"


def resolve_finn_location(location_str: str) -> str:
    key = location_str.strip().lower()
    if not key:
        return FINN_LOCATION_CODES["norge"]
    if key in FINN_LOCATION_CODES:
        return FINN_LOCATION_CODES[key]
    if re.match(r"^[\d.]+$", key):
        return key
    print(
        f"Warning: Unknown location '{location_str}'. Defaulting to all of Norway.",
        file=sys.stderr,
    )
    return FINN_LOCATION_CODES["norge"]


def curl_fetch(url: str) -> str:
    """Fetch a URL with curl. Returns empty string on failure."""
    try:
        result = subprocess.run(
            ["curl", "-sL", "--max-time", "15", "-A", USER_AGENT, url],
            capture_output=True,
            text=True,
            timeout=20,
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout
        return ""
    except Exception:
        return ""


# ===================================================================
# 1. FINN.NO Scraper (server-rendered HTML)
# ===================================================================


def parse_relative_date(text: str) -> str:
    today = datetime.now(timezone.utc)
    text = text.strip().lower()
    if text == "ny i dag":
        return today.strftime("%Y-%m-%d")
    if text == "i går":
        return (today - timedelta(days=1)).strftime("%Y-%m-%d")
    match = re.match(r"(\d+)\s*(dag|uke|måned|år)", text)
    if match:
        amount = int(match.group(1))
        unit = match.group(2)
        if unit == "dag":
            return (today - timedelta(days=amount)).strftime("%Y-%m-%d")
        elif unit == "uke":
            return (today - timedelta(weeks=amount)).strftime("%Y-%m-%d")
        elif unit == "måned":
            new_month = today.month - amount
            year = today.year
            while new_month < 1:
                new_month += 12
                year -= 1
            return today.replace(year=year, month=new_month).strftime("%Y-%m-%d")
    return text


def parse_norwegian_date(text: str) -> str:
    text = text.strip()
    if not text:
        return "unknown"
    match = re.match(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", text)
    if match:
        day, month, year = match.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"
    months_nb = {
        "januar": 1,
        "februar": 2,
        "mars": 3,
        "april": 4,
        "mai": 5,
        "juni": 6,
        "juli": 7,
        "august": 8,
        "september": 9,
        "oktober": 10,
        "november": 11,
        "desember": 12,
    }
    match = re.match(r"(\d{1,2})\.\s*([a-zæøå]+)\s*(\d{4})", text.lower())
    if match:
        day, month_name, year = match.groups()
        month = months_nb.get(month_name)
        if month:
            return f"{year}-{month:02d}-{int(day):02d}"
    if re.match(r"^\d{4}-\d{2}-\d{2}", text):
        return text
    return text


def scrape_finn(
    query: Optional[str] = None,
    location: str = "1.20001.20061",
    max_pages: int = 2,
) -> list[dict]:
    """Scrape job listings from finn.no using curl.

    ponytail: Uses a simple per-card extraction approach. The HTML is server-rendered
    with job cards containing predictable id attributes. Each card is an <article> with
    an id="card-<number>". We extract one card at a time using regex lookahead for the
    next card id. This is O(n²) in the worst case but fine for <100 cards.
    """
    jobs: list[dict] = []
    seen_urls: set[str] = set()

    base_url = "https://www.finn.no/job/search"
    params = [f"location={location}", "sort=RELEVANCE", "working_language=2"]
    if query:
        params.append(f"q={query.replace(' ', '+')}")
    search_url = f"{base_url}?{'&'.join(params)}"

    for page_num in range(1, max_pages + 1):
        url = f"{search_url}&page={page_num}"
        print(f"[finn.no] Fetching page {page_num}: {url}", file=sys.stderr)

        html = curl_fetch(url)
        if not html:
            print(f"[finn.no] Failed to fetch page {page_num}", file=sys.stderr)
            break

        # Find all card ids: <article ... id="card-12345">
        card_ids = re.findall(r'<article[^>]*\bid="card-(\d+)"[^>]*>', html)
        if not card_ids:
            print(f"[finn.no] No job cards found on page {page_num}", file=sys.stderr)
            break

        print(
            f"[finn.no] Found {len(card_ids)} job cards on page {page_num}",
            file=sys.stderr,
        )

        for cid in card_ids:
            # Extract card content: from <article id="card-<cid>"> to next <article or end
            card_match = re.search(
                rf'<article[^>]*\bid="card-{cid}"[^>]*>.*?(?=<article\s|\Z)',
                html,
                re.DOTALL,
            )
            if not card_match:
                continue
            card_html = card_match.group()

            job = _extract_finn_job(card_html)
            if job and job["url"] not in seen_urls:
                seen_urls.add(job["url"])
                job["source"] = "finn.no"
                jobs.append(job)

    return jobs


def _extract_finn_job(card_html: str) -> Optional[dict]:
    """Extract job data from a single finn.no job card HTML block."""
    try:
        # URL and title: <a class="job-card-link ..." href="...">Title</a>
        link_match = re.search(
            r'<a[^>]*class="[^"]*job-card-link[^"]*"[^>]*href="([^"]+)"', card_html
        )
        if not link_match:
            return None
        url = link_match.group(1)
        if url.startswith("/"):
            url = f"https://www.finn.no{url}"

        # Extract title from the job-card-link anchor. The title is the text of the
        # first link matching job-card-link class. Strip any inner spans.
        title = "Unknown"
        link_area = re.search(
            r'<a[^>]*class="[^"]*job-card-link[^"]*"[^>]*>(.*?)</a>',
            card_html,
            re.DOTALL,
        )
        if link_area:
            raw = link_area.group(1)
            # Remove any HTML tags inside, keep text
            raw = re.sub(r"<[^>]+>", "", raw).strip()
            if raw:
                title = raw

        # Company: in <strong> inside .text-caption
        company_match = re.search(r"<strong>([^<]+)</strong>", card_html)
        company = company_match.group(1).strip() if company_match else "Unknown"

        # Date: inside <time datetime="...">
        date_text = ""
        time_match = re.search(r'<time[^>]*datetime="([^"]*)"', card_html)
        if time_match:
            date_text = time_match.group(1)
        else:
            date_match = re.search(r"<time[^>]*>([^<]+)</time>", card_html)
            if date_match:
                date_text = date_match.group(1).strip()
        date = parse_relative_date(date_text) if date_text else "unknown"

        # Location: find <li> in footer that does NOT contain date text
        location = ""
        footer_section = re.search(r"<footer[^>]*>.*?</footer>", card_html, re.DOTALL)
        if footer_section:
            footer_html = footer_section.group()
            pills = re.findall(r"<li[^>]*>([^<]+)</li>", footer_html)
            for pill in pills:
                pill_text = pill.strip()
                if pill_text and not re.search(
                    r"\d+\s*(dag|uke|måned|år)", pill_text.lower()
                ):
                    location = pill_text

        return {
            "title": title,
            "company": company,
            "location": location,
            "date": date,
            "url": url,
            "description_snippet": "",
        }
    except Exception as e:
        print(f"[finn.no] Warning: Failed to extract job: {e}", file=sys.stderr)
        return None


# ===================================================================
# 2. ARBEIDSPLASSEN.NO (NAV) Scraper
# ===================================================================


def scrape_arbeidsplassen(
    query: Optional[str] = None,
    location: str = "",
    max_pages: int = 2,
) -> list[dict]:
    """Scrape job listings from arbeidsplassen.nav.no using curl + detail page fetch.

    The search page is a Next.js SPA, but it renders job links in the HTML.
    We extract links, then fetch each detail page for full info.
    """
    jobs: list[dict] = []
    seen_urls: set[str] = set()

    base_url = "https://arbeidsplassen.nav.no/stillinger"
    params = []
    if query:
        params.append(f"q={query.replace(' ', '+')}")
    if location:
        params.append(f"county={location.upper()}")
    search_url = f"{base_url}?{'&'.join(params)}"

    for page_num in range(1, max_pages + 1):
        url = search_url  # NAV doesn't paginate via URL param; just re-fetch
        print(f"[arbeidsplassen.no] Fetching page {page_num}: {url}", file=sys.stderr)

        html = curl_fetch(url)
        if not html:
            print(f"[arbeidsplassen.no] Failed to fetch page", file=sys.stderr)
            break

        # Extract job detail links: /stillinger/stilling/<uuid>
        links = re.findall(r'href="/stillinger/stilling/([^"]+)"', html)
        unique_links = list(dict.fromkeys(links))  # deduplicate preserving order

        if not unique_links:
            print(f"[arbeidsplassen.no] No job links found", file=sys.stderr)
            break

        print(
            f"[arbeidsplassen.no] Found {len(unique_links)} job links", file=sys.stderr
        )

        for job_id in unique_links:
            if job_id in seen_urls:
                continue
            seen_urls.add(job_id)
            job_url = f"https://arbeidsplassen.nav.no/stillinger/stilling/{job_id}"
            job_detail_html = curl_fetch(job_url)
            if job_detail_html:
                job = _extract_arbeidsplassen_job(job_detail_html, job_url)
                if job:
                    job["source"] = "arbeidsplassen.no"
                    jobs.append(job)
            else:
                # Fallback: just record the link without details
                jobs.append(
                    {
                        "title": job_id,  # placeholder
                        "company": "Unknown",
                        "location": location or "Unknown",
                        "date": "unknown",
                        "url": job_url,
                        "description_snippet": "",
                        "source": "arbeidsplassen.no",
                    }
                )

        if len(jobs) >= 100:
            break

    return jobs


def _extract_arbeidsplassen_job(html: str, url: str) -> Optional[dict]:
    """Extract job data from arbeidsplassen.no detail page."""
    try:
        # Title: from <title> or <h1>
        title_match = re.search(r"<title>([^<]+)</title>", html)
        title = title_match.group(1).strip() if title_match else "Unknown"
        # Clean title (remove site suffix like " - Arbeidsplassen")
        title = re.sub(
            r"\s*[-–|]\s*Arbeidsplassen\.*$", "", title, flags=re.IGNORECASE
        ).strip()

        # Company: various possible patterns
        company = "Unknown"
        # Try job-advertiser or similar
        company_match = re.search(
            r"(?:employer|company|arbeidsgiver)[^>]*>([^<]+)</", html, re.IGNORECASE
        )
        if company_match:
            company = company_match.group(1).strip()
        else:
            # Look for "Arbeidsgiver" in definition list
            company_match = re.search(
                r"<dt[^>]*>[^<]*Arbeidsgiver[^<]*</dt>\s*<dd[^>]*>([^<]+)</dd>",
                html,
                re.IGNORECASE,
            )
            if company_match:
                company = company_match.group(1).strip()

        # Location
        location = ""
        loc_match = re.search(
            r"<dt[^>]*>[^<]*(?:location|sted|Sted)[^<]*</dt>\s*<dd[^>]*>([^<]+)</dd>",
            html,
            re.IGNORECASE,
        )
        if loc_match:
            location = loc_match.group(1).strip()

        # Date
        date_text = ""
        date_match = re.search(r'<time[^>]*datetime="([^"]+)"', html)
        if date_match:
            date_text = date_match.group(1)
            # Truncate ISO datetime to date
            date_match_full = re.match(r"(\d{4}-\d{2}-\d{2})", date_text)
            if date_match_full:
                date_text = date_match_full.group(1)
        date = parse_norwegian_date(date_text) if date_text else "unknown"

        # Description snippet
        desc_match = re.search(
            r'<meta[^>]*name="description"[^>]*content="([^"]+)"', html, re.IGNORECASE
        )
        description_snippet = desc_match.group(1).strip() if desc_match else ""

        return {
            "title": title,
            "company": company,
            "location": location,
            "date": date,
            "url": url,
            "description_snippet": description_snippet,
        }
    except Exception as e:
        print(
            f"[arbeidsplassen.no] Warning: Failed to extract job: {e}", file=sys.stderr
        )
        return None


# ===================================================================
# 3. JOBNORGE.NO Scraper (public API)
# ===================================================================

# ponytail: Norwegian fylkesnummer (county codes) post-2024 split.
# API requires integer codes, not names. Map both county and city names
# to the correct fylkesnummer so callers can pass either.
JOBNORGE_COUNTY_CODES = {
    # Counties
    "oslo": 3,
    "rogaland": 11,
    "møre og romsdal": 15,
    "nordland": 18,
    "innlandet": 31,
    "vestfold": 32,
    "telemark": 33,
    "agder": 34,
    "vestland": 38,
    "trøndelag": 42,
    "troms": 46,
    "finnmark": 54,
    # Cities → county
    "bergen": 38,
    "trondheim": 42,
    "stavanger": 11,
    "tromsø": 46,
    "kristiansand": 34,
    "fredrikstad": 32,
    "sandnes": 11,
    "tromso": 46,
    "drammen": 32,
    "sarpsborg": 32,
    "skien": 33,
    "ålesund": 15,
    "haugesund": 11,
    "sandefjord": 32,
    "arendal": 34,
    "hanski": 32,
    "molde": 15,
    "hamar": 31,
    "larvik": 32,
    "halden": 32,
    "moss": 32,
    "porsgrunn": 33,
    "bodø": 18,
    "narvik": 18,  # Narvik is in Troms after 2024, but geographically Nordland-ish; Troms=46
    "alstahaug": 18,
    "levanger": 42,
    "namsos": 42,
    "steinkjer": 42,
}


def resolve_jobbnorge_county(location_str: str) -> Optional[int]:
    """Resolve a location name to a Jobbnorge fylkesnummer. Returns None if unknown."""
    key = location_str.strip().lower()
    if key in JOBNORGE_COUNTY_CODES:
        return JOBNORGE_COUNTY_CODES[key]
    if key.isdigit():
        return int(key)
    return None


def scrape_jobbnorge(
    query: Optional[str] = None,
    location: str = "",
    max_pages: int = 2,
) -> list[dict]:
    """Scrape job listings from jobbnorge.no using their public API (v3/Jobs).

    ponytail: API requires county=fylkesnummer (int), not a location string.
    resolve_jobbnorge_county maps city/county names to codes.
    """
    jobs: list[dict] = []
    seen_urls: set[str] = set()

    api_url = "https://publicapi.jobbnorge.no/v3/Jobs"
    params = ["results=50"]
    if query:
        params.append(f"term={query.replace(' ', '%20')}")
    if location:
        county_code = resolve_jobbnorge_county(location)
        if county_code is not None:
            params.append(f"county={county_code}")
        else:
            print(
                f"[jobbnorge.no] Warning: Unknown location '{location}'. "
                f"Passing without county filter.",
                file=sys.stderr,
            )

    for page_num in range(1, max_pages + 1):
        params_with_page = params + [f"page={page_num}"]
        url = f"{api_url}?{'&'.join(params_with_page)}"
        print(f"[jobbnorge.no] Fetching page {page_num}: {url}", file=sys.stderr)

        raw = curl_fetch(url)
        if not raw:
            print(f"[jobbnorge.no] Failed to fetch page {page_num}", file=sys.stderr)
            break

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            print(f"[jobbnorge.no] Invalid JSON on page {page_num}", file=sys.stderr)
            break

        items = data.get("jobs", [])
        if not items:
            print(f"[jobbnorge.no] No items found on page {page_num}", file=sys.stderr)
            break

        print(
            f"[jobbnorge.no] Found {len(items)} jobs on page {page_num}",
            file=sys.stderr,
        )

        for item in items:
            job_url = item.get("link", "")
            if job_url and not job_url.startswith("http"):
                job_url = (
                    f"https://www.jobbnorge.no{job_url}"
                    if job_url.startswith("/")
                    else ""
                )
            if job_url in seen_urls:
                continue
            seen_urls.add(job_url)

            title = item.get("title") or "Unknown"
            company = item.get("employer") or "Unknown"

            # Location: from locations[0] object
            loc = ""
            locations = item.get("locations", [])
            if locations:
                area = locations[0].get("area", "")
                municipality = locations[0].get("municipality", "")
                loc = area or municipality or ""

            date_raw = item.get("publicationDate") or ""
            date = parse_norwegian_date(date_raw) if date_raw else "unknown"

            # Build a proper URL if the API gives us an ID
            if not job_url and item.get("id"):
                job_url = (
                    f"https://www.jobbnorge.no/ledige-stillinger/stilling/{item['id']}"
                )

            jobs.append(
                {
                    "title": title,
                    "company": company,
                    "location": loc,
                    "date": date,
                    "url": job_url,
                    "description_snippet": (item.get("summary") or "")[:200],
                    "source": "jobbnorge.no",
                }
            )

    return jobs


# ===================================================================
# Orchestrator
# ===================================================================

SITE_SCRAPERS = {
    "finn": scrape_finn,
    "nav": scrape_arbeidsplassen,
    "arbeidsplassen": scrape_arbeidsplassen,
    "jobbnorge": scrape_jobbnorge,
    # ponytail: LinkedIn blocks unauthenticated search; individual job detail pages
    # work via /apply's web_fetch instead. LinkedIn is intentionally excluded.
}


def scrape_all(
    query: Optional[str] = None,
    location: str = "",
    max_pages: int = 2,
    sites: list[str] = None,
) -> list[dict]:
    """Scrape job listings from multiple sites using curl."""
    all_jobs: list[dict] = []
    seen_urls: set[str] = set()

    if sites is None:
        sites = ["finn", "nav", "jobbnorge"]

    for site in sites:
        site = site.lower().strip()
        scraper = SITE_SCRAPERS.get(site)
        if not scraper:
            print(f"Warning: Unknown site '{site}'. Skipping.", file=sys.stderr)
            continue

        print(f"\n{'='*60}", file=sys.stderr)
        print(f"Scraping {site}...", file=sys.stderr)
        print(f"{'='*60}", file=sys.stderr)

        try:
            if site == "finn":
                loc_code = resolve_finn_location(location)
                jobs = scraper(query=query, location=loc_code, max_pages=max_pages)
            else:
                jobs = scraper(query=query, location=location, max_pages=max_pages)

            for job in jobs:
                if job["url"] not in seen_urls:
                    seen_urls.add(job["url"])
                    all_jobs.append(job)

            print(
                f"Got {len(jobs)} jobs from {site} ({len(all_jobs)} unique total)",
                file=sys.stderr,
            )
        except Exception as e:
            print(f"Error scraping {site}: {e}", file=sys.stderr)
            continue

    return all_jobs


# ===================================================================
# Output formatting
# ===================================================================


def format_as_seen_json(jobs: list[dict], query: str, location: str) -> dict:
    """Format scraped jobs into the seen_jobs.json structure with source tracking."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    seen = {}
    for job in jobs:
        key = job["url"]
        seen[key] = {
            "title": job["title"],
            "company": job["company"],
            "url": job["url"],
            "location": job.get("location", ""),
            "source": job.get("source", "unknown"),
            "first_seen": job.get("date", today),
            "fit": "unknown",
            "status": "new",
        }
    return {
        "query": query or "all",
        "location": location,
        "scraped_at": today,
        "total": len(jobs),
        "seen": seen,
    }


# ===================================================================
# CLI
# ===================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Scrape job listings from Norwegian job portals using curl"
    )
    parser.add_argument(
        "--query",
        "-q",
        type=str,
        default=None,
        help="Search query (e.g. 'data engineer'). If omitted, fetches all recent jobs.",
    )
    parser.add_argument(
        "--location",
        "-l",
        type=str,
        default="",
        help="Location (city name). Default: all of Norway",
    )
    parser.add_argument(
        "--site",
        "-s",
        type=str,
        default="all",
        choices=["finn", "nav", "arbeidsplassen", "jobbnorge", "all"],
        help="Job site to scrape. 'all' scrapes finn.no, arbeidsplassen.no, jobbnorge.no. Default: all",
    )
    parser.add_argument(
        "--pages",
        "-p",
        type=int,
        default=2,
        help="Number of pages to scrape per site. Default: 2",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output file path. If omitted, prints JSON to stdout.",
    )
    parser.add_argument(
        "--dump-all",
        action="store_true",
        help="Fetch recent jobs without a query filter.",
    )

    args = parser.parse_args()

    query = args.query
    if args.dump_all:
        query = None

    if args.site == "all":
        sites = ["finn", "nav", "jobbnorge"]
    else:
        sites = [args.site]

    jobs = scrape_all(
        query=query, location=args.location, max_pages=args.pages, sites=sites
    )

    output = {
        "jobs_list": [
            {
                "title": j["title"],
                "company": j["company"],
                "location": j.get("location", ""),
                "date": j.get("date", ""),
                "url": j["url"],
                "source": j.get("source", "unknown"),
                "description_snippet": j.get("description_snippet", ""),
            }
            for j in jobs
        ]
    }

    output_str = json.dumps(output, indent=2, ensure_ascii=False)
    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_str)
        print(f"Written {len(jobs)} jobs to {args.output}", file=sys.stderr)
    else:
        print(output_str)


if __name__ == "__main__":
    main()
