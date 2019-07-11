import asyncio
import curses
import itertools
import random
import time
from pathlib import Path

from curses_tools import draw_frame, read_controls, get_frame_size
from physics import update_speed
from space_garbage import fly_garbage

TIC_TIMEOUT = 0.1
STARS_SYMBOLS = "+*.:"
MIN_NUM_STARS = 10
MAX_NUM_STARS = 100
PADDING = 3
BASE_PATH = Path(__file__).parent
ANIMATIONS_PATH = BASE_PATH / "animations"

coroutines = []
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


async def fill_orbit_with_garbage(canvas, garbage_frames):
    _, max_col = canvas.getmaxyx()
    while True:
        coroutines.append(fly_garbage(canvas, random.randint(0, max_col), random.choice(garbage_frames)))
        await sleep(random.randint(5, 15))


async def fire(canvas, start_row, start_column, rows_speed=-0.3, columns_speed=0):
    """Display animation of gun shot. Direction and speed can be specified."""

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

    cur_row = limit_coordinate(row - init_row_shift_x2 // 2, max_row)
    cur_col = limit_coordinate(column - init_col_shift_x2 // 2, max_col)

    row_speed, column_speed = 0, 0

    prev_frame = None
    while True:
        if prev_frame is not None:
            draw_frame(canvas, cur_row, cur_col, prev_frame, negative=True)

        frame_rows, frame_cols = get_frame_size(spaceship_frame)
        row_shift, col_shift, is_space = read_controls(canvas)

        row_speed, column_speed = update_speed(row_speed, column_speed, row_shift, col_shift)
        if is_space:  # cannon shot
            coroutines.append(fire(canvas, cur_row, cur_col + frame_cols // 2))

        row, column = row + row_speed, column + column_speed
        cur_row = limit_coordinate(cur_row + row_shift, max_row - frame_rows)
        cur_col = limit_coordinate(cur_col + col_shift, max_col - frame_cols)

        prev_frame = spaceship_frame
        draw_frame(canvas, cur_row, cur_col, spaceship_frame)

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


def draw(canvas):
    global coroutines

    curses.curs_set(False)  # hide cursor

    max_row, max_col = canvas.getmaxyx()
    num_stars = random.randint(MIN_NUM_STARS, MAX_NUM_STARS)

    coroutines.append(fire(canvas, max_row // 2, max_col // 2))
    coroutines += [blink(canvas,
                         random.randint(PADDING, max_row - PADDING),
                         random.randint(PADDING, max_col - PADDING),
                         symbol=random.choice(STARS_SYMBOLS))
                   for _ in range(num_stars)]

    spaceship_frames = get_frames_from_files(sorted(ANIMATIONS_PATH.rglob("rocket_frame_*.txt")))
    coroutines.append(animate_spaceship(spaceship_frames))
    coroutines.append(run_spaceship(canvas, max_row // 2, max_col // 2))

    garbage_frames = get_frames_from_files(ANIMATIONS_PATH.rglob("trash_*.txt"))
    coroutines.append(fill_orbit_with_garbage(canvas, garbage_frames))

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
