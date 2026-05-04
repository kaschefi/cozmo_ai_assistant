import asyncio


async def run_timer_logic(seconds: int, face_library):
    """
    This function runs the countdown loop.
    """
    print(f" Timer logic started for {seconds} seconds.")

    for i in range(seconds, -1, -1):
        # Format the numbers (MM:SS)
        mins, secs = divmod(i, 60)
        time_display = f"{mins:02d}:{secs:02d}"

        # Tell the Face Library to show these numbers
        face_library.act_timer(time_display)

        await asyncio.sleep(1)

    print(" Done! Resetting face.")
    face_library.act_reset()