# Setup Guide

Step-by-step instructions for getting the AI Job Search framework running with DeepSeek.

## 1. Prerequisites

### Python

Python 3.10+ is required. Check with:

```bash
python --version
```

### DeepSeek API key

You'll need a DeepSeek API key. Get one from [DeepSeek Platform](https://platform.deepseek.com/). Then store it in a `.env` file:

```bash
cp .env.example .env
# Edit .env and paste your key
```

The app loads it automatically via `python-dotenv` on startup.

### pip dependencies

Install the required Python packages:

```bash
pip install -r requirements.txt
```

### LaTeX (for compiling CVs and cover letters)

Install a LaTeX distribution to compile the generated `.tex` files to PDF:

- **Windows:** [MiKTeX](https://miktex.org/download)
- **macOS:** [MacTeX](https://tug.org/mactex/)
- **Linux:** `sudo apt install texlive-full` or `sudo dnf install texlive-scheme-full`

The CV compiles with `lualatex` (pdflatex often fails on modern MiKTeX installs with `fontawesome5` font-expansion errors). The cover letter compiles with `xelatex` because `cover.cls` requires `fontspec` for its custom Lato/Raleway fonts.

### Playwright (no longer needed)

The scraper previously used Playwright + headless Chromium (~300MB). It has been replaced with curl (stdlib).
If you already have Playwright installed, you can remove it:

```bash
pip uninstall playwright && npx playwright uninstall
```

## 2. Fork and clone

```bash
gh repo fork MadsLorentzen/ai-job-search --clone
cd ai-job-search
```

Or manually: fork on GitHub, then clone your fork.

## 3. Run the agent

Start the agent:

```bash
python main.py
```

You'll see a prompt where you can type slash commands. Start with the setup command:

```
/setup
```

The agent will offer three paths, auto-detecting which materials you have:

- **Path A (documents folder — recommended):** Point `/setup` at your `documents/` folder (CV PDF, LinkedIn export, diplomas, reference letters, past applications). The agent reads everything and populates your profile. Idempotent and safe to re-run as you add more material; see `documents/README.md` for the folder layout.
- **Path B (CV import):** Share your existing CV (paste the text or provide a file path). The agent extracts your information and asks follow-up questions for anything missing.
- **Path C (interview):** Answer structured interview questions section by section.

All paths produce the same result: fully populated profile files.

### What gets populated

| File | Content |
|------|---------|
| `CANDIDATE.md` | Your full candidate profile |
| `.agent/skills/job-application-assistant/01-candidate-profile.md` | Structured education, experience, skills |
| `.agent/skills/job-application-assistant/02-behavioral-profile.md` | Behavioral assessment |
| `.agent/skills/job-application-assistant/03-writing-style.md` | Writing style guide |
| `.agent/skills/job-application-assistant/04-job-evaluation.md` | Personalized skill match areas and career goals |
| `.agent/skills/job-application-assistant/05-cv-templates.md` | Profile statement templates for your background |
| `.agent/skills/job-application-assistant/06-cover-letter-templates.md` | Cover letter templates |
| `.agent/skills/job-application-assistant/07-interview-prep.md` | STAR examples from your experience |
| `.agent/skills/job-scraper/search-queries.md` | Job search queries for `/scrape` |
| `cv/main_example.tex` | Your LaTeX CV with actual details |

### Re-running setup

You can update specific sections later:

```
/setup --section skills
/setup --section experience
/setup --section search
```

The `--section search` option is especially useful as your priorities evolve. It re-runs the search configuration interview and suggests role types you may not have considered based on your full profile.

## 4. Optional: Set up salary benchmarking

If you have salary data (from a union, salary survey, Glassdoor, or personal research):

1. **Option A:** Create `salary_data.json` manually in the repo root (see `tools/README_SALARY_TOOL.md` for the format)
2. **Option B:** Convert from Excel:
   ```bash
   pip install openpyxl
   python tools/convert_salary_excel.py path/to/salary-data.xlsx --source "My Salary Data 2025"
   ```

This creates `salary_data.json` which the `/apply` workflow uses for salary benchmarking. If you skip this step, salary lookup is simply omitted.

## 5. Test the workflow

Find a job posting you're interested in, then:

```
/apply https://www.finn.no/job/fulltime/1234567
```

Or paste the job description directly:

```
/apply [paste job posting text here]
```

The agent will:
1. **Parse** the job posting (URL or text)
2. **Evaluate fit** against your profile (skills, experience, culture, location, career alignment)
3. **Draft** a tailored CV and cover letter in LaTeX
4. **Spawn a reviewer agent** that researches the company and critiques the drafts
5. **Revise** based on the reviewer's feedback
6. **Compile and inspect** both PDFs: lualatex for the CV, xelatex for the cover letter. The agent reads the rendered pages and iterates on the LaTeX until the CV is exactly 2 pages with no orphaned entry titles, and the cover letter is exactly 1 page with the signature visible and fonts consistent.
7. **Present** the final output with a verification checklist

## 6. Compile your documents

After `/apply` creates the LaTeX files:

```bash
# Compile CV
cd cv && lualatex main_<company>.tex && cd ..

# Compile cover letter
cd cover_letters && xelatex cover_<company>_<role>.tex && cd ..
```

## Other commands

- **`/scrape`** — Search job portals for positions matching your profile
- **`/expand`** — Enrich your profile by scanning documents and linked online presence (GitHub, portfolio)
- **`/upskill [url]`** — Analyze skill gaps and generate a prioritized learning plan
- **`/reset [scope]`** — Wipe profile data or documents folder
- **`/help`** — Show available commands
- **`/exit`** — Exit the agent

## Troubleshooting

### "DEEPSEEK_API_KEY not set"
Make sure your `.env` file exists and contains your key:

```bash
cp .env.example .env
# Edit .env and paste your key
```

### "salary_data.json not found"
This is expected if you haven't set up salary benchmarking. The `/apply` workflow skips this step automatically.

### Job search not working
Make sure `curl` is installed and you have network access. The scraper fetches Norwegian job portals (finn.no, jobbnorge.no, nav.arbeidplassen.no) directly via HTTP.

### LaTeX compilation errors
- CV: uses `lualatex` (pdflatex often fails on modern MiKTeX with `fontawesome5` font-expansion errors; lualatex handles the same sources cleanly)
- Cover letter: uses `xelatex` (for custom fonts in `OpenFonts/fonts/`)
- Make sure your LaTeX distribution includes the `moderncv` package

### Fonts not found in cover letter
The cover letter template expects fonts in `cover_letters/OpenFonts/fonts/`. Make sure this directory exists and contains the Lato and Raleway font files.