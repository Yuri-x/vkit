from typing import Optional
from PIL import ImageDraw

from vkit.image.type import VImage, VImageKind
from .type import VImageGrid
from .grid_blender import create_image_from_image_grid


def visualize_image_grid(
    image_grid: VImageGrid,
    image: Optional[VImage] = None,
    line_color: str = 'black',
    show_index: bool = False,
    index_color: str = 'red',
):
    if not image:
        image = create_image_from_image_grid(image_grid, VImageKind.RGB)
        image.mat.fill(255)

    pil_image = image.to_pil_image()
    draw = ImageDraw.Draw(pil_image)

    for row in range(image_grid.num_rows):
        for col in range(image_grid.num_cols):
            point0 = image_grid.points_2d[row][col]

            draw_left_right = False
            if col < image_grid.num_cols - 1:
                # Draw left-right line.
                point1 = image_grid.points_2d[row][col + 1]
                draw.line([(point0.x, point0.y), (point1.x, point1.y)], fill=line_color)
                draw_left_right = True

            draw_up_down = False
            if row < image_grid.num_rows - 1:
                # Draw up-down line.
                point1 = image_grid.points_2d[row + 1][col]
                draw.line([(point0.x, point0.y), (point1.x, point1.y)], fill=line_color)
                draw_up_down = True

            if draw_left_right and draw_up_down and show_index:
                draw.text((point0.x, point0.y), f'{row},{col}', fill=index_color)

    return VImage.from_pil_image(pil_image)
