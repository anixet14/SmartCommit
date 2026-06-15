#!/c/Python312/python
import sys
import os
import subprocess
import argparse
import importlib
import time
try:
    from dotenv import load_dotenv
    load_dotenv()  # loads .env into os.environ if file exists
except ImportError:
    pass  # dotenv not required if using system environment variables

"""
Prepare-commit-msg Git hook that asks Google Gemini to generate a Conventional Commits
formatted commit message based on the staged diff.

Usage (Git will call this automatically as a hook):
  prepare-commit-msg <commit_msg_filepath> [commit_source] [sha1]

Behavior:
- If GEMINI_API_KEY is not set, exits with an error.
- If commit_source is 'message' or 'commit', exits immediately (do not overwrite user-provided messages).
- If there are no staged changes, exits quietly.
- Otherwise, sends staged diff to Gemini and writes the raw generated commit message
  back to the commit message file.
"""

MAX_SUBJECT_LENGTH = 50
MODEL_NAME = "gemini-2.5-flash"


def read_api_key():
    """Return the Gemini API key from environment or raise ValueError."""
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise ValueError("GEMINI_API_KEY environment variable is not set.")
    return key


def get_hook_args(argv=None):
    # Accept argv to make the function testable; fall back to sys.argv
    if argv is None:
        argv = sys.argv
    if len(argv) < 2:
        raise ValueError("prepare-commit-msg expects at least 1 argument: commit_msg_filepath")
    commit_msg_filepath = argv[1]
    commit_source = argv[2] if len(argv) >= 3 else None
    return commit_msg_filepath, commit_source


def is_user_message_source(commit_source: str) -> bool:
    # Git uses 'message' when commit message provided with -m, 'commit' may indicate --amend
    if not commit_source:
        return False
    lower = commit_source.lower()
    return lower == "message" or lower == "commit"


def get_staged_diff() -> str:
    try:
        result = subprocess.run([
            "git",
            "diff",
            "--staged"
        ], capture_output=True, text=True, check=False, encoding='utf-8', errors='replace')
    except Exception as e:
        # Return empty string on failure; caller will treat as no changes
        print(f"WARN: running git diff failed: {e}", file=sys.stderr)
        return ""

    return result.stdout or ""


def build_prompt(diff_text: str) -> str:
    prompt = """
You are an expert software developer and git maintainer. Based on the staged git diff below, compose a concise, high-quality commit message using the Conventional Commits format.

Requirements (must follow exactly):
- Output only the raw commit message with no commentary, explanation, or markdown formatting.
- Use Conventional Commits types (e.g., feat, fix, docs, chore, refactor, perf, test).
- Enforce a 50-character limit for the SUBJECT line (the first line). If necessary, shorten the subject to fit 50 characters while remaining clear.
- The commit message should have a subject line (type: short summary) and, optionally, a blank line followed by a more detailed body if the changes require it.
- Do NOT include surrounding backticks or triple-backticks in your output.

Format example to emulate exactly (subject <= 50 chars):
feat(parser): add support for X

Add a short descriptive body if necessary. Keep the body lines reasonably wrapped.

Staged git diff (do not invent changes, base message only on the diff below):

{diff}
""".strip().format(diff=diff_text)
    return prompt


def sanitize_generated_text(text: str) -> str:
    # Remove surrounding code fences/backticks and trim
    if not text:
        return ""
    t = text.strip()
    # Remove triple backticks blocks
    if t.startswith("```") and t.endswith("```"):
        t = t[3:-3].strip()
    # Remove single backticks occurrences that wrap whole text
    if t.startswith("`") and t.endswith("`"):
        t = t[1:-1].strip()
    # In case the model prepends or appends quotes
    if (t.startswith('"') and t.endswith('"')) or (t.startswith("'") and t.endswith("'")):
        t = t[1:-1].strip()
    return t


def extract_text_from_response(resp) -> str:
    # The google.generativeai response format can vary between releases.
    # Try several known shapes defensively.
    try:
        # Newer SDKs often have .candidates[0].output[0].content or .candidates[0].content[0].text
        if hasattr(resp, "candidates") and resp.candidates:
            c0 = resp.candidates[0]
            # Try direct text
            if hasattr(c0, "content"):
                content = c0.content
                # content may be a list of dicts
                if isinstance(content, list) and len(content) > 0:
                    first = content[0]
                    if isinstance(first, dict) and "text" in first:
                        return first["text"]
                    if isinstance(first, str):
                        return first
                elif isinstance(content, str):
                    return content
            # Fallback: candidate may have 'output' or 'text'
            if hasattr(c0, "output"):
                out = c0.output
                if isinstance(out, list) and len(out) > 0:
                    el = out[0]
                    if isinstance(el, dict) and "text" in el:
                        return el["text"]
                    if isinstance(el, str):
                        return el
            if hasattr(c0, "text"):
                return c0.text

        # Some responses return a simple .text attribute
        if hasattr(resp, "text") and isinstance(resp.text, str):
            return resp.text

        # Some return .output or .result
        if hasattr(resp, "output"):
            out = resp.output
            if isinstance(out, str):
                return out
            if isinstance(out, dict) and "content" in out:
                return out["content"]

        if hasattr(resp, "result"):
            res = resp.result
            if isinstance(res, str):
                return res
            if isinstance(res, dict) and "content" in res:
                return res["content"]

        # Last resort: try to stringify
        return str(resp)
    except Exception:
        try:
            return str(resp)
        except Exception:
            return ""


def run_gemini(prompt: str, api_key: str):
    """Call Gemini and return the model response object (may raise)."""
    try:
        from google import genai
    except ImportError:
        raise RuntimeError(
            "Could not import google.genai. "
            "Install it with: pip install google-genai"
        )
    
    with genai.Client(api_key=api_key) as client:
        return client.models.generate_content(model=MODEL_NAME, contents=prompt)


def run_hook(commit_msg_filepath: str, commit_source: str = None, dry_run: bool = False):
    """Core logic of the hook. Returns the generated message on success (or None).

    If dry_run is True, the function will return the message instead of writing the file.
    """
    # If the user supplied a message via -m or --amend, don't overwrite
    if is_user_message_source(commit_source):
        return None

    diff_text = get_staged_diff()
    if not diff_text.strip():
        return None

    prompt = build_prompt(diff_text)

    try:
        api_key = read_api_key()
    except ValueError as e:
        raise

    # Call Gemini with retries for transient errors (503/unavailable/rate limits)
    max_attempts = 3
    response = None
    for attempt in range(1, max_attempts + 1):
        try:
            response = run_gemini(prompt, api_key)
            break
        except Exception as e:
            msg = str(e) or ""
            is_transient = False
            # simple heuristic for transient errors from the GenAI API
            if any(token in msg for token in ("503", "UNAVAILABLE", "overloaded", "rate limit", "rate_limited", "timeout", "timed out")):
                is_transient = True

            # If the SDK import failed or it's a non-transient error, surface it immediately
            if not is_transient:
                raise RuntimeError(f"Gemini API call failed: {e}")

            # If transient and we have attempts left, wait and retry
            if attempt < max_attempts:
                wait = 2 ** (attempt - 1)
                print(f"WARN: transient Gemini error (attempt {attempt}/{max_attempts}): {e}. Retrying in {wait}s...", file=sys.stderr)
                time.sleep(wait)
                continue

            # Exhausted retries — warn and skip AI generation (do not block commits)
            print(f"WARN: Gemini unavailable after {max_attempts} attempts: {e}. Skipping AI commit message generation.", file=sys.stderr)
            return None

    raw = extract_text_from_response(response)
    cleaned = sanitize_generated_text(raw)

    if not cleaned:
        raise RuntimeError("No text returned from Gemini or failed to parse response.")

    # Ensure subject line is <= MAX_SUBJECT_LENGTH; if not, attempt a best-effort truncation of the first line
    lines = cleaned.splitlines()
    if not lines:
        return None
    subject = lines[0].strip()
    if len(subject) > MAX_SUBJECT_LENGTH:
        truncated = subject[:MAX_SUBJECT_LENGTH]
        if " " in truncated:
            truncated = " ".join(truncated.split(" ")[:-1]).rstrip()
        subject = truncated
    rest = "\n".join(lines[1:]).rstrip()
    final_message = subject + ("\n\n" + rest if rest else "")

    if dry_run:
        # Return generated message for dry-run/testing
        return final_message

    # Write to commit message file
    with open(commit_msg_filepath, "w", encoding="utf-8") as f:
        f.write(final_message + "\n")
    return final_message


def main(argv=None):
    # Simple CLI wrapper so git hook usage is unchanged and tests can call run_hook.
    parser = argparse.ArgumentParser(prog="prepare-commit-msg")
    parser.add_argument("commit_msg_filepath")
    parser.add_argument("commit_source", nargs="?", default=None)
    parser.add_argument("--dry-run", action="store_true", help="Print generated message instead of writing the commit file (for testing)")
    args = parser.parse_args(argv[1:] if argv else None)

    try:
        result = run_hook(args.commit_msg_filepath, args.commit_source, dry_run=args.dry_run)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    # If dry-run, print the message for preview
    if args.dry_run and result:
        print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
