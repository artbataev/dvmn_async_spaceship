#!/usr/bin/env python3

import asyncio
import curses
import itertools
import random
import time

import game_state as state
from curses_tools import draw_frame, read_controls, get_frame_size
from explosion import explode
from game_scenario import get_garbage_delay_tics, PHRASES
from obstacles import show_obstacles
from physics import update_speed
from settings import GARBAGE_FRAMES_PATHS, SPACESHIP_FRAMES_PATHS, GAMEOVER_FRAME_PATH
from settings import PADDING
from settings import SHOW_OBSTACLES
from settings import STARS_SYMBOLS, MIN_NUM_STARS, MAX_NUM_STARS
from settings import START_YEAR, START_TIME, TIC_TIMEOUT
from space_garbage import fly_garbage


def get_frame_from_file(filename):
    with open(filename, "r", encoding="utf-8") as file:
        return file.read()


def get_frames_from_files(filenames):
    frames = []
    for filename in filenames:
        frames.append(get_frame_from_file(filename))
    return frames


def limit_coordinate(coordinate, max_coordinate):
    return max(0, min(coordinate, max_coordinate))


async def sleep(tics=1):
    for _ in range(tics):
        await asyncio.sleep(0)


async def tick_game_time():
    while True:
        state.year = START_YEAR + int((time.monotonic() - START_TIME) // 1.5)
        await sleep()


async def show_year_info(canvas):
    def get_year_info_frame(year, phrase):
        year_str = f"|| {year} | {phrase} ||"
        year_str_len = len(year_str)
        year_info_frame = "=" * year_str_len + "\n" + year_str + "\n" + "=" * year_str_len
        return year_info_frame

    phrase = PHRASES[START_YEAR]
    while True:
        if state.year in PHRASES:
            phrase = PHRASES[state.year]
        frame = get_year_info_frame(state.year, phrase)
        draw_frame(canvas, 0, 0, frame)
        canvas.syncup()  # needed to draw correctly
        await sleep()
        draw_frame(canvas, 0, 0, frame, negative=True)


async def fill_orbit_with_garbage(canvas, garbage_frames):
    _, max_col = canvas.getmaxyx()
    while True:
        state.coroutines.append(fly_garbage(canvas, random.randint(0, max_col), random.choice(garbage_frames)))
        await sleep(get_garbage_delay_tics(state.year) or 30)


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
        for obstacle in state.obstacles:
            if obstacle.has_collision(row, column):
                state.obstacles_in_last_collisions.append(obstacle)
                return
        canvas.addstr(round(row), round(column), symbol)
        await sleep()
        canvas.addstr(round(row), round(column), ' ')
        row += rows_speed
        column += columns_speed


async def animate_spaceship(frames):
    for frame in itertools.cycle(frames):
        state.spaceship_frame = frame
        await sleep()


async def run_spaceship(canvas, row, column):
    # find shift to draw text the way, when (row, column) is the center
    init_row_shift_x2, init_col_shift_x2 = get_frame_size(state.spaceship_frame)
    max_row, max_col = canvas.getmaxyx()

    # fix position to center spaceship
    row = limit_coordinate(row - init_row_shift_x2 // 2, max_row)
    column = limit_coordinate(column - init_col_shift_x2 // 2, max_col)

    row_speed, column_speed = 0, 0

    prev_frame = None
    while True:
        if prev_frame is not None:
            draw_frame(canvas, row, column, prev_frame, negative=True)

        frame_rows, frame_cols = get_frame_size(state.spaceship_frame)

        for obstacle in state.obstacles:
            if obstacle.has_collision(row, column, frame_rows, frame_cols):
                # game over
                state.coroutines.append(explode(canvas, row + frame_rows / 2, column + frame_cols / 2))
                await sleep(4)  # wait till the end of explosion
                state.coroutines.append(show_gameover(canvas))
                return

        row_shift, col_shift, space_pressed = read_controls(canvas)
        row_speed, column_speed = update_speed(row_speed, column_speed, row_shift, col_shift)

        row = limit_coordinate(row + row_speed, max_row - frame_rows)
        column = limit_coordinate(column + column_speed, max_col - frame_cols)

        prev_frame = state.spaceship_frame
        draw_frame(canvas, row, column, state.spaceship_frame)

        if space_pressed:  # cannon shot
            state.coroutines.append(fire(canvas, row, column + frame_cols // 2))

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
    game_over_frame = get_frame_from_file(GAMEOVER_FRAME_PATH)
    frame_rows, frame_cols = get_frame_size(game_over_frame)
    max_row, max_col = canvas.getmaxyx()
    while True:
        draw_frame(canvas, max_row / 2 - frame_rows / 2, max_col / 2 - frame_cols / 2, game_over_frame)
        await sleep()


def draw(canvas):
    curses.curs_set(False)  # hide cursor

    max_row, max_col = canvas.getmaxyx()
    num_stars = random.randint(MIN_NUM_STARS, MAX_NUM_STARS)

    state.coroutines.append(tick_game_time())
    state.coroutines.append(show_year_info(canvas.derwin(max_row - PADDING, 0)))
    state.coroutines.append(fire(canvas, max_row // 2, max_col // 2))
    state.coroutines += [blink(canvas,
                               random.randint(PADDING, max_row - PADDING),
                               random.randint(PADDING, max_col - PADDING),
                               symbol=random.choice(STARS_SYMBOLS))
                         for _ in range(num_stars)]

    spaceship_frames = get_frames_from_files(SPACESHIP_FRAMES_PATHS)
    state.coroutines.append(animate_spaceship(spaceship_frames))
    state.coroutines.append(run_spaceship(canvas, max_row // 2, max_col // 2))

    garbage_frames = get_frames_from_files(GARBAGE_FRAMES_PATHS)
    state.coroutines.append(fill_orbit_with_garbage(canvas, garbage_frames))

    if SHOW_OBSTACLES:
        state.coroutines.append(show_obstacles(canvas, state.obstacles))  # for debugging purpose
    canvas.nodelay(True)

    while True:
        for coroutine in state.coroutines.copy():  # using .copy() because list can be modified
            try:
                coroutine.send(None)
            except StopIteration:
                state.coroutines.remove(coroutine)
        canvas.refresh()
        time.sleep(TIC_TIMEOUT)


if __name__ == "__main__":
    curses.update_lines_cols()
    curses.wrapper(draw)
