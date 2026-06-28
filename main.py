#!/usr/bin/env python3
"""
DeepSeek Job Search Agent
=========================
A full-featured job application assistant powered by DeepSeek (OpenAI-compatible API),
implementing all slash commands from the original Claude Code workflow.

Commands:
  /setup          - Profile onboarding (documents, CV import, or interview)
  /apply <url>    - Full drafter-reviewer job application workflow
  /scrape         - Search job portals for matching positions
  /expand         - Competency expansion from documents and online presence
  /upskill [url]  - Skill gap analysis and learning plan
  /reset [scope]  - Reset profile data (profile, documents, or all)
  /help           - Show available commands
  /exit           - Exit the agent
"""

import os
import re
import sys
import json
import shlex
import inspect
import glob as glob_module
import subprocess
from typing import Optional
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Try importing pypdf for PDF reading
try:
    import pypdf
except ImportError:
    print(
        "Warning: 'pypdf' library is missing. PDF reading will be limited. Install: pip install pypdf"
    )

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.join(REPO_ROOT, ".agent", "skills", "job-application-assistant")
COMMANDS_DIR = os.path.join(REPO_ROOT, ".agent", "commands")
SCRAPER_DIR = os.path.join(REPO_ROOT, ".agent", "skills", "job-scraper")
UPSKILL_DIR = os.path.join(REPO_ROOT, ".agent", "skills", "upskill")
# ponytail: DeepSeek API is OpenAI-compatible — swap SDK, endpoint, model, done.
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash")
# ponytail: V4 defaults to thinking mode; disable for fast agentic tool-calling.
# Set DEEPSEEK_THINKING=1 in .env to enable chain-of-thought (slower but more deliberate).
DEEPSEEK_THINKING = os.environ.get("DEEPSEEK_THINKING", "0") == "1"
DEEPSEEK_REASONING_EFFORT = os.environ.get("DEEPSEEK_REASONING_EFFORT", "high")

# ---------------------------------------------------------------------------
# 1. Local Tool Definitions
# ---------------------------------------------------------------------------


def list_directory_files(directory_path: str = "documents") -> str:
    """Recursively lists all files in a specified directory."""
    safe_path = os.path.normpath(os.path.join(REPO_ROOT, directory_path))
    if not safe_path.startswith(REPO_ROOT):
        return "Error: Access denied. You can only view files within the workspace."
    if not os.path.exists(safe_path):
        return f"Error: Directory '{directory_path}' does not exist."
    file_list = []
    for root, _, files in os.walk(safe_path):
        for file in files:
            relative_path = os.path.relpath(os.path.join(root, file), REPO_ROOT)
            file_list.append(relative_path)
    if not file_list:
        return f"No files found in '{directory_path}'."
    return "Found files:\n" + "\n".join(file_list)


def read_workspace_file(path: str) -> str:
    """Reads the content of a file within the workspace. Supports PDF and text files."""
    safe_path = os.path.normpath(os.path.join(REPO_ROOT, path))
    if not safe_path.startswith(REPO_ROOT):
        return "Error: Access denied. You can only read files within the workspace."
    if not os.path.exists(safe_path):
        return f"Error: File '{path}' not found."
    if safe_path.lower().endswith(".pdf"):
        try:
            reader = pypdf.PdfReader(safe_path)
            extracted_text = []
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                extracted_text.append(f"--- Page {i+1} ---\n{page_text}")
            return "\n".join(extracted_text)
        except Exception as e:
            return f"Error parsing PDF '{path}': {str(e)}"
    try:
        with open(safe_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception as e:
        return f"Error reading text file '{path}': {str(e)}"


def write_workspace_file(path: str, content: str) -> str:
    """Writes or overwrites a file in the workspace with the specified content."""
    safe_path = os.path.normpath(os.path.join(REPO_ROOT, path))
    if not safe_path.startswith(REPO_ROOT):
        return "Error: Access denied. You can only write files within the workspace."
    try:
        os.makedirs(os.path.dirname(safe_path), exist_ok=True)
        with open(safe_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote content to '{path}'."
    except Exception as e:
        return f"Error writing file '{path}': {str(e)}"


def execute_shell_command(command: str) -> str:
    """Executes a shell command in the local environment (max 120s timeout)."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        output = []
        if result.stdout:
            output.append(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            output.append(f"STDERR:\n{result.stderr}")
        return (
            "\n".join(output)
            if output
            else "Command executed successfully with no output."
        )
    except subprocess.TimeoutExpired:
        return "Error: Command execution timed out after 120 seconds."
    except Exception as e:
        return f"Error executing command: {str(e)}"


def glob_search(pattern: str) -> str:
    """Glob search for files matching a pattern relative to the workspace root."""
    safe_path = os.path.join(REPO_ROOT, pattern)
    matches = glob_module.glob(safe_path, recursive=True)
    if not matches:
        return f"No files matching '{pattern}'."
    relative = [os.path.relpath(m, REPO_ROOT) for m in matches]
    return "Found files:\n" + "\n".join(relative)


def grep_search(pattern: str, file_pattern: str = "*") -> str:
    """Search for a pattern in files matching a glob. Uses grep command."""
    cmd = f"grep -rn {shlex.quote(pattern)} --include={shlex.quote(file_pattern)} . 2>/dev/null | head -100"
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30, check=False
        )
        if result.stdout:
            return result.stdout.strip()
        return f"No matches for '{pattern}' in '{file_pattern}'."
    except Exception as e:
        return f"Error searching: {str(e)}"


def append_to_csv(filepath: str, row_data: str) -> str:
    """Appends a row to a CSV file. row_data should be comma-separated values."""
    safe_path = os.path.normpath(os.path.join(REPO_ROOT, filepath))
    if not safe_path.startswith(REPO_ROOT):
        return "Error: Access denied."
    try:
        os.makedirs(os.path.dirname(safe_path), exist_ok=True)
        with open(safe_path, "a", newline="", encoding="utf-8") as f:
            f.write(row_data + "\n")
        return f"Appended to '{filepath}'."
    except Exception as e:
        return f"Error writing CSV: {str(e)}"


def web_fetch(url: str) -> str:
    """Fetches a URL and returns the text content. Uses curl."""
    try:
        result = subprocess.run(
            [
                "curl",
                "-sL",
                "--max-time",
                "30",
                "-A",
                "Mozilla/5.0 (compatible; AgentJobSearch/1.0)",
                url,
            ],
            capture_output=True,
            text=True,
            timeout=35,
            check=False,
        )
        if result.returncode == 0 and result.stdout:
            # Basic HTML to text conversion
            text = result.stdout
            # Remove scripts and styles
            text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL)
            text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
            # Replace common block tags with newlines
            text = re.sub(
                r"</?(div|p|br|li|h[1-6]|tr|section|article)[^>]*>", "\n", text
            )
            # Remove remaining HTML tags
            text = re.sub(r"<[^>]+>", "", text)
            # Decode HTML entities
            html_entities = {
                "&": "&",
                "<": "<",
                ">": ">",
                '"': '"',
                "&#39;": "'",
                "&#x27;": "'",
                "&#x2F;": "/",
                "&#xa0;": " ",
                "&nbsp;": " ",
            }
            for entity, char in html_entities.items():
                text = text.replace(entity, char)
            # Collapse excessive whitespace
            text = re.sub(r"\n{3,}", "\n\n", text)
            text = text.strip()
            if len(text) > 50000:
                text = text[:50000] + "\n\n... [TRUNCATED]"
            return text if text else f"Fetched but no readable content from {url}"
        return f"Error fetching {url}: HTTP {result.returncode}"
    except subprocess.TimeoutExpired:
        return f"Error: Timed out fetching {url}"
    except Exception as e:
        return f"Error fetching {url}: {str(e)}"


# ---------------------------------------------------------------------------
# 2. OpenAI-Compatible Chat Session (DeepSeek)
# ---------------------------------------------------------------------------

# Registry: function_name -> callable (populated by _register_tools)
_TOOL_FUNCTIONS = {}


def _make_tool_schema(func) -> dict:
    """Auto-generate OpenAI tool schema from a Python function's signature and docstring."""
    sig = inspect.signature(func)
    properties = {}
    required = []
    for name, param in sig.parameters.items():
        prop = {"type": "string"}  # ponytail: all our tools use str params
        if param.default is inspect.Parameter.empty:
            required.append(name)
        else:
            prop["description"] = f"Default: {param.default}"
        properties[name] = prop

    doc_first_line = (func.__doc__ or "").strip().split("\n")[0]
    return {
        "type": "function",
        "function": {
            "name": func.__name__,
            "description": doc_first_line,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }


def _register_tools(*funcs) -> list:
    """Register tool functions and return their OpenAI-compatible schema list."""
    schemas = []
    for f in funcs:
        _TOOL_FUNCTIONS[f.__name__] = f
        schemas.append(_make_tool_schema(f))
    return schemas


class ChatSession:
    """OpenAI-compatible chat session with automatic tool-call loop."""

    def __init__(
        self,
        system_prompt: str,
        model: str,
        tools: Optional[list] = None,
        thinking: bool = False,
        reasoning_effort: str = "high",
    ):
        self.client = OpenAI(
            api_key=os.environ.get("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com",
        )
        self.model = model
        self.thinking = thinking
        self.reasoning_effort = reasoning_effort
        self.messages = [{"role": "system", "content": system_prompt}]
        self.tool_schemas = tools or []
        self.tool_map = {
            s["function"]["name"]: _TOOL_FUNCTIONS[s["function"]["name"]]
            for s in self.tool_schemas
        }

    def send_message(self, user_text: str) -> str:
        """Send a message and return the text response, executing tool calls as needed."""
        self.messages.append({"role": "user", "content": user_text})

        while True:
            kwargs = {"model": self.model, "messages": self.messages}
            if self.tool_schemas:
                kwargs["tools"] = self.tool_schemas
                # ponytail: V4 ignores temperature in thinking mode; only set in non-thinking.
                if not self.thinking:
                    kwargs["temperature"] = 0.2
            if self.thinking:
                kwargs["reasoning_effort"] = self.reasoning_effort
                kwargs["extra_body"] = {"thinking": {"type": "enabled"}}

            response = self.client.chat.completions.create(**kwargs)
            choice = response.choices[0]

            # Stop — return the final text
            if choice.finish_reason == "stop":
                self.messages.append(choice.message.model_dump(exclude_none=True))
                return choice.message.content or ""

            # Tool calls — execute them and loop
            if choice.finish_reason == "tool_calls":
                self.messages.append(choice.message.model_dump(exclude_none=True))
                for tc in choice.message.tool_calls:
                    fn_name = tc.function.name
                    try:
                        args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        args = {}
                    fn = self.tool_map.get(fn_name)
                    if fn:
                        result = fn(**args)
                    else:
                        result = f"Error: unknown tool '{fn_name}'"
                    self.messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": str(result),
                        }
                    )
                continue

            # Unknown finish_reason — return whatever text we got
            return choice.message.content or ""


def create_chat_session(
    system_prompt: str, tools_list: Optional[list] = None
) -> ChatSession:
    """Creates a ChatSession with the given system prompt and tool functions."""
    tool_schemas = _register_tools(*tools_list) if tools_list else []
    return ChatSession(
        system_prompt,
        DEEPSEEK_MODEL,
        tool_schemas,
        thinking=DEEPSEEK_THINKING,
        reasoning_effort=DEEPSEEK_REASONING_EFFORT,
    )


# ---------------------------------------------------------------------------
# 3. Skill File Loaders
# ---------------------------------------------------------------------------


def load_skill_file(filename: str) -> str:
    """Loads a skill file from the job-application-assistant skill directory."""
    path = os.path.join(SKILL_DIR, filename)
    if not os.path.exists(path):
        return f"<!-- {filename} not found -->"
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return f"<!-- Error reading {filename} -->"


def load_all_skill_files() -> dict:
    """Loads all skill files into a dict keyed by short name."""
    files = {
        "candidate_profile": "01-candidate-profile.md",
        "behavioral_profile": "02-behavioral-profile.md",
        "writing_style": "03-writing-style.md",
        "job_evaluation": "04-job-evaluation.md",
        "cv_templates": "05-cv-templates.md",
        "cover_letter_templates": "06-cover-letter-templates.md",
        "interview_prep": "07-interview-prep.md",
        "skill_main": "SKILL.md",
    }
    return {key: load_skill_file(fname) for key, fname in files.items()}


def load_search_queries() -> str:
    """Loads search queries from the job-scraper skill directory."""
    path = os.path.join(SCRAPER_DIR, "search-queries.md")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


# ---------------------------------------------------------------------------
# 4. Command Implementations
# ---------------------------------------------------------------------------


def cmd_help() -> str:
    """Show available commands."""
    return """
## Available Commands

| Command | Description |
|---------|-------------|
| `/setup` | Profile onboarding - 3 paths: documents folder, CV import, or interview |
| `/apply <url>` or `/apply <text>` | Full drafter-reviewer job application workflow |
| `/scrape` | Search job portals for matching positions |
| `/scrape <focus>` | Search with a specific focus (e.g. "/scrape data science") |
| `/expand` | Enrich your profile from documents and online presence |
| `/upskill` | Aggregate skill gap analysis from tracked jobs |
| `/upskill <url>` | Targeted skill gap analysis for a specific job |
| `/reset profile` | Clear profile data from skill files |
| `/reset documents` | Delete files from the documents/ folder |
| `/reset all` | Both of the above |
| `/help` | Show this help message |
| `/exit` | Exit the agent |

**How to use:** Just type any command above. For `/apply`, paste a job URL or the full
job description text after the command. For `/scrape`, optionally add a focus area.
"""


def cmd_setup(args: str) -> str:
    """Run the profile onboarding workflow as an interactive multi-turn session."""
    skills = load_all_skill_files()

    system_prompt = f"""You are a career onboarding specialist helping the user build their professional profile.
Your goal is to collect the user's professional information and populate all profile files.

You have access to tools: list files, read files, write files, execute shell commands, glob search, grep search.

### Context - Skill Files Ready to Populate:
{json.dumps({k: len(v.splitlines()) for k, v in skills.items()}, indent=2)}

### Current CANDIDATE.md state:
{read_workspace_file("CANDIDATE.md")[:2000] if os.path.exists(os.path.join(REPO_ROOT, "CANDIDATE.md")) else "No CANDIDATE.md"}

### Workflow to follow:
1. First, check if `documents/` folder has files. If yes, offer Path A (read documents), Path B (CV import), Path C (interview).
2. Follow the selected path to collect data.
3. Populate ALL skill files (01-candidate-profile.md, 02-behavioral-profile.md, 03-writing-style.md, 04-job-evaluation.md, 05-cv-templates.md, 06-cover-letter-templates.md, 07-interview-prep.md).
4. Update CANDIDATE.md with the user's information.
5. Generate cv/main_example.tex with the user's data.
6. Generate search queries.

IMPORTANT RULES:
- Be conversational and guide the user step by step
- Read existing files before writing to avoid overwriting data
- Present changes for confirmation before writing
- After the session, write files only with user confirmation
- When writing markdown files, use the Write tool
- When writing LaTeX, use the Write tool
- Work through ALL 7 profile files before finishing setup
- After setup is complete, summarize what was created and prompt the user to type /done
"""

    tools_setup = [
        list_directory_files,
        read_workspace_file,
        write_workspace_file,
        execute_shell_command,
        glob_search,
        grep_search,
    ]

    doc_status = list_directory_files("documents")
    user_prompt = f"""
Check if documents/ folder has content and guide the user through setup.

Documents folder status: {doc_status}

Ask the user which path they'd like:
- **Path A**: Read my documents folder (recommended if documents/ has content)
- **Path B**: Single CV import (paste a CV)
- **Path C**: Interview mode (structured questions)

Wait for their choice before proceeding.
"""

    session = create_chat_session(system_prompt, tools_setup)
    response = session.send_message(user_prompt)
    print(f"\n[Setup] > {response}\n", flush=True)

    print(
        "--- Setup interactive session started ---\n"
        "  Type your responses to continue the conversation.\n"
        "  Type  /done   when setup is complete.\n"
        "  Type  /cancel to abort setup.\n",
        flush=True,
    )

    while True:
        try:
            user_input = input("You (setup) > ")
            stripped = user_input.strip()

            if stripped == "/done":
                print(
                    "\n[Setup] Setup session complete. Returning to main session.\n",
                    flush=True,
                )
                break
            if stripped == "/cancel":
                print(
                    "\n[Setup] Setup cancelled. Returning to main session.\n",
                    flush=True,
                )
                break
            if not stripped:
                continue

            print("Thinking...", flush=True)
            response = session.send_message(user_input)
            print(f"\n[Setup] > {response}\n", flush=True)

        except KeyboardInterrupt:
            print("\n[Setup] Interrupted. Returning to main session.", flush=True)
            break
        except Exception as e:
            print(f"\n[Setup] Error: {e}\n", flush=True)
            break

    return ""  # All output was printed during the interactive loop


def cmd_apply(args: str) -> str:
    """
    Full drafter-reviewer job application workflow.
    Implemented as a multi-turn agent conversation with reviewer phase.
    """
    if not args.strip():
        return "**Usage:** `/apply <job-posting-url>` or `/apply <paste full job posting text>`\n\nPlease provide a job posting URL or paste the full job description."

    skills = load_all_skill_files()
    profile_01 = skills.get("candidate_profile", "")

    system_prompt_eval = f"""You are a job application drafter. Evaluate the job posting against the candidate's profile.

### Candidate Profile:
{profile_01[:3000]}

### Evaluation Framework:
{skills.get('job_evaluation', '')[:2000]}

### Your Tools:
- web_fetch(url) - Fetch a URL's content
- read_workspace_file(path) - Read any file
- execute_shell_command(cmd) - Run shell commands
- write_workspace_file(path, content) - Write files

### Workflow Step 1 - Evaluate Fit:
1. If the argument is a URL, use web_fetch to retrieve the job posting.
2. Analyze against the candidate profile.
3. Present: skills match, experience match, behavioral/culture match, overall fit score.
4. Ask the user if they want to proceed with drafting.
5. **If yes**, continue to Step 2 (draft CV + cover letter).
6. **If no**, stop.

For the salary lookup, run: python3 salary_lookup.py "Company Name" --json
If it fails, skip salary benchmarking.

After user approves, write both draft files to disk:
- cv/main_<company>.tex (English, moderncv/banking format, 2 pages)
- cover_letters/cover_<company>_<role>.tex (match posting language, cover.cls, ~1 page)
"""

    tools_apply = [
        list_directory_files,
        read_workspace_file,
        write_workspace_file,
        execute_shell_command,
        web_fetch,
        glob_search,
    ]

    job_arg = args.strip()

    session = create_chat_session(system_prompt_eval, tools_apply)
    # ponytail: skill files 01 (candidate) and 04 (evaluation) are already in the system prompt,
    # no need for the model to re-read them via tool use. Only instruct it to read files not in context.
    return session.send_message(
        f"Evaluate this job posting and draft the application:\n\n{job_arg}\n\n"
        f"First, check if this is a URL (fetch it) or pasted text. "
        f"Read the skill files: 03-writing-style.md, 05-cv-templates.md, 06-cover-letter-templates.md. "
        f"Then present the fit evaluation."
    )


def cmd_scrape(args: str) -> str:
    """
    Search job portals for matching positions using Playwright-based multi-site scraper.
    """
    search_queries = load_search_queries()
    skills = load_all_skill_files()
    profile_01 = skills.get("candidate_profile", "")

    system_prompt = f"""You are a job search assistant. Search for jobs matching the candidate's profile.

### Candidate Profile Summary:
{profile_01[:2000]}

### Search Queries Configuration:
{search_queries[:2000] if search_queries else "No search queries configured yet. Run /setup first."}

### Your Tools:
- web_fetch(url) - Fetch a URL's content
- read_workspace_file(path) - Read any file
- write_workspace_file(path, content) - Write files
- execute_shell_command(cmd) - Run shell commands (Use this to run the multi-site scraper)
- glob_search(pattern) - Find files
- grep_search(pattern, file_pattern) - Search file contents
- append_to_csv(filepath, row_data) - Append to CSV

### How to run the multi-site scraper:
Use execute_shell_command to run. Supported sites: finn.no, arbeidsplassen.nav.no, jobbnorge.no.

    # Scrape all sites at once (recommended):
    python3 job_scraper/scraper.py --query "<search terms>" --location "<city>" --site all --pages 2

    # Or scrape individual sites:
    python3 job_scraper/scraper.py --query "<search terms>" --location "<city>" --site finn --pages 2
    python3 job_scraper/scraper.py --query "<search terms>" --location "<city>" --site nav --pages 2
    python3 job_scraper/scraper.py --query "<search terms>" --site jobbnorge --pages 2

The --site flag accepts: finn, nav, arbeidsplassen, jobbnorge, all (default: all)

This will return JSON with job listings including: title, company, location, date, url, source.
The scraper uses curl for all sites (no Playwright dependency). LinkedIn is excluded from
scraping because it blocks unauthenticated search; individual LinkedIn job detail pages
still work via /apply's web_fetch function.

### Deduplication files:
- `job_scraper/seen_jobs.json` — All previously seen jobs (keyed by URL)
- `job_search_tracker.csv` — Jobs you've already applied to (columns: date,company,sector,role,role_type,channel,status,contact_person,fit_rating,notes,cv_file,cover_letter_file,source)

### Workflow:
1. Read `job_scraper/seen_jobs.json` (create `{{"seen": {{}}}}` if missing)
2. Read `job_search_tracker.csv` for previously applied jobs
3. Run the multi-site scraper with --site all for the focus area/location
4. Parse the JSON output from the scraper (includes results from all sites)
5. Deduplicate against seen_jobs.json and tracker
6. Apply quick fit assessment (high/medium/low) based on candidate profile
7. Update seen_jobs.json with ALL scraped results:
   - Merge new jobs into the `seen` dict
   - Write back the full updated seen_jobs.json using write_workspace_file
8. Present only the NEW matches in a table sorted by fit (high first), grouped by source site
9. For each new job, include: title, company, location, date, URL, source site, fit assessment
10. If no results from --site all, try scraping individual sites to catch failures

IMPORTANT: Only present jobs found via actual scraper output. Never fabricate job postings.
"""
    tools_scrape = [
        read_workspace_file,
        write_workspace_file,
        execute_shell_command,
        web_fetch,
        glob_search,
        grep_search,
        append_to_csv,
    ]

    focus = args.strip() if args.strip() else "all categories"
    session = create_chat_session(system_prompt, tools_scrape)
    return session.send_message(
        f"Search for jobs with focus: {focus}. "
        f"First read seen_jobs.json and the tracker, then run the multi-site scraper using "
        f"execute_shell_command with --site all and the appropriate query and location. "
        f"Parse the results from all sites. Deduplicate, assess fit, update seen_jobs.json, "
        f"and present results grouped by source site."
    )


def cmd_expand(args: str) -> str:
    """
    Enrich the candidate profile by discovering competencies from documents and online presence.
    """
    skills = load_all_skill_files()
    profile_01 = skills.get("candidate_profile", "")

    system_prompt = f"""You are a competency discovery specialist. Enrich the candidate's profile by finding
hidden skills and competencies in their documents and online presence.

### Current Profile:
{profile_01[:2000]}

### Your Tools:
- read_workspace_file(path) - Read any file
- write_workspace_file(path, content) - Write files
- web_fetch(url) - Fetch a URL's content for web enrichment
- execute_shell_command(cmd) - Run shell commands
- glob_search(pattern) - Find files
- grep_search(pattern, file_pattern) - Search file contents
- list_directory_files(path) - List files in a directory

### Workflow:
1. Scan documents/cv/, documents/linkedin/, documents/diplomas/, documents/references/
2. Read each document and extract experience items
3. Check profile for GitHub URL or other URLs -> fetch them
4. For each item, search web for skill implications
5. Build a competency map (deduplicated, removing what's already in profile)
6. Present grouped summary for user approval
7. Write confirmed additions to 01-candidate-profile.md and 02-behavioral-profile.md

IMPORTANT RULES:
- Additive only - never modify existing content, only append
- Source-traceable - every addition records where it came from
- User confirms before writing
- Label inferred behavioral additions for review
"""

    tools_expand = [
        list_directory_files,
        read_workspace_file,
        write_workspace_file,
        execute_shell_command,
        web_fetch,
        glob_search,
        grep_search,
    ]

    session = create_chat_session(system_prompt, tools_expand)
    return session.send_message(
        "Run the competency expansion workflow. "
        "First scan all document sources and online presence, "
        "then present findings for user approval."
    )


def cmd_upskill(args: str) -> str:
    """
    Analyze skill gaps and generate a prioritized learning plan.
    Aggregate mode (no args) or targeted mode (with URL).
    """
    skills = load_all_skill_files()
    profile_01 = skills.get("candidate_profile", "")

    system_prompt = f"""You are a skill gap analyst. Compare job requirements against the candidate's
profile and produce a prioritized learning plan.

### Candidate Profile:
{profile_01[:3000]}

### Your Tools:
- read_workspace_file(path) - Read any file
- write_workspace_file(path, content) - Write files
- web_fetch(url) - Fetch a URL's content
- execute_shell_command(cmd) - Run shell commands
- glob_search(pattern) - Find files
- grep_search(pattern, file_pattern) - Search file contents

### Workflow:
1. Detect mode: no args = aggregate (read job_search_tracker.csv), URL = targeted (fetch it)
2. Load candidate profile
3. Pass 1 - Hard skill diff: extract skills from jobs, diff against profile
4. Pass 2 - LLM synthesis: identify domain, soft, tooling, credential gaps
5. Build gap heatmap (Critical/High/Medium/Low)
6. Web-search learning resources for each critical/high gap
7. Build learning plan with study directions and time estimates
8. Suggest study order
9. Save report to upskill/report-YYYY-MM-DD.md

IMPORTANT: Never fabricate resources. Only cite resources found via web_fetch.
"""

    tools_upskill = [
        read_workspace_file,
        write_workspace_file,
        execute_shell_command,
        web_fetch,
        glob_search,
        grep_search,
    ]

    arg = args.strip()
    if arg and (arg.startswith("http://") or arg.startswith("https://")):
        prompt = f"Run targeted upskill analysis for: {arg}"
    else:
        prompt = "Run aggregate upskill analysis from job_search_tracker.csv"

    session = create_chat_session(system_prompt, tools_upskill)
    return session.send_message(prompt)


def cmd_reset(args: str) -> str:
    """
    Reset profile data - profile, documents, or all.
    """
    scope = args.strip().lower() if args.strip() else ""
    valid_scopes = {"profile", "documents", "all"}

    if not scope or scope not in valid_scopes:
        return """**Usage:** `/reset <scope>`

Available scopes:
- **`profile`** — Clears candidate data from skill files. Framework structure preserved.
- **`documents`** — Deletes files from the `documents/` folder. Structure and README preserved.
- **`all`** — Both of the above.

**This is destructive.** You will be asked to confirm with `RESET` before anything is changed.

Example: `/reset profile`
"""

    # Build a description of what will be cleared
    description_parts = [f"## Reset Scope: {scope}\n"]

    if scope in ("profile", "all"):
        description_parts.append("### Profile files to clear:")
        for fname in ["01-candidate-profile.md", "02-behavioral-profile.md"]:
            path = os.path.join(SKILL_DIR, fname)
            if os.path.exists(path):
                size = os.path.getsize(path)
                status = (
                    f"has content ({size} bytes)" if size > 100 else "already empty"
                )
                description_parts.append(f"- {fname} — {status}")
            else:
                description_parts.append(f"- {fname} — not found")
        description_parts.append(
            "- 05-cv-templates.md — profile statements section will be cleared"
        )
        description_parts.append(
            "- 07-interview-prep.md — STAR examples section will be cleared"
        )
        description_parts.append("")

    if scope in ("documents", "all"):
        description_parts.append("### Document folders to clear:")
        for subdir in ["cv", "linkedin", "diplomas", "references", "applications"]:
            dirpath = os.path.join(REPO_ROOT, "documents", subdir)
            items = []
            if os.path.exists(dirpath):
                items = [f for f in os.listdir(dirpath)]
            if items:
                description_parts.append(
                    f"- documents/{subdir}/ — {len(items)} item(s)"
                )
            else:
                description_parts.append(f"- documents/{subdir}/ — empty")
        description_parts.append("documents/README.md — NOT deleted (preserved)")
        description_parts.append("")

    description_parts.append(
        "**This cannot be undone.**\n\n"
        "Type **`RESET`** (all caps) to confirm, or anything else to cancel."
    )

    return "\n".join(description_parts)


def execute_reset(scope: str) -> str:
    """Execute the actual reset after confirmation."""
    results = []

    if scope in ("profile", "all"):
        blank_candidate = """# Candidate Profile

<!-- Run /setup to populate this file -->

## Identity

## Education

## Professional Experience

## Independent Projects

## Technical Skills

## Publications

## Awards

## References
"""
        write_workspace_file(
            ".agent/skills/job-application-assistant/01-candidate-profile.md",
            blank_candidate,
        )
        results.append("Cleared 01-candidate-profile.md")

        blank_behavioral = """# Behavioral Profile

<!-- Run /setup to populate this file -->

## Overview

## Strongest Behavioral Traits

## How I Work Best

## Growth Areas

## Mapping to Job Posting Language

## Management Style Preferences

## Using This in Applications
"""
        write_workspace_file(
            ".agent/skills/job-application-assistant/02-behavioral-profile.md",
            blank_behavioral,
        )
        results.append("Cleared 02-behavioral-profile.md")

        cv_templates_path = os.path.join(SKILL_DIR, "05-cv-templates.md")
        if os.path.exists(cv_templates_path):
            with open(cv_templates_path, "r") as f:
                content = f.read()
            content = re.sub(
                r"\*\*Profile statement templates:\*\*.*?(?=\n##|\Z)",
                "**Profile statement templates:**\n\n<!-- Run /setup to populate role-specific profile statements -->",
                content,
                flags=re.DOTALL,
            )
            with open(cv_templates_path, "w") as f:
                f.write(content)
            results.append("Cleared profile statements from 05-cv-templates.md")

        interview_path = os.path.join(SKILL_DIR, "07-interview-prep.md")
        if os.path.exists(interview_path):
            with open(interview_path, "r") as f:
                content = f.read()
            content = re.sub(
                r"## Ready-Made STAR Examples.*?(?=\n## |\Z)",
                "## Ready-Made STAR Examples\n\n<!-- Run /setup to populate STAR examples from your actual experience -->",
                content,
                flags=re.DOTALL,
            )
            content = re.sub(
                r"\n## STAR Candidates \(Complete Manually\).*?(?=\n## |\Z)",
                "",
                content,
                flags=re.DOTALL,
            )
            with open(interview_path, "w") as f:
                f.write(content)
            results.append("Cleared STAR examples from 07-interview-prep.md")

    if scope in ("documents", "all"):
        for subdir in ["cv", "linkedin", "diplomas", "references"]:
            dirpath = os.path.join(REPO_ROOT, "documents", subdir)
            if os.path.exists(dirpath):
                for fname in os.listdir(dirpath):
                    fpath = os.path.join(dirpath, fname)
                    if os.path.isfile(fpath):
                        os.remove(fpath)
                results.append(f"Cleared documents/{subdir}/")
        apps_dir = os.path.join(REPO_ROOT, "documents", "applications")
        if os.path.exists(apps_dir):
            for item in os.listdir(apps_dir):
                item_path = os.path.join(apps_dir, item)
                if os.path.isdir(item_path):
                    for root, dirs, files in os.walk(item_path, topdown=False):
                        for f in files:
                            os.remove(os.path.join(root, f))
                        for d in dirs:
                            os.rmdir(os.path.join(root, d))
                    os.rmdir(item_path)
            results.append("Cleared documents/applications/")

    if not results:
        return "Nothing was changed — no files to clear."

    return "## Reset Complete\n\n### Cleared:\n" + "\n".join(f"- {r}" for r in results)


# ---------------------------------------------------------------------------
# 5. Command Router
# ---------------------------------------------------------------------------

COMMAND_HANDLERS = {
    "/setup": cmd_setup,
    "/apply": cmd_apply,
    "/scrape": cmd_scrape,
    "/expand": cmd_expand,
    "/upskill": cmd_upskill,
    "/reset": cmd_reset,
    "/help": lambda args: cmd_help(),
}


def route_command(user_input: str) -> Optional[str]:
    """Routes a user command to the appropriate handler. Returns handler output or None."""
    stripped = user_input.strip()

    for cmd_prefix, handler in COMMAND_HANDLERS.items():
        if stripped.startswith(cmd_prefix):
            args = stripped[len(cmd_prefix) :].strip()
            result = handler(args)
            return result

    return None


# ---------------------------------------------------------------------------
# 6. Main Runner Loop
# ---------------------------------------------------------------------------


def load_system_prompt() -> str:
    """Build the base system prompt for the interactive session."""
    instructions = ""
    skill_path = os.path.join(SKILL_DIR, "SKILL.md")
    if os.path.exists(skill_path):
        try:
            with open(skill_path, "r") as f:
                instructions = f.read()[:1000]
        except Exception:
            pass

    return f"""You are a capable AI job search assistant running locally on the user's computer.
You have direct access to the local workspace via your tools.

You can read files, write files, list files, execute shell commands, fetch web URLs,
search with glob/grep, and append to CSV files.

### Available Tools:
- list_directory_files(directory_path) — List files in a directory
- read_workspace_file(path) — Read any file (text or PDF)
- write_workspace_file(path, content) — Create/overwrite files
- execute_shell_command(command) — Run shell commands (compile LaTeX, run scripts, etc.)
- glob_search(pattern) — Find files with glob patterns
- grep_search(pattern, file_pattern) — Search file contents
- web_fetch(url) — Fetch a URL and return readable text
- append_to_csv(filepath, row_data) — Append a row to CSV

### Available Slash Commands (handled by the system):
- /setup, /apply, /scrape, /expand, /upskill, /reset, /help

When the user asks a general question (not a slash command), answer helpfully using your context.
When they ask you to read or analyze files, use the tools provided.
Keep your responses structured, professional, and clear.
"""


def main():
    print("[DeepSeek Job Search Agent]", flush=True)
    print("=" * 56, flush=True)

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("Error: DEEPSEEK_API_KEY not found. Create a .env file:", flush=True)
        print("       cp .env.example .env", flush=True)
        sys.exit(1)

    system_prompt = load_system_prompt()

    main_tools = [
        list_directory_files,
        read_workspace_file,
        write_workspace_file,
        execute_shell_command,
        glob_search,
        grep_search,
        web_fetch,
        append_to_csv,
    ]

    try:
        session = create_chat_session(system_prompt, main_tools)
    except Exception as e:
        print(f"Error establishing session: {e}", flush=True)
        sys.exit(1)

    print(f"  Model:      {DEEPSEEK_MODEL}", flush=True)
    print(f"  Thinking:   {'ON' if DEEPSEEK_THINKING else 'OFF'}", flush=True)
    if DEEPSEEK_THINKING:
        print(f"  Reasoning:  {DEEPSEEK_REASONING_EFFORT}", flush=True)
    print(flush=True)
    print("Ready! Type a command or ask a question.")
    print("Type '/help' for available commands, '/exit' to quit.\n", flush=True)

    pending_reset_scope = None

    while True:
        try:
            user_input = input("You > ")
            if user_input.strip() == "/exit":
                print("Goodbye!")
                break

            if not user_input.strip():
                continue

            # Handle RESET confirmation flow
            if user_input.strip() == "RESET" and pending_reset_scope:
                result = execute_reset(pending_reset_scope)
                print(f"\nAgent > {result}\n", flush=True)
                pending_reset_scope = None
                continue
            elif user_input.strip() == "RESET":
                print(
                    "\nAgent > Reset what? Use `/reset profile`, `/reset documents`, or `/reset all`.\n",
                    flush=True,
                )
                continue
            else:
                pending_reset_scope = None

            # Handle slash commands
            cmd_result = route_command(user_input)
            if cmd_result is not None:
                print(f"\nAgent > {cmd_result}\n", flush=True)
                # Track pending reset confirmation
                stripped = user_input.strip()
                if stripped.startswith("/reset") and not cmd_result.startswith(
                    "**Usage"
                ):
                    args = stripped[len("/reset") :].strip().lower()
                    if args in ("profile", "documents", "all"):
                        pending_reset_scope = args
                continue

            # Regular conversation - send to DeepSeek
            print("Thinking...", flush=True)
            response = session.send_message(user_input)
            print(f"\nAgent > {response}\n", flush=True)

        except KeyboardInterrupt:
            print("\nExiting agent session.", flush=True)
            break
        except Exception as e:
            print(f"\nAn error occurred: {e}\n", flush=True)


if __name__ == "__main__":
    main()
