# backend/test/test_sync_memory.py
import os
import sys

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from dotenv import load_dotenv
load_dotenv()

from schemas.memory_db import long_term_memory
from sync_memory import export_profile_to_markdown, import_profile_from_markdown

TEST_USER = "test_sync_user"
TEST_MD_PATH = os.path.join(backend_dir, "data", "test_user_profile.md")


def test_markdown_sync():
    print("=" * 60)
    print("  TESTING TWO-WAY MARKDOWN MEMORY SYNC")
    print("=" * 60)

    # 1. Reset test user
    long_term_memory.reset_user_memory(user_id=TEST_USER)

    # 2. Add two initial memories directly
    long_term_memory.save_memory("User's name is Alice", user_id=TEST_USER)
    long_term_memory.save_memory("User likes coffee", user_id=TEST_USER)

    # 3. Export to test markdown
    export_profile_to_markdown(file_path=TEST_MD_PATH, user_id=TEST_USER)
    with open(TEST_MD_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    assert "Alice" in content
    assert "coffee" in content
    print(" -> Initial export succeeded.")

    # 4. Simulate user editing the markdown file:
    #    - Update: change coffee to "tea"
    #    - Delete: remove the Alice line
    #    - Add: add a new line for location
    lines = content.splitlines()
    new_lines = []
    for line in lines:
        if "Alice" in line:
            # Delete Alice by skipping line
            continue
        elif "coffee" in line:
            # Change coffee to tea
            new_lines.append(line.replace("User likes coffee", "User loves green tea"))
        else:
            new_lines.append(line)

    # Add a new line
    new_lines.append("- User lives in Munich")

    with open(TEST_MD_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(new_lines))
    print(" -> File edited: Deleted Alice, Updated coffee -> green tea, Added Munich.")

    # 5. Run sync import
    import_profile_from_markdown(file_path=TEST_MD_PATH, user_id=TEST_USER)

    # 6. Verify database reflects edits
    mems = long_term_memory.get_all_memories(user_id=TEST_USER)
    print(f" -> DB after sync: {mems}")
    assert not any("Alice" in m for m in mems), "Alice should have been deleted!"
    assert any("green tea" in m for m in mems), "Green tea update should be in DB!"
    assert not any("coffee" in m for m in mems), "Old coffee fact should be replaced!"
    assert any("Munich" in m for m in mems), "Munich addition should be in DB!"

    # 7. Clean up
    if os.path.exists(TEST_MD_PATH):
        os.remove(TEST_MD_PATH)
    long_term_memory.reset_user_memory(user_id=TEST_USER)

    print("\n" + "=" * 60)
    print(" ALL MARKDOWN SYNC TESTS PASSED! ")
    print("=" * 60)


if __name__ == "__main__":
    test_markdown_sync()

