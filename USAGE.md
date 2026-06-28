# Usage Guide

## Prerequisites
- Python 3.10+
- DeepSeek API key (stored in `.env` file)
- LaTeX distribution with `lualatex` and `xelatex` (e.g., TeX Live, MiKTeX)
- Python packages: `openai`, `pypdf`, `python-dotenv`

## Quick Start
1. **Fork & clone**  
   ```bash
   gh repo fork MadsLorentzen/ai-job-search --clone
   cd ai-job-search
   ```
2. **Set API key**  
   ```bash
   cp .env.example .env
   # Edit .env and paste your DeepSeek API key
   ```
3. **Install dependencies**  
   ```bash
   pip install -r requirements.txt
   ```
4. **Run the agent**  
   ```bash
   python main.py
   ```
5. **Onboard your profile** – at the prompt type `/setup` and follow the wizard (documents folder, single CV import, or interview mode).

## Core Commands
| Command | Description |
|---------|-------------|
| `/setup` | Profile onboarding – three paths (documents folder, single CV import, interview mode). |
| `/scrape` | Search Norwegian job portals (`finn.no`, `jobbnorge.no`, `nav.arbeidplassen.no`) for matches. |
| `/apply <url>` | Apply to a job posting – parses, evaluates fit, drafts CV + cover letter, reviewer loop, PDF compilation. |
| `/expand` | Enrich profile from online sources (GitHub, portfolio, Google Scholar, etc.). |
| `/upskill [url]` | Analyze skill gaps and generate a learning plan with resources. |
| `/reset [scope]` | Wipe profile data or documents (`profile`, `documents`, `all`). |
| `/help` | Show available commands. |
| `/exit` | Exit the agent. |

## Detailed Workflow

### 1. Setup (`/setup`)
- **Path A** – Documents folder (recommended if you have CV, LinkedIn export, diplomas, references).  
- **Path B** – Single CV import (paste or attach a CV).  
- **Path C** – Interview mode (answer structured questions).  

The wizard collects identity, education, experience, skills, behavioral traits, career goals, and job‑search preferences, then writes the following files:

- `CANDIDATE.md`
- `.agent/skills/job-application-assistant/01‑candidate-profile.md`
- `.agent/skills/job-application-assistant/02‑behavioral-profile.md`
- `.agent/skills/job-application-assistant/03‑writing-style.md`
- `.agent/skills/job-application-assistant/04‑job-evaluation.md`
- `.agent/skills/job-application-assistant/05‑cv-templates.md`
- `.agent/skills/job-application-assistant/06‑cover-letter-templates.md`
- `.agent/skills/job-application-assistant/07‑interview-prep.md`
- `cv/main_example.tex`
- `.agent/skills/job-scraper/search-queries.md`

### 2. Search (`/scrape`)
Runs a curl‑based scraper against the supported Norwegian portals, deduplicates results, scores each posting against your profile, and presents a ranked list.

### 3. Apply (`/apply <url>`)
1. **Parse** the posting (URL or raw text).  
2. **Evaluate fit** using the skill‑match model.  
3. **Draft** a tailored CV and cover letter in LaTeX.  
4. **Reviewer** – a second DeepSeek agent researches the company and critiques the drafts.  
5. **Revise** based on feedback.  
6. **Compile** PDFs (`lualatex` for CV, `xelatex` for cover letter) and perform layout checks.  
7. **Present** the final PDFs with a verification checklist.

### 4. Advanced Usage
- **Partial updates**: ` /setup --section <section>` (e.g., `skills`, `experience`, `search`).  
- **Salary benchmarking**: place `salary_data.json` in the repo root (see `tools/README_SALARY_TOOL.md`).  
- **Reset**: ` /reset profile`, ` /reset documents`, or ` /reset all`.

## Troubleshooting
- **`DEEPSEEK_API_KEY not set`** – create your `.env` file as shown in the quick‑start.
- **LaTeX compilation errors** – ensure `lualatex` and `xelatex` are installed and the `moderncv` package is available.  
- **Missing fonts** – the cover‑letter class expects Lato and Raleway fonts in `cover_letters/OpenFonts/fonts/`.  
- **Job search fails** – verify `curl` is installed and you have network access.

For full details, see:
- `README.md` – project overview.  
- `SETUP.md` – step‑by‑step installation.  
- `.agent/commands/*.md` – command‑specific documentation.

---  

*ponytail: added concise usage guide as a new top‑level file; no code changes required.*  

<task_progress>
- [x] Analyze project structure
- [x] Add documentation and usage guide
</task_progress>
</write_to_file>