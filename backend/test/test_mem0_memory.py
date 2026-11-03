# backend/test/test_mem0_memory.py
import os
import sys
import time

# Ensure backend root is on sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if not os.path.exists(os.path.join(backend_dir, "schemas")):
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, backend_dir)

from schemas.memory_db import long_term_memory


def test_mem0_end_to_end():
    print("=" * 60)
    print(" [1/5] Resetting test memory...")
    test_user = "test_eval_user"
    long_term_memory.reset_user_memory(user_id=test_user)

    initial_mems = long_term_memory.get_all_memories(user_id=test_user)
    assert len(initial_mems) == 0, f"Expected 0 initial memories, got: {initial_mems}"
    print(" -> Memory reset clean.")

    print("\n [2/5] Testing Dialogue Extraction (Name & Language)...")
    dialogue = [
        {"role": "user", "content": "Hi, my name is Alex and I specialize in Python development."},
        {"role": "assistant", "content": "Nice to meet you, Alex! Python is a great language."}
    ]
    long_term_memory.add_dialogue(dialogue, user_id=test_user)

    # Allow a moment for storage write
    time.sleep(1)
    all_mems = long_term_memory.get_all_memories(user_id=test_user)
    print(f" -> Extracted memories ({len(all_mems)}):")
    for m in all_mems:
        print(f"    * {m}")
    assert any("Alex" in m for m in all_mems), "User name 'Alex' was not captured!"
    assert any("Python" in m for m in all_mems), "Programming language 'Python' was not captured!"

    print("\n [3/5] Testing Hybrid Semantic Search...")
    retrieved = long_term_memory.retrieve_relevant_memories("What programming language do I code in?", user_id=test_user, limit=2)
    print(f" -> Query retrieved: {retrieved}")
    assert any("Python" in r for r in retrieved), "Hybrid retrieval failed to retrieve Python preference!"

    print("\n [4/5] Testing Memory Update & Conflict Resolution...")
    update_dialogue = [
        {"role": "user", "content": "Actually, I don't use Python anymore. I switched completely to Rust."},
        {"role": "assistant", "content": "Got it! Rust has fantastic memory safety."}
    ]
    long_term_memory.add_dialogue(update_dialogue, user_id=test_user)
    time.sleep(1)

    updated_retrieved = long_term_memory.retrieve_relevant_memories("What language do I code in?", user_id=test_user, limit=3)
    print(f" -> Retrieved after update: {updated_retrieved}")
    assert any("Rust" in r for r in updated_retrieved), "Updated preference 'Rust' was not found!"

    print("\n [5/5] Testing Noise Rejection (Weather / Time / Appointments)...")
    noise_dialogue = [
        {"role": "user", "content": "What's the weather like right now? Also remind me of my 4pm meeting."},
        {"role": "assistant", "content": "It is cloudy and 18 degrees. I noted your 4pm meeting."}
    ]
    long_term_memory.add_dialogue(noise_dialogue, user_id=test_user)
    time.sleep(1)

    final_mems = long_term_memory.get_all_memories(user_id=test_user)
    print(f" -> Final memories count ({len(final_mems)}):")
    for m in final_mems:
        print(f"    * {m}")
    assert not any("18 degrees" in m.lower() for m in final_mems), "Transient weather detail leaked into permanent memory!"

    # Clean up test user
    long_term_memory.reset_user_memory(user_id=test_user)
    print("\n" + "=" * 60)
    print(" ALL MEM0 MEMORY TESTS PASSED SUCCESSFULLY! ")
    print("=" * 60)


if __name__ == "__main__":
    test_mem0_end_to_end()

