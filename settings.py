import time
from pathlib import Path

SHOW_OBSTACLES = False

TIC_TIMEOUT = 0.1
STARS_SYMBOLS = "+*.:"
MIN_NUM_STARS = 10
MAX_NUM_STARS = 100
PADDING = 3
BASE_PATH = Path(__file__).parent
ANIMATIONS_PATH = BASE_PATH / "animations"
GARBAGE_FRAMES_PATHS = list(ANIMATIONS_PATH.rglob("garbage/*.txt"))
SPACESHIP_FRAMES_PATHS = sorted(ANIMATIONS_PATH.rglob("rocket_frame_*.txt"))
GAMEOVER_FRAME_PATH = ANIMATIONS_PATH / "game_over.txt"

START_YEAR = 1957
START_TIME = time.monotonic()
