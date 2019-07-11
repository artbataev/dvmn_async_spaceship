import asyncio

from curses_tools import draw_frame
from curses_tools import get_frame_size
from explosion import explode
from obstacles import Obstacle


async def fly_garbage(canvas, column, garbage_frame, obstacles, obstacles_in_last_collisions, speed=0.5):
    """Animate garbage, flying from top to bottom. Сolumn position will stay same, as specified on start."""
    rows_number, columns_number = canvas.getmaxyx()

    column = max(column, 0)
    column = min(column, columns_number - 1)

    row = 0

    obstacle = Obstacle(row, column, *get_frame_size(garbage_frame))
    obstacles.append(obstacle)
    while row < rows_number:
        if obstacle in obstacles_in_last_collisions:
            obstacles_in_last_collisions.remove(obstacle)
            await explode(canvas, row, column)
            return
        obstacle.row = row
        draw_frame(canvas, row, column, garbage_frame)
        await asyncio.sleep(0)
        draw_frame(canvas, row, column, garbage_frame, negative=True)
        row += speed
    obstacles.remove(obstacle)
