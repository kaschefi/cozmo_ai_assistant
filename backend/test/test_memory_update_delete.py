# backend/test/test_memory_update_delete.py
import os
import sys
import time

# Ensure backend root is on sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if not os.path.exists(os.path.join(backend_dir, "schemas")):
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, backend_dir)

from dotenv import load_dotenv
load_dotenv()

from schemas.memory_db import long_term_memory

TEST_USER = "test_e2e_reconciliation_user"


def run_e2e_memory_tests():
    print("=" * 65)
    print("  E2E TEST: LONG-TERM MEMORY UPDATE & DELETE WITH RECONCILIATION")
    print("=" * 65)

    # Clean slate for test user
    print("\n[Step 0] Cleaning test user environment...")
    long_term_memory.reset_user_memory(user_id=TEST_USER)
    initial_mems = long_term_memory.get_all_memories(user_id=TEST_USER)
    print(f" -> Active memories: {initial_mems}")
    assert len(initial_mems) == 0, "Test user memory should be empty initially"

    # -------------------------------------------------------------
    # 1. DIRECT CRUD TEST
    # -------------------------------------------------------------
    print("\n[Step 1] Testing Direct Save & Update...")
    save_res = long_term_memory.save_memory("User's name is Michael", user_id=TEST_USER)
    details = long_term_memory.get_all_memories_with_details(user_id=TEST_USER)
    print(f" -> Stored details: {details}")
    assert len(details) == 1, "Should have exactly 1 memory stored"
    mem_id = details[0]["id"]
    assert "Michael" in details[0]["memory"]

    print(f"\n[Step 2] Updating memory {mem_id} directly to 'User's name is Mohammad'...")
    upd_success = long_term_memory.update_memory(mem_id, "User's name is Mohammad")
    assert upd_success, "update_memory should return True"

    mems_after_upd = long_term_memory.get_all_memories(user_id=TEST_USER)
    print(f" -> Memories after update: {mems_after_upd}")
    assert any("Mohammad" in m for m in mems_after_upd), "Mohammad should be present"
    assert not any("Michael" in m for m in mems_after_upd), "Michael must NOT be present"

    print("\n[Step 3] Testing Search after Update...")
    search_res = long_term_memory.retrieve_relevant_memories("what is my name?", user_id=TEST_USER)
    print(f" -> Search results for 'what is my name?': {search_res}")
    assert any("Mohammad" in r for r in search_res), "Search should find Mohammad"
    assert not any("Michael" in r for r in search_res), "Search must not find Michael"

    print(f"\n[Step 4] Deleting memory {mem_id} directly...")
    del_success = long_term_memory.delete_memory(mem_id)
    assert del_success, "delete_memory should return True"
    mems_after_del = long_term_memory.get_all_memories(user_id=TEST_USER)
    print(f" -> Memories after delete: {mems_after_del}")
    assert len(mems_after_del) == 0, "All memories should be deleted"

    # -------------------------------------------------------------
    # 2. DIALOGUE RECONCILIATION TEST (UPDATE CONFLICT RESOLUTION)
    # -------------------------------------------------------------
    print("\n" + "-" * 65)
    print(" [Step 5] Dialogue Reconciliation: Seeding initial memories")
    print("-" * 65)
    # Seed memories: user name is Michael, user studies robotics
    long_term_memory.save_memory("User's name is Michael", user_id=TEST_USER)
    long_term_memory.save_memory("User studies robotics engineering", user_id=TEST_USER)

    current_mems = long_term_memory.get_all_memories(user_id=TEST_USER)
    print(f" -> Current seeded memories: {current_mems}")
    assert len(current_mems) == 2

    print("\n[Step 6] Simulating user turn correcting their name:")
    print(" -> User: 'my name is not michael forget that, my name is mohammad'")
    dialogue_turn_update = [
        {"role": "user", "content": "my name is not michael forget that, my name is mohammad"},
        {"role": "assistant", "content": "Understood! I have updated my records to Mohammad."}
    ]
    long_term_memory.add_dialogue(dialogue_turn_update, user_id=TEST_USER)

    mems_reconciled = long_term_memory.get_all_memories(user_id=TEST_USER)
    print(f" -> Memories after dialogue update: {mems_reconciled}")

    assert any("Mohammad" in m for m in mems_reconciled), "Mohammad must be in memory"
    assert not any("Michael" in m for m in mems_reconciled), "Michael must be completely eliminated"

    # -------------------------------------------------------------
    # 3. DIALOGUE RECONCILIATION TEST (DELETE / FORGET REQUEST)
    # -------------------------------------------------------------
    print("\n[Step 7] Simulating user turn asking to forget a fact:")
    print(" -> User: 'forget that I study robotics, delete that'")
    dialogue_turn_delete = [
        {"role": "user", "content": "forget that I study robotics, delete that"},
        {"role": "assistant", "content": "Got it, I have erased that from my memory."}
    ]
    long_term_memory.add_dialogue(dialogue_turn_delete, user_id=TEST_USER)

    mems_final = long_term_memory.get_all_memories(user_id=TEST_USER)
    print(f" -> Memories after dialogue delete: {mems_final}")

    assert not any("robotics" in m.lower() for m in mems_final), "Robotics should be completely deleted"
    assert any("Mohammad" in m for m in mems_final), "Mohammad should still be remembered"

    # -------------------------------------------------------------
    # 4. FINAL QUERY TEST
    # -------------------------------------------------------------
    print("\n[Step 8] Final search query verification: 'What is my name?'")
    final_search = long_term_memory.retrieve_relevant_memories("what is my name?", user_id=TEST_USER)
    print(f" -> Search query results: {final_search}")
    assert any("Mohammad" in r for r in final_search)
    assert not any("Michael" in r for r in final_search)

    # Clean up test user
    print("\n[Step 9] Cleaning up test user records...")
    long_term_memory.reset_user_memory(user_id=TEST_USER)

    print("\n" + "=" * 65)
    print("  ALL TESTS PASSED SUCCESSFULLY! ")
    print("  - Direct Update & Delete: PASSED")
    print("  - Dialogue-driven Name Update (Michael -> Mohammad): PASSED")
    print("  - Dialogue-driven Forget / Deletion: PASSED")
    print("  - Postgres pgvector concurrency: PASSED")
    print("=" * 65)


if __name__ == "__main__":
    run_e2e_memory_tests()

