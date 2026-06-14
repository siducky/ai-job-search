import os
import subprocess
import sys
from google import genai
from google.genai import types

# Try importing pypdf to ensure it's installed
try:
    import pypdf
except ImportError:
    print("Error: 'pypdf' library is missing. Please run: pip install pypdf")
    sys.exit(1)

# ---------------------------------------------------------
# 1. Local Tools Definitions
# ---------------------------------------------------------


def list_directory_files(directory_path: str = "documents") -> str:
    """
    Recursively lists all files in a specified directory (defaults to 'documents').
    Use this to scan the documents folder and see what files are available to process.
    """
    safe_path = os.path.normpath(directory_path)
    if safe_path.startswith("..") or os.path.isabs(safe_path):
        return "Error: Access denied. You can only view files within the workspace."

    if not os.path.exists(safe_path):
        return f"Error: Directory '{directory_path}' does not exist."

    file_list = []
    for root, _, files in os.walk(safe_path):
        for file in files:
            relative_path = os.path.relpath(os.path.join(root, file))
            file_list.append(relative_path)

    if not file_list:
        return f"No files found in '{directory_path}'."

    return "Found files:\n" + "\n".join(file_list)


def read_workspace_file(path: str) -> str:
    """
    Reads the content of a file within the workspace.
    Automatically detects and extracts readable text from both raw text files (.md, .txt, .tex)
    and PDF files (.pdf).
    """
    safe_path = os.path.normpath(path)
    if safe_path.startswith("..") or os.path.isabs(safe_path):
        return "Error: Access denied. You can only read files within the workspace."

    if not os.path.exists(safe_path):
        return f"Error: File '{path}' not found."

    # Check if the file is a PDF
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

    # Fallback to plain text reading
    try:
        with open(safe_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception as e:
        return f"Error reading text file '{path}': {str(e)}"


def write_workspace_file(path: str, content: str) -> str:
    """
    Writes or overwrites a file in the workspace with the specified content.
    Use this to write CV drafts, cover letters, or edit profile markdown files.
    """
    safe_path = os.path.normpath(path)
    if safe_path.startswith("..") or os.path.isabs(safe_path):
        return "Error: Access denied. You can only write files within the workspace."

    try:
        os.makedirs(os.path.dirname(safe_path), exist_ok=True)
        with open(safe_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote content to '{path}'."
    except Exception as e:
        return f"Error writing file '{path}': {str(e)}"


def execute_shell_command(command: str) -> str:
    """
    Executes a shell command in the local environment.
    Use this to compile LaTeX files, run scrapers, or run python tools.
    """
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=60
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
        return "Error: Command execution timed out after 60 seconds."
    except Exception as e:
        return f"Error executing command: {str(e)}"


# ---------------------------------------------------------
# 2. Workspace Guideline Loader
# ---------------------------------------------------------


def load_system_guidelines() -> str:
    """Loads system instructions from the repository configuration."""
    base_instructions = ""
    skill_path = ".claude/skills/job-application-assistant/SKILL.md"
    if os.path.exists(skill_path):
        try:
            with open(skill_path, "r", encoding="utf-8") as f:
                base_instructions = f.read()
        except Exception as e:
            print(f"Warning: Failed to load SKILL.md ({e})")

    orchestrator_context = """
    You are a highly capable AI agentic job search assistant running locally on the user's computer.
    You have direct access to the local workspace via your tools.
    
    You can read files, write files, list files, and execute shell commands to build CVs, cover letters, and run scrapers.
    Keep your responses structured, professional, and clear.
    """
    return f"{orchestrator_context}\n\n=== Work Space Domain Rules ===\n{base_instructions}"


# ---------------------------------------------------------
# 3. Main Runner Loop
# ---------------------------------------------------------


def main():
    print("[DEBUG 1/5] Script started.", flush=True)

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is not set.", flush=True)
        print("Please export it: export GEMINI_API_KEY='your_key'", flush=True)
        sys.exit(1)

    print("[DEBUG 2/5] API Key found. Initializing Gemini Client...", flush=True)
    client = genai.Client()

    print("[DEBUG 3/5] Loading workspace guidelines...", flush=True)
    system_instruction = load_system_guidelines()

    # === HERE IS WHERE THE TOOLS_LIST IS UPDATED ===
    # This list passes our python functions directly to the Gemini API.
    tools_list = [
        list_directory_files,
        read_workspace_file,
        write_workspace_file,
        execute_shell_command,
    ]

    print("[DEBUG 4/5] Establishing active chat session with Gemini...", flush=True)
    try:
        chat = client.chats.create(
            model="gemini-2.5-flash",  # Fast, high limits, and reliable tool calling
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=tools_list,
                temperature=0.2,
            ),
        )
    except Exception as e:
        print(f"Error establishing session: {e}", flush=True)
        sys.exit(1)

    print("[DEBUG 5/5] Setup complete.")
    print("\n========================================================")
    print(" Gemini Job Search Agent Active")
    print(" You can ask me to view your profile, run scripts, or adapt CVs.")
    print(" Type '/exit' to close.")
    print("========================================================\n", flush=True)

    while True:
        try:
            user_input = input("You > ")
            if user_input.strip() == "/exit":
                print("Goodbye!")
                break

            if not user_input.strip():
                continue

            print("Thinking...")
            # The SDK automatically intercepts and executes tools in the background.
            response = chat.send_message(user_input)

            print(f"\nAgent > {response.text}\n", flush=True)

        except KeyboardInterrupt:
            print("\nExiting agent session.")
            break
        except Exception as e:
            print(f"\nAn error occurred: {e}\n", flush=True)


if __name__ == "__main__":
    main()
