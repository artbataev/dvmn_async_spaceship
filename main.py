import asyncio
import curses
import itertools
import random
import time
from pathlib import Path

from curses_tools import draw_frame, read_controls, get_frame_size
from game_scenario import get_garbage_delay_tics, PHRASES
from physics import update_speed
from space_garbage import fly_garbage

TIC_TIMEOUT = 0.1
STARS_SYMBOLS = "+*.:"
MIN_NUM_STARS = 10
MAX_NUM_STARS = 100
PADDING = 3
BASE_PATH = Path(__file__).parent
ANIMATIONS_PATH = BASE_PATH / "animations"

START_YEAR = 1957
year = START_YEAR
start_time = time.time()

coroutines = []
obstacles = []
obstacles_in_last_collisions = []
spaceship_frame = ""


def get_frames_from_files(files):
    frames = []
    for file in files:
        with open(file, "r", encoding="utf-8") as f:
            frames.append(f.read())
    return frames


def limit_coordinate(coordinate, max_coordinate):
    return max(0, min(coordinate, max_coordinate))


async def sleep(tics=1):
    for _ in range(tics):
        await asyncio.sleep(0)


async def tick_game_time():
    global start_time
    global year
    while True:
        year = START_YEAR + int((time.time() - start_time) // 1.5)
        await sleep()


async def show_year_info(canvas):
    def get_year_info_frame(year, phrase):
        year_str = f"|| {year} | {phrase} ||"
        year_str_len = len(year_str)
        year_info_frame = "=" * year_str_len + "\n" + year_str + "\n" + "=" * year_str_len
        return year_info_frame

    phrase = PHRASES[START_YEAR]
    while True:
        if year in PHRASES:
            phrase = PHRASES[year]
        frame = get_year_info_frame(year, phrase)
        draw_frame(canvas, 0, 0, frame)
        canvas.syncup()  # needed to draw correctly
        await sleep()
        draw_frame(canvas, 0, 0, frame, negative=True)


async def fill_orbit_with_garbage(canvas, garbage_frames):
    global obstacles
    global obstacles_in_last_collisions
    global year
    _, max_col = canvas.getmaxyx()
    while True:
        coroutines.append(fly_garbage(canvas, random.randint(0, max_col), random.choice(garbage_frames), obstacles,
                                      obstacles_in_last_collisions))
        await sleep(get_garbage_delay_tics(year) or 30)


async def fire(canvas, start_row, start_column, rows_speed=-0.3, columns_speed=0):
    """Display animation of gun shot. Direction and speed can be specified."""
    global obstacles
    global obstacles_in_last_collisions

    row, column = start_row, start_column

    canvas.addstr(round(row), round(column), '*')
    await sleep()

    canvas.addstr(round(row), round(column), 'O')
    await sleep()
    canvas.addstr(round(row), round(column), ' ')

    row += rows_speed
    column += columns_speed

    symbol = '-' if columns_speed else '|'

    rows, columns = canvas.getmaxyx()
    max_row, max_column = rows - 1, columns - 1

    curses.beep()

    while 0 < row < max_row and 0 < column < max_column:
        for obstacle in obstacles.copy():  # using .copy() because list can be modified
            if obstacle.has_collision(row, column):
                obstacles_in_last_collisions.append(obstacle)
                obstacles.remove(obstacle)
                return
        canvas.addstr(round(row), round(column), symbol)
        await sleep()
        canvas.addstr(round(row), round(column), ' ')
        row += rows_speed
        column += columns_speed


async def animate_spaceship(frames):
    global spaceship_frame
    for frame in itertools.cycle(frames):
        spaceship_frame = frame
        await sleep()


async def run_spaceship(canvas, row, column):
    global spaceship_frame
    global coroutines
    # find shift to draw text the way, when (row, column) is the center
    init_row_shift_x2, init_col_shift_x2 = get_frame_size(spaceship_frame)
    max_row, max_col = canvas.getmaxyx()

    # fix position to center spaceship
    row = limit_coordinate(row - init_row_shift_x2 // 2, max_row)
    column = limit_coordinate(column - init_col_shift_x2 // 2, max_col)

    row_speed, column_speed = 0, 0

    prev_frame = None
    while True:
        if prev_frame is not None:
            draw_frame(canvas, row, column, prev_frame, negative=True)

        frame_rows, frame_cols = get_frame_size(spaceship_frame)

        for obstacle in obstacles:
            if obstacle.has_collision(row, column, frame_rows, frame_cols):
                coroutines.append(show_gameover(canvas))
                return

        row_shift, col_shift, is_space = read_controls(canvas)
        row_speed, column_speed = update_speed(row_speed, column_speed, row_shift, col_shift)

        row = limit_coordinate(row + row_speed, max_row - frame_rows)
        column = limit_coordinate(column + column_speed, max_col - frame_cols)

        prev_frame = spaceship_frame
        draw_frame(canvas, row, column, spaceship_frame)

        if is_space:  # cannon shot
            coroutines.append(fire(canvas, row, column + frame_cols // 2))

        await sleep()


async def blink(canvas, row, column, symbol='*'):
    while True:
        canvas.addstr(row, column, symbol, curses.A_DIM)
        await sleep(random.randint(1, 10))

        canvas.addstr(row, column, symbol)
        await sleep(random.randint(1, 3))

        canvas.addstr(row, column, symbol, curses.A_BOLD)
        await sleep(random.randint(1, 5))

        canvas.addstr(row, column, symbol)
        await sleep(random.randint(1, 3))


async def show_gameover(canvas):
    game_over_frame = get_frames_from_files(ANIMATIONS_PATH.glob("game_over.txt"))[0]
    frame_rows, frame_cols = get_frame_size(game_over_frame)
    max_row, max_col = canvas.getmaxyx()
    while True:
        draw_frame(canvas, max_row / 2 - frame_rows / 2, max_col / 2 - frame_cols / 2, game_over_frame)
        await sleep()


def draw(canvas):
    global coroutines
    global obstacles

    curses.curs_set(False)  # hide cursor

    max_row, max_col = canvas.getmaxyx()
    num_stars = random.randint(MIN_NUM_STARS, MAX_NUM_STARS)

    coroutines.append(tick_game_time())
    coroutines.append(show_year_info(canvas.derwin(max_row - PADDING, 0)))
    coroutines.append(fire(canvas, max_row // 2, max_col // 2))
    coroutines += [blink(canvas,
                         random.randint(PADDING, max_row - PADDING),
                         random.randint(PADDING, max_col - PADDING),
                         symbol=random.choice(STARS_SYMBOLS))
                   for _ in range(num_stars)]

    spaceship_frames = get_frames_from_files(sorted(ANIMATIONS_PATH.rglob("rocket_frame_*.txt")))
    coroutines.append(animate_spaceship(spaceship_frames))
    coroutines.append(run_spaceship(canvas, max_row // 2, max_col // 2))

    garbage_frames = get_frames_from_files(ANIMATIONS_PATH.rglob("garbage/*.txt"))
    coroutines.append(fill_orbit_with_garbage(canvas, garbage_frames))

    # coroutines.append(show_obstacles(canvas, obstacles))  # for debugging purpose
    canvas.nodelay(True)

    while True:
        for coroutine in coroutines.copy():  # using .copy() because list can be modified
            try:
                coroutine.send(None)
            except StopIteration:
                coroutines.remove(coroutine)
        canvas.refresh()
        time.sleep(TIC_TIMEOUT)


if __name__ == "__main__":
    curses.update_lines_cols()
    curses.wrapper(draw)
