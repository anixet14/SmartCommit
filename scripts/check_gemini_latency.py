#!/usr/bin/env python3
"""Check Gemini API connectivity and measure response latency.

Usage:
  python3 scripts/check_gemini_latency.py [--prompt "Short prompt"] [--model MODEL] [--max-latency SECONDS]

Environment:
  GEMINI_API_KEY must be set in environment.

Exit codes:
  0 - success (API reachable, optional latency within threshold)
  2 - missing GEMINI_API_KEY
  3 - google.genai import error
  4 - latency exceeded max threshold
  5 - API call failed

This script performs a single generate_content call and prints latency and sample output.
"""
import os
import sys
import time
import argparse

MODEL_DEFAULT = "gemini-2.5-flash"


def extract_text_from_response(resp) -> str:
    try:
        if hasattr(resp, "candidates") and resp.candidates:
            c0 = resp.candidates[0]
            if hasattr(c0, "content"):
                content = c0.content
                if isinstance(content, list) and len(content) > 0:
                    first = content[0]
                    if isinstance(first, dict) and "text" in first:
                        return first["text"]
                    if isinstance(first, str):
                        return first
                elif isinstance(content, str):
                    return content
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
        if hasattr(resp, "text") and isinstance(resp.text, str):
            return resp.text
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
        return str(resp)
    except Exception:
        try:
            return str(resp)
        except Exception:
            return ""


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check Gemini API latency")
    parser.add_argument("--prompt", default="Write a one-line commit message summarizing: small change", help="Prompt to send to the model")
    parser.add_argument("--model", default=MODEL_DEFAULT, help="Model name to use")
    parser.add_argument("--max-latency", type=float, default=None, help="Fail if latency (s) exceeds this value")
    parser.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout in seconds for the client")
    args = parser.parse_args(argv[1:] if argv else None)

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY environment variable is not set.", file=sys.stderr)
        return 2

    try:
        from google import genai
    except Exception as e:
        print("ERROR: Could not import google.genai. Install with: pip install google-genai", file=sys.stderr)
        print(f"DETAIL: {e}", file=sys.stderr)
        return 3

    try:
        start = time.perf_counter()
        with genai.Client(api_key=api_key) as client:
            # model generate
            resp = client.models.generate_content(model=args.model, contents=args.prompt)
        end = time.perf_counter()
    except Exception as e:
        print(f"ERROR: API call failed: {e}", file=sys.stderr)
        return 5

    latency = end - start
    print(f"Gemini model: {args.model}")
    print(f"Latency: {latency:.3f} seconds")

    text = extract_text_from_response(resp)
    print("--- Response excerpt ---")
    print(text[:1000])
    print("--- End excerpt ---")

    if args.max_latency is not None and latency > args.max_latency:
        print(f"ERROR: latency {latency:.3f}s exceeds threshold {args.max_latency}s", file=sys.stderr)
        return 4

    return 0


if __name__ == '__main__':
    sys.exit(main())
