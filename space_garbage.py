import asyncio
from contextlib import contextmanager

import game_state as state
from curses_tools import draw_frame
from curses_tools import get_frame_size
from explosion import explode
from obstacles import Obstacle


@contextmanager
def add_obstacle(row, column, rows_size=1, columns_size=1, uid=None):
    obstacle = Obstacle(row, column, rows_size, columns_size, uid)
    state.obstacles.append(obstacle)
    try:
        yield obstacle
    finally:
        state.obstacles.remove(obstacle)


async def fly_garbage(canvas, column, garbage_frame, speed=0.5):
    """Animate garbage, flying from top to bottom. Сolumn position will stay same, as specified on start."""
    rows_number, columns_number = canvas.getmaxyx()

    column = max(column, 0)
    column = min(column, columns_number - 1)

    row = 0

    with add_obstacle(row, column, *get_frame_size(garbage_frame)) as obstacle:
        while row < rows_number:
            if obstacle in state.obstacles_in_last_collisions:
                state.obstacles_in_last_collisions.remove(obstacle)
                await explode(canvas, row, column)
                return
            obstacle.row = row
            draw_frame(canvas, row, column, garbage_frame)
            await asyncio.sleep(0)
            draw_frame(canvas, row, column, garbage_frame, negative=True)
            row += speed
