#!/usr/bin/env python3
"""
Multi-Site Job Scraper
======================
Uses Playwright (headless Chromium) to scrape job listings from Norwegian job portals.

Supported sites:
  - finn.no        : JavaScript-heavy SPA
  - arbeidsplassen.nav.no : Next.js SPA
  - jobbnorge.no   : jQuery-based SPA (loads results via AJAX into <div id="jobs">)

Output: JSON to stdout or file, matching the seen_jobs.json structure with source field.

Usage:
    # Finn.no
    python job_scraper/scraper.py --query "data engineer" --location Oslo --site finn --pages 2

    # Arbeidsplassen.no
    python job_scraper/scraper.py --query "data engineer" --location Oslo --site nav --pages 2

    # Jobbnorge.no
    python job_scraper/scraper.py --query "data engineer" --site jobbnorge --pages 2

    # All sites at once
    python job_scraper/scraper.py --query "data engineer" --location Oslo --site all --pages 2

    # Output to file
    python job_scraper/scraper.py --query "software developer" --location Oslo --site all --output results.json

    # Dump recent jobs without query filter
    python job_scraper/scraper.py --dump-all --site all --pages 1
"""

import argparse
import asyncio
import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import Optional

from playwright.async_api import async_playwright

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------------------
# Finn.no configuration
# ---------------------------------------------------------------------------

# Finn.no location codes (numeric IDs)
FINN_LOCATION_CODES = {
    "norge": "0.20001",
    "oslo": "0.20061",
    "bergen": "1.20001.20046",
    "trondheim": "1.20001.20016",
    "stavanger": "1.20001.20012",
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

FINN_JOB_CATEGORY = "0"
FINN_JOB_SUB_CATEGORY = "1.2.1"


def resolve_finn_location(location_str: str) -> str:
    """Resolve a location string to a finn.no location code."""
    key = location_str.strip().lower()
    if key in FINN_LOCATION_CODES:
        return FINN_LOCATION_CODES[key]
    if re.match(r"^[\d.]+$", key):
        return key
    print(
        f"Warning: Unknown location '{location_str}'. Defaulting to 'oslo'.",
        file=sys.stderr,
    )
    return FINN_LOCATION_CODES["oslo"]


# ---------------------------------------------------------------------------
# Arbeidsplassen.no configuration
# ---------------------------------------------------------------------------

NAV_LOCATION_CODES = {
    "norge": "",
    "oslo": "Oslo",
    "bergen": "Bergen",
    "trondheim": "Trondheim",
    "stavanger": "Stavanger",
    "tromsø": "Tromsø",
    "kristiansand": "Kristiansand",
    "akershus": "Akershus",
    "vestland": "Vestland",
    "rogaland": "Rogaland",
    "trøndelag": "Trøndelag",
    "nordland": "Nordland",
    "møre og romsdal": "Møre og Romsdal",
    "vestfold": "Vestfold",
    "telemark": "Telemark",
    "buskerud": "Buskerud",
    "innlandet": "Innlandet",
    "østfold": "Østfold",
    "finnmark": "Finnmark",
    "agder": "Agder",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def parse_relative_date(text: str) -> str:
    """Parse relative date strings (finn.no style) into ISO date."""
    today = datetime.now(timezone.utc)
    text = text.strip().lower()

    if text == "ny i dag":
        return today.strftime("%Y-%m-%d")
    if text == "i går":
        return today.replace(day=today.day - 1).strftime("%Y-%m-%d")

    match = re.match(r"(\d+)\s*(dag|uke|måned|år)", text)
    if match:
        amount = int(match.group(1))
        unit = match.group(2)
        if unit == "dag":
            return today.replace(day=today.day - amount).strftime("%Y-%m-%d")
        elif unit == "uke":
            return today.replace(day=today.day - amount * 7).strftime("%Y-%m-%d")
        elif unit == "måned":
            new_month = today.month - amount
            year = today.year
            while new_month < 1:
                new_month += 12
                year -= 1
            return today.replace(year=year, month=new_month).strftime("%Y-%m-%d")

    return text


def parse_norwegian_date(text: str) -> str:
    """Parse Norwegian date strings like '1. juni 2026' or '01.06.2026' into ISO date."""
    text = text.strip()
    if not text:
        return "unknown"

    # Try DD.MM.YYYY
    match = re.match(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", text)
    if match:
        day, month, year = match.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"

    # Try Norwegian month names: "1. juni 2026"
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

    # Try ISO format already
    if re.match(r"^\d{4}-\d{2}-\d{2}", text):
        return text

    return text


# ---------------------------------------------------------------------------
# Browser / context helper
# ---------------------------------------------------------------------------


async def make_browser_context(playwright, headless: bool = True):
    """Create a standard browser context for scraping."""
    browser = await playwright.chromium.launch(
        headless=headless,
        args=["--no-sandbox", "--disable-setuid-sandbox"],
    )
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={"width": 1920, "height": 1080},
    )
    return browser, context


# ===================================================================
# 1. FINN.NO Scraper
# ===================================================================


async def scrape_finn(
    query: Optional[str] = None,
    location: str = "0.20061",
    max_pages: int = 2,
    headless: bool = True,
    timeout_ms: int = 30000,
) -> list[dict]:
    """
    Scrape job listings from finn.no using Playwright.

    Args:
        query: Search query (e.g. "data engineer"). If None, fetches all recent jobs.
        location: Finn.no location code (e.g. "0.20061" for Oslo).
        max_pages: Number of search result pages to scrape.
        headless: Run browser in headless mode.
        timeout_ms: Navigation timeout in milliseconds.

    Returns:
        List of job dicts with keys: title, company, location, date, url, description_snippet, source
    """
    jobs: list[dict] = []
    seen_urls: set[str] = set()

    base_url = "https://www.finn.no/job/fulltime/search.html"
    params = [
        f"location={location}",
        "sort=PUBLISHED_DESC",
    ]
    if query:
        params.append(f"q={query.replace(' ', '+')}")

    search_url = f"{base_url}?{'&'.join(params)}"

    async with async_playwright() as p:
        browser, context = await make_browser_context(p, headless)
        page = await context.new_page()

        for page_num in range(1, max_pages + 1):
            url = f"{search_url}&page={page_num}"
            print(f"[finn.no] Fetching page {page_num}: {url}", file=sys.stderr)

            try:
                await page.goto(url, timeout=timeout_ms, wait_until="networkidle")
                await page.wait_for_timeout(3000)
                await page.wait_for_selector("article", timeout=10000)
            except Exception as e:
                print(
                    f"[finn.no] Warning: Failed to load page {page_num}: {e}",
                    file=sys.stderr,
                )
                break

            articles = await page.query_selector_all("article")
            print(
                f"[finn.no] Found {len(articles)} articles on page {page_num}",
                file=sys.stderr,
            )

            if not articles:
                print("[finn.no] No more articles found. Stopping.", file=sys.stderr)
                break

            for article in articles:
                job = await extract_finn_job(article)
                if job and job["url"] not in seen_urls:
                    seen_urls.add(job["url"])
                    job["source"] = "finn.no"
                    jobs.append(job)

        await browser.close()

    return jobs


async def extract_finn_job(article) -> Optional[dict]:
    """Extract job data from a single finn.no article element."""
    try:
        link_el = await article.query_selector("a.job-card-link")
        if not link_el:
            return None

        title = await link_el.inner_text()
        url = await link_el.get_attribute("href")
        if not url:
            return None
        if url.startswith("/"):
            url = f"https://www.finn.no{url}"

        company_el = await article.query_selector(".text-caption strong")
        company = await company_el.inner_text() if company_el else "Unknown"

        desc_el = await article.query_selector("h3")
        description_snippet = await desc_el.inner_text() if desc_el else ""

        location = ""
        date_text = ""
        footer = await article.query_selector("footer")
        if footer:
            pills = await footer.query_selector_all("li")
            for pill in pills:
                text = (await pill.inner_text()).strip()
                time_el = await pill.query_selector("time")
                if time_el:
                    date_text = text
                else:
                    location = text

        date = parse_relative_date(date_text) if date_text else "unknown"

        return {
            "title": title.strip(),
            "company": company.strip(),
            "location": location.strip(),
            "date": date,
            "url": url,
            "description_snippet": description_snippet.strip(),
        }
    except Exception as e:
        print(f"[finn.no] Warning: Failed to extract job: {e}", file=sys.stderr)
        return None


# ===================================================================
# 2. ARBEIDSPLASSEN.NO (NAV) Scraper
# ===================================================================


async def scrape_arbeidsplassen(
    query: Optional[str] = None,
    location: str = "",
    max_pages: int = 2,
    headless: bool = True,
    timeout_ms: int = 30000,
) -> list[dict]:
    """
    Scrape job listings from arbeidsplassen.nav.no using Playwright.

    This is a Next.js SPA that renders job results client-side.

    Args:
        query: Search query (e.g. "data engineer"). If None, fetches all recent jobs.
        location: Location filter (e.g. "Oslo" or "" for all).
        max_pages: Number of search result pages to scrape.
        headless: Run browser in headless mode.
        timeout_ms: Navigation timeout in milliseconds.

    Returns:
        List of job dicts with keys: title, company, location, date, url, description_snippet, source
    """
    jobs: list[dict] = []
    seen_urls: set[str] = set()

    base_url = "https://arbeidsplassen.nav.no/sok"
    params = []
    if query:
        params.append(f"searchstring={query.replace(' ', '+')}")
    if location:
        params.append(f"location={location}")
    params.append("page=1")  # We'll override this per-page

    async with async_playwright() as p:
        browser, context = await make_browser_context(p, headless)
        page = await context.new_page()

        for page_num in range(1, max_pages + 1):
            param_list = [pp for pp in params if not pp.startswith("page=")]
            param_list.append(f"page={page_num}")
            url = f"{base_url}?{'&'.join(param_list)}"
            print(
                f"[arbeidsplassen.no] Fetching page {page_num}: {url}",
                file=sys.stderr,
            )

            try:
                await page.goto(url, timeout=timeout_ms, wait_until="networkidle")
                await page.wait_for_timeout(5000)

                # Try to wait for job cards to appear. NAV uses a specific card layout.
                # Common selectors for job cards on this site:
                try:
                    await page.wait_for_selector(
                        'a[href*="/stillinger/"]', timeout=10000
                    )
                except Exception:
                    # Try alternative selectors
                    try:
                        await page.wait_for_selector(
                            "[data-testid='job-card'], .job-card, article", timeout=5000
                        )
                    except Exception:
                        pass

            except Exception as e:
                print(
                    f"[arbeidsplassen.no] Warning: Failed to load page {page_num}: {e}",
                    file=sys.stderr,
                )
                break

            # Extract job listings. Try several possible selectors.
            job_elements = await page.query_selector_all('a[href*="/stillinger/"]')
            if not job_elements:
                # Try a broader search for job links
                job_elements = await page.query_selector_all("a[href*='stilling']")

            print(
                f"[arbeidsplassen.no] Found {len(job_elements)} potential job links on page {page_num}",
                file=sys.stderr,
            )

            if not job_elements:
                print(
                    "[arbeidsplassen.no] No job links found. Stopping.",
                    file=sys.stderr,
                )
                break

            for el in job_elements:
                job = await extract_arbeidsplassen_job(page, el)
                if job and job["url"] not in seen_urls:
                    seen_urls.add(job["url"])
                    job["source"] = "arbeidsplassen.no"
                    jobs.append(job)

            # Limit jobs to avoid duplicates
            if len(jobs) >= 100:
                break

        await browser.close()

    return jobs


async def extract_arbeidsplassen_job(page, link_element) -> Optional[dict]:
    """Extract job data from an arbeidsplassen.no job link element."""
    try:
        url = await link_element.get_attribute("href")
        if not url:
            return None
        if url.startswith("/"):
            url = f"https://arbeidsplassen.nav.no{url}"

        # Get the title text from the link element
        title = (await link_element.inner_text()).strip()
        if not title or len(title) < 3:
            return None

        # Try to find the parent card container for additional metadata
        # Navigate up to find the card container
        parent = await link_element.evaluate(
            "el => el.closest('li, div, article, section')"
        )

        company = "Unknown"
        location = ""
        date_text = ""

        if parent:
            # Try to extract company name
            company_selectors = await page.evaluate(
                """(parent) => {
                    const el = parent.querySelector('[data-testid="company-name"], .company-name, strong');
                    return el ? el.textContent.trim() : null;
                }""",
                parent,
            )
            if company_selectors:
                company = company_selectors

            # Try to extract location
            location_selectors = await page.evaluate(
                """(parent) => {
                    const el = parent.querySelector('[data-testid="location"], .location');
                    return el ? el.textContent.trim() : null;
                }""",
                parent,
            )
            if location_selectors:
                location = location_selectors

            # Try to extract date
            date_selectors = await page.evaluate(
                """(parent) => {
                    const el = parent.querySelector('time');
                    return el ? (el.dateTime || el.textContent.trim()) : null;
                }""",
                parent,
            )
            if date_selectors:
                date_text = date_selectors

        # Fallback: use page-level selectors near the link
        if company == "Unknown":
            company_el = await link_element.evaluate("""(el) => {
                    const section = el.closest('li, div, article, section');
                    if (!section) return null;
                    const strong = section.querySelector('strong');
                    return strong ? strong.textContent.trim() : null;
                }""")
            if company_el:
                company = company_el

        date = parse_norwegian_date(date_text) if date_text else "unknown"

        return {
            "title": title,
            "company": company,
            "location": location,
            "date": date,
            "url": url,
            "description_snippet": "",
        }
    except Exception as e:
        print(
            f"[arbeidsplassen.no] Warning: Failed to extract job: {e}",
            file=sys.stderr,
        )
        return None


# ===================================================================
# 3. JOBNORGE.NO Scraper
# ===================================================================


async def scrape_jobbnorge(
    query: Optional[str] = None,
    location: str = "",
    max_pages: int = 2,
    headless: bool = True,
    timeout_ms: int = 30000,
) -> list[dict]:
    """
    Scrape job listings from jobbnorge.no using Playwright.

    Jobbnorge is a jQuery-based SPA that loads results via AJAX into <div id="jobs">.

    Args:
        query: Search query (e.g. "data engineer"). If None, fetches all recent jobs.
        location: Location filter (optional).
        max_pages: Number of search result pages to scrape.
        headless: Run browser in headless mode.
        timeout_ms: Navigation timeout in milliseconds.

    Returns:
        List of job dicts with keys: title, company, location, date, url, description_snippet, source
    """
    jobs: list[dict] = []
    seen_urls: set[str] = set()

    base_url = "https://www.jobbnorge.no/search"
    params = []
    if query:
        params.append(f"q={query.replace(' ', '+')}")
    if location:
        params.append(f"location={location}")

    async with async_playwright() as p:
        browser, context = await make_browser_context(p, headless)
        page = await context.new_page()

        # Jobbnorge loads all results on one page with "Vis flere" button.
        # We'll load the page once and scroll/interact to load more.
        url = f"{base_url}?{'&'.join(params)}" if params else base_url
        print(f"[jobbnorge.no] Fetching: {url}", file=sys.stderr)

        try:
            await page.goto(url, timeout=timeout_ms, wait_until="networkidle")
            await page.wait_for_timeout(5000)

            # Wait for the jobs container to appear
            try:
                await page.wait_for_selector("#jobs", timeout=10000)
            except Exception:
                print(
                    "[jobbnorge.no] Warning: #jobs container not found",
                    file=sys.stderr,
                )

            # Wait for initial job items to load
            await page.wait_for_timeout(3000)

            # Click "Vis flere" multiple times to load more results
            for page_num in range(1, max_pages):
                try:
                    show_more_btn = await page.query_selector("#showmore button")
                    if show_more_btn:
                        is_visible = await show_more_btn.is_visible()
                        if is_visible:
                            await show_more_btn.click()
                            await page.wait_for_timeout(3000)
                            print(
                                f"[jobbnorge.no] Clicked 'Vis flere' (page {page_num + 1})",
                                file=sys.stderr,
                            )
                        else:
                            print(
                                "[jobbnorge.no] 'Vis flere' button not visible, stopping.",
                                file=sys.stderr,
                            )
                            break
                    else:
                        print(
                            "[jobbnorge.no] No 'Vis flere' button found, stopping.",
                            file=sys.stderr,
                        )
                        break
                except Exception as e:
                    print(
                        f"[jobbnorge.no] Warning: Could not click 'Vis flere': {e}",
                        file=sys.stderr,
                    )
                    break

        except Exception as e:
            print(f"[jobbnorge.no] Warning: Failed to load page: {e}", file=sys.stderr)

        # Extract job listings from the rendered page
        # Jobbnorge renders search-result elements inside #jobs
        job_elements = await page.query_selector_all("#jobs .search-result")
        if not job_elements:
            # Fallback: look for any links to job details
            job_elements = await page.query_selector_all(
                "#jobs a[href*='ledig-stilling']"
            )
        if not job_elements:
            job_elements = await page.query_selector_all("#jobs a[href*='stilling']")

        print(
            f"[jobbnorge.no] Found {len(job_elements)} job elements",
            file=sys.stderr,
        )

        for el in job_elements:
            job = await extract_jobbnorge_job(page, el)
            if job and job["url"] not in seen_urls:
                seen_urls.add(job["url"])
                job["source"] = "jobbnorge.no"
                jobs.append(job)

        await browser.close()

    return jobs


async def extract_jobbnorge_job(page, element) -> Optional[dict]:
    """Extract job data from a jobbnorge.no job element."""
    try:
        # Try to find the link
        link_el = await element.query_selector("a")
        if not link_el:
            # The element itself might be a link
            tag = await element.evaluate("el => el.tagName.toLowerCase()")
            if tag == "a":
                link_el = element
            else:
                return None

        url = await link_el.get_attribute("href")
        if not url:
            return None
        if url.startswith("/"):
            url = f"https://www.jobbnorge.no{url}"

        title = (await link_el.inner_text()).strip()

        # Extract metadata from the job element
        company = "Unknown"
        location = ""
        date_text = ""

        # Company - often in a specific element within search-result
        company_el = await element.query_selector(".employer, .company")
        if company_el:
            company = (await company_el.inner_text()).strip()

        # Location
        location_el = await element.query_selector(".location, .city")
        if location_el:
            location = (await location_el.inner_text()).strip()

        # Date
        date_el = await element.query_selector(".date, .deadline, time")
        if date_el:
            date_text = (await date_el.inner_text()).strip()

        # Try extracting from inline text if structured elements aren't available
        if company == "Unknown":
            # Try to get all text and parse
            all_text = (await element.inner_text()).strip()
            lines = [l.strip() for l in all_text.split("\n") if l.strip()]
            if len(lines) >= 2:
                # Often the structure is: Title, Company, Location + Date
                if not company and len(lines) > 1:
                    company = lines[1]
                if not location and len(lines) > 2:
                    location = lines[2]

        date = parse_norwegian_date(date_text) if date_text else "unknown"

        return {
            "title": title,
            "company": company,
            "location": location,
            "date": date,
            "url": url,
            "description_snippet": "",
        }
    except Exception as e:
        print(
            f"[jobbnorge.no] Warning: Failed to extract job: {e}",
            file=sys.stderr,
        )
        return None


# ===================================================================
# Orchestrator
# ===================================================================


SITE_SCRAPERS = {
    "finn": scrape_finn,
    "nav": scrape_arbeidsplassen,
    "arbeidsplassen": scrape_arbeidsplassen,
    "jobbnorge": scrape_jobbnorge,
}


async def scrape_all(
    query: Optional[str] = None,
    location: str = "oslo",
    max_pages: int = 2,
    sites: list[str] = None,
    headless: bool = True,
    timeout_ms: int = 30000,
) -> list[dict]:
    """
    Scrape job listings from multiple sites.

    Args:
        query: Search query.
        location: Location string (city name).
        max_pages: Number of pages per site.
        sites: List of site identifiers to scrape. Defaults to all.
        headless: Run browser in headless mode.
        timeout_ms: Navigation timeout.

    Returns:
        Combined list of job dicts from all sites.
    """
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
                jobs = await scraper(
                    query=query,
                    location=loc_code,
                    max_pages=max_pages,
                    headless=headless,
                    timeout_ms=timeout_ms,
                )
            elif site == "nav" or site == "arbeidsplassen":
                loc = NAV_LOCATION_CODES.get(location.strip().lower(), location)
                jobs = await scraper(
                    query=query,
                    location=loc,
                    max_pages=max_pages,
                    headless=headless,
                    timeout_ms=timeout_ms,
                )
            else:  # jobbnorge
                jobs = await scraper(
                    query=query,
                    location=location,
                    max_pages=max_pages,
                    headless=headless,
                    timeout_ms=timeout_ms,
                )

            # Deduplicate across sites
            for job in jobs:
                if job["url"] not in seen_urls:
                    seen_urls.add(job["url"])
                    all_jobs.append(job)

            print(
                f"Got {len(jobs)} jobs from {site} ({len(all_jobs)} unique total)",
                file=sys.stderr,
            )

        except Exception as e:
            print(
                f"Error scraping {site}: {e}",
                file=sys.stderr,
            )
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
        description="Scrape job listings from Norwegian job portals using Playwright"
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
        default="oslo",
        help="Location (city name). Default: oslo",
    )
    parser.add_argument(
        "--site",
        "-s",
        type=str,
        default="all",
        choices=["finn", "nav", "arbeidsplassen", "jobbnorge", "all"],
        help="Job site to scrape. 'all' scrapes finn.no, arbeidsplassen.no, and jobbnorge.no. Default: all",
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
    parser.add_argument(
        "--visible",
        action="store_true",
        help="Run with visible browser (not headless) for debugging.",
    )

    args = parser.parse_args()

    query = args.query
    if args.dump_all:
        query = None

    # Resolve sites to scrape
    if args.site == "all":
        sites = ["finn", "nav", "jobbnorge"]
    else:
        sites = [args.site]

    try:
        jobs = asyncio.run(
            scrape_all(
                query=query,
                location=args.location,
                max_pages=args.pages,
                sites=sites,
                headless=not args.visible,
            )
        )
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(1)

    # Format as seen_jobs JSON
    output = format_as_seen_json(jobs, query or "all", args.location)

    # Also include a flat list for easy consumption by the Gemini agent
    output["jobs_list"] = [
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
