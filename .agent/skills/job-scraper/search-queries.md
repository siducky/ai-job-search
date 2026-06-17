# Search Queries for Job Scraper

<!-- SETUP: Customize these queries based on your skills, target roles, and location -->

## Search Sites

Primary (Norwegian job market):
- **finn.no** - Norway's largest online marketplace (jobs section)
- **jobbnorge.no** - major Norwegian job board
- **nav.arbeidplassen.no** - official Norwegian welfare and labour office job portal

Secondary (company career pages via Google):
- Direct Google searches with `site:` filters for known target companies
- **linkedin.com/jobs** - LinkedIn job listings (filter: Norway / your city)

## Query Categories

Queries are grouped by priority. Each query should be combined with your location terms (e.g. "Oslo", "Bergen", "Trondheim", "Stavanger") where the site supports it.

### Priority 1: [YOUR_PRIMARY_ROLE_TYPE]

These match your strongest and most desired career direction.

```
site:finn.no "[YOUR_PRIMARY_JOB_TITLE]" [YOUR_CITY]
site:finn.no "[YOUR_KEY_SKILL]" [YOUR_CITY]
site:jobbnorge.no "[YOUR_PRIMARY_JOB_TITLE]" [YOUR_CITY]
site:arbeidplassen.nav.no "[YOUR_PRIMARY_JOB_TITLE]" [YOUR_CITY]
site:linkedin.com/jobs "[YOUR_PRIMARY_JOB_TITLE]" Norway
```

### Priority 2: [YOUR_DOMAIN_EXPERTISE]

These match your domain expertise.

```
site:finn.no [YOUR_DOMAIN_KEYWORD_1] [YOUR_CITY]
site:finn.no [YOUR_DOMAIN_KEYWORD_2] [YOUR_COUNTRY]
site:jobbnorge.no [YOUR_DOMAIN_KEYWORD_1] [YOUR_CITY]
site:linkedin.com/jobs [YOUR_DOMAIN_KEYWORD_1] [YOUR_CITY] Norway
```

### Priority 3: [YOUR_ADJACENT_ROLE_TYPE]

Adjacent roles you could pivot into.

```
site:finn.no "[YOUR_ADJACENT_TITLE_1]" [YOUR_KEY_SKILL] [YOUR_CITY]
site:finn.no "[YOUR_ADJACENT_TITLE_2]" [YOUR_KEY_SKILL] [YOUR_CITY]
site:jobbnorge.no "[YOUR_ADJACENT_TITLE_1]" [YOUR_KEY_SKILL] [YOUR_CITY]
```

### Priority 4: Broader Technical / Consulting

Wider net for general technical roles.

```
site:finn.no [YOUR_KEY_SKILL] [YOUR_CITY]
site:jobbnorge.no [YOUR_KEY_SKILL] [YOUR_CITY]
site:linkedin.com/jobs "[YOUR_KEY_SKILL]" Norway
site:arbeidplassen.nav.no [YOUR_KEY_SKILL] [YOUR_CITY]
```

## Location Filter

When evaluating results, verify the job location is within reasonable commute distance from your home. Define acceptable areas:
- [YOUR_CITY] and surrounding areas
- [ACCEPTABLE_AREA_1]
- [ACCEPTABLE_AREA_2]
- [BORDERLINE_AREA] (borderline - ~X min by transit)
- [TOO_FAR_AREA] (too far)

## Date Filter

Only include jobs posted within the last 14 days, or with an application deadline that has not yet passed. If a posting date cannot be determined, include it but flag as "date unknown".

## Adapting Queries

If the user specifies a focus area, select queries from the matching category and also generate 2-3 custom queries for that focus. For example:
- "/scrape [focus_area]" -> relevant category queries + custom focus-specific queries