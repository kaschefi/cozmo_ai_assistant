import json
import pycozmo

from pathlib import Path

# Path to cozmo_animations.json at project root (or local dir fallback)
project_root = Path(__file__).resolve().parents[3]
json_path = project_root / "cozmo_animations.json"
if not json_path.exists():
    json_path = Path("cozmo_animations.json")

with open(json_path) as f:
    anims = json.load(f)

with pycozmo.connect() as cli:

    cli.load_anims()
    anim_name = anims["launch"]["wakeup_04"]
    anim_name2 = anims["launch"]["wakeup_startdriving_01"]

    cli.play_anim(anim_name)
    cli.wait_for(pycozmo.event.EvtAnimationCompleted)