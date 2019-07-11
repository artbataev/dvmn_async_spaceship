import asyncio
import curses
import itertools
import random
import time
from pathlib import Path

from curses_tools import draw_frame, read_controls, get_frame_size
from space_garbage import fly_garbage

TIC_TIMEOUT = 0.1
STARS_SYMBOLS = "+*.:"
MIN_NUM_STARS = 10
MAX_NUM_STARS = 100
PADDING = 3
BASE_PATH = Path(__file__).parent
ANIMATIONS_PATH = BASE_PATH / "animations"

coroutines = []


def limit_coordinate(coordinate, max_coordinate):
    return max(0, min(coordinate, max_coordinate))


async def fill_orbit_with_garbage(canvas, garbage_frames):
    _, max_col = canvas.getmaxyx()
    while True:
        coroutines.append(fly_garbage(canvas, random.randint(0, max_col), random.choice(garbage_frames)))
        for _ in range(random.randint(5, 15)):
            await asyncio.sleep(0)


def get_frames_from_files(files):
    frames = []
    for file in files:
        with open(file, "r", encoding="utf-8") as f:
            frames.append(f.read())
    return frames


async def fire(canvas, start_row, start_column, rows_speed=-0.3, columns_speed=0):
    """Display animation of gun shot. Direction and speed can be specified."""

    row, column = start_row, start_column

    canvas.addstr(round(row), round(column), '*')
    await asyncio.sleep(0)

    canvas.addstr(round(row), round(column), 'O')
    await asyncio.sleep(0)
    canvas.addstr(round(row), round(column), ' ')

    row += rows_speed
    column += columns_speed

    symbol = '-' if columns_speed else '|'

    rows, columns = canvas.getmaxyx()
    max_row, max_column = rows - 1, columns - 1

    curses.beep()

    while 0 < row < max_row and 0 < column < max_column:
        canvas.addstr(round(row), round(column), symbol)
        await asyncio.sleep(0)
        canvas.addstr(round(row), round(column), ' ')
        row += rows_speed
        column += columns_speed


async def animate_spaceship(canvas, row, column, frames):
    # find shift to draw text the way, when (row, column) is the center
    init_row_shift_x2, init_col_shift_x2 = get_frame_size(frames[0])
    max_row, max_col = canvas.getmaxyx()

    cur_row = limit_coordinate(row - init_row_shift_x2 // 2, max_row)
    cur_col = limit_coordinate(column - init_col_shift_x2 // 2, max_col)

    prev_frame = None
    for frame in itertools.cycle(frames):
        if prev_frame is not None:
            draw_frame(canvas, cur_row, cur_col, prev_frame, negative=True)

        row_shift, col_shift, is_space = read_controls(canvas)
        frame_rows, frame_cols = get_frame_size(frame)
        cur_row = limit_coordinate(cur_row + row_shift, max_row - frame_rows)
        cur_col = limit_coordinate(cur_col + col_shift, max_col - frame_cols)
        prev_frame = frame
        draw_frame(canvas, cur_row, cur_col, frame)
        await asyncio.sleep(0)


async def blink(canvas, row, column, symbol='*'):
    while True:
        canvas.addstr(row, column, symbol, curses.A_DIM)
        for _ in range(random.randint(1, 10)):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol)
        for _ in range(random.randint(1, 3)):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol, curses.A_BOLD)
        for _ in range(random.randint(1, 5)):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol)
        for _ in range(random.randint(1, 3)):
            await asyncio.sleep(0)


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
    coroutines.append(animate_spaceship(canvas, max_row // 2, max_col // 2, spaceship_frames))

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
