import os
import sys
import re
import argparse
from typing import List, Dict, Any, Optional

# Ensure backend root is on sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from dotenv import load_dotenv
load_dotenv()

from schemas.memory_db import long_term_memory

DEFAULT_PROFILE_PATH = os.path.join(backend_dir, "data", "user_profile.md")
DEFAULT_USER_ID = "cozmo_owner"


def export_profile_to_markdown(file_path: str = DEFAULT_PROFILE_PATH, user_id: str = DEFAULT_USER_ID) -> str:
    """
    Exports all active memory records from the vector database to a readable markdown file.
    Each item contains an explicit ID tag so updates and deletes can be tracked.
    """
    os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
    records = long_term_memory.get_all_memories_with_details(user_id=user_id)

    lines = [
        "# MoKa Long-Term Memory Profile",
        f"# User ID: {user_id}",
        "# Instructions:",
        "#   - Edit any existing line text to UPDATE a memory.",
        "#   - Delete an entire line to DELETE that memory from the database.",
        "#   - Add a new line starting with '- User ...' without an [id: ...] tag to ADD a new memory.",
        "",
        "## Active Memories",
        ""
    ]

    if not records:
        lines.append("# (No memories currently stored. Add lines below starting with '- User ...')")
    else:
        for r in records:
            mem_id = r.get("id")
            text = r.get("memory", "").strip()
            lines.append(f"- [id: {mem_id}] {text}")

    lines.append("")
    content = "\n".join(lines)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"[SyncMemory] Successfully exported {len(records)} memories to: {file_path}")
    return content


def parse_markdown_profile(file_path: str) -> List[Dict[str, Optional[str]]]:
    """
    Parses user_profile.md and extracts memories.
    Returns a list of dicts: [{'id': Optional[str], 'text': str}]
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Profile file not found at: {file_path}")

    parsed = []
    # Pattern matching: - [id: <uuid>] <memory text>
    item_pattern = re.compile(r"^[-*]\s*(?:\[id:\s*([a-zA-Z0-9_-]+)\])?\s*(.*)$")

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            # Ignore empty lines, headings, comments
            if not stripped or stripped.startswith("#"):
                continue

            match = item_pattern.match(stripped)
            if match:
                mem_id = match.group(1)
                text = match.group(2).strip()
                if text:
                    parsed.append({
                        "id": mem_id if mem_id else None,
                        "text": text
                    })

    return parsed


def import_profile_from_markdown(file_path: str = DEFAULT_PROFILE_PATH, user_id: str = DEFAULT_USER_ID):
    """
    Synchronizes manual markdown edits into the database:
    - Deleted lines -> client.delete(id)
    - Changed text -> client.update(id, new_text)
    - New lines -> client.add(text, infer=False)
    """
    parsed_items = parse_markdown_profile(file_path)
    existing_records = long_term_memory.get_all_memories_with_details(user_id=user_id)
    existing_map = {r["id"]: r["memory"].strip() for r in existing_records}

    parsed_ids = {item["id"] for item in parsed_items if item["id"]}

    updates_count = 0
    deletes_count = 0
    adds_count = 0

    # 1. Identify DELETIONS: IDs in DB that are missing from markdown file
    for db_id, db_text in existing_map.items():
        if db_id not in parsed_ids:
            print(f" [DELETE] Removing memory {db_id}: '{db_text}'")
            long_term_memory.delete_memory(db_id)
            deletes_count += 1

    # 2. Identify UPDATES & ADDITIONS:
    for item in parsed_items:
        mem_id = item["id"]
        text = item["text"]

        if mem_id and mem_id in existing_map:
            # Check if text changed
            old_text = existing_map[mem_id]
            if text != old_text:
                print(f" [UPDATE] Updating {mem_id}:\n    Old: '{old_text}'\n    New: '{text}'")
                long_term_memory.update_memory(mem_id, text)
                updates_count += 1
        else:
            # New line without ID or unrecognized ID -> ADD
            print(f" [ADD] Adding new memory: '{text}'")
            long_term_memory.save_memory(text, user_id=user_id)
            adds_count += 1

    print("\n" + "=" * 50)
    print(f"[Sync Completed] Adds: {adds_count} | Updates: {updates_count} | Deletes: {deletes_count}")
    print("=" * 50)

    # Re-export to update IDs for any newly added items
    export_profile_to_markdown(file_path=file_path, user_id=user_id)


def main():
    parser = argparse.ArgumentParser(description="Two-way Memory Markdown Sync for MoKa Assistant")
    parser.add_argument("--export", action="store_true", help="Export active database memories to user_profile.md")
    parser.add_argument("--import", dest="import_sync", action="store_true", help="Sync manual edits from user_profile.md into database")
    parser.add_argument("--file", type=str, default=DEFAULT_PROFILE_PATH, help="Path to markdown profile file")
    parser.add_argument("--user", type=str, default=DEFAULT_USER_ID, help="Target user ID (default: cozmo_owner)")

    args = parser.parse_args()

    # Default action if no flags provided:
    # If the markdown file exists, import manual edits; otherwise export.
    if args.export:
        export_profile_to_markdown(file_path=args.file, user_id=args.user)
    elif args.import_sync:
        import_profile_from_markdown(file_path=args.file, user_id=args.user)
    else:
        if os.path.exists(args.file):
            print(f"[SyncMemory] Found {args.file}. Syncing your manual edits to database...")
            import_profile_from_markdown(file_path=args.file, user_id=args.user)
        else:
            print(f"[SyncMemory] No existing profile file found. Exporting database to {args.file}...")
            export_profile_to_markdown(file_path=args.file, user_id=args.user)


if __name__ == "__main__":
    main()

