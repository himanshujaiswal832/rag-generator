"""
Export Agent Transcripts for Assessment Submission
Reads raw conversation logs and exports structured Markdown and JSONL transcripts.
"""

import os
import json
import shutil
from datetime import datetime

CONVERSATION_ID = "781deab7-3294-4235-9281-f59519343a7a"
APP_DATA_DIR = r"C:\Users\user\.gemini\antigravity-ide"
LOGS_DIR = os.path.join(APP_DATA_DIR, "brain", CONVERSATION_ID, ".system_generated", "logs")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "transcripts")

def export_transcripts():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    raw_full = os.path.join(LOGS_DIR, "transcript_full.jsonl")
    raw_compact = os.path.join(LOGS_DIR, "transcript.jsonl")

    src_file = raw_full if os.path.exists(raw_full) else raw_compact
    if not os.path.exists(src_file):
        print(f"[!] Log file not found at: {src_file}")
        return

    # 1. Copy raw JSONL
    dest_jsonl = os.path.join(OUTPUT_DIR, "transcript_full.jsonl")
    shutil.copy(src_file, dest_jsonl)
    print(f"[+] Exported raw JSONL transcript to: {dest_jsonl}")

    # 2. Parse and format Markdown transcript
    md_path = os.path.join(OUTPUT_DIR, "agent_transcript.md")
    lines_written = 0

    with open(src_file, "r", encoding="utf-8") as f_in, open(md_path, "w", encoding="utf-8") as f_out:
        f_out.write("# AI Agent Trajectory Transcript\n\n")
        f_out.write(f"- **Conversation ID:** `{CONVERSATION_ID}`\n")
        f_out.write(f"- **Project:** RAG Generator (Candidate Coding Assessment)\n")
        f_out.write(f"- **Export Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f_out.write("---\n\n")

        for line in f_in:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                step_idx = record.get("step_index", lines_written)
                step_type = record.get("type", "UNKNOWN")
                source = record.get("source", "")
                content = record.get("content", "")

                f_out.write(f"### Step {step_idx}: [{source}] {step_type}\n\n")

                if content:
                    f_out.write(f"```text\n{content[:2000]}\n```\n\n")

                tool_calls = record.get("tool_calls", [])
                if tool_calls:
                    f_out.write("**Tool Calls:**\n")
                    for tc in tool_calls:
                        name = tc.get("name") or tc.get("tool_name", "tool")
                        args = tc.get("args") or tc.get("arguments", {})
                        f_out.write(f"- `{name}`: `{json.dumps(args)[:200]}`\n")
                    f_out.write("\n")

                f_out.write("---\n\n")
                lines_written += 1
            except Exception as e:
                continue

    print(f"[+] Formatted {lines_written} steps into: {md_path}")

if __name__ == "__main__":
    export_transcripts()
