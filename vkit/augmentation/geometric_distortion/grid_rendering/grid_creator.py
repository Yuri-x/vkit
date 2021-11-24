from itertools import chain

from vkit.label.type import VPoint
from .type import VImageGrid
from .interface import PointProjector


def create_src_image_grid(height, width, grid_size):
    ys = list(range(0, height, grid_size))
    if ys[-1] != height - 1:
        ys.append(height - 1)

    xs = list(range(0, width, grid_size))
    if xs[-1] != width - 1:
        xs.append(width - 1)

    points_2d = []
    for y in ys:
        points = []
        for x in xs:
            points.append(VPoint(y=y, x=x))
        points_2d.append(points)

    return VImageGrid(points_2d=points_2d)


def create_dst_image_grid_and_shift_amounts_and_rescale_ratios(
    src_image_grid,
    point_projector_or_dst_points_2d,
    rescale_as_src=True,
):
    dst_points_2d = []

    if isinstance(point_projector_or_dst_points_2d, PointProjector):
        point_projector = point_projector_or_dst_points_2d

        src_flatten_points = src_image_grid.flatten_points
        num_src_flatten_points = len(src_flatten_points)

        dst_flatten_points = point_projector.project_points(src_flatten_points)

        assert len(dst_flatten_points) == num_src_flatten_points
        dst_points_2d = []
        for begin in range(0, num_src_flatten_points, src_image_grid.num_cols):
            dst_points_2d.append(dst_flatten_points[begin:begin + src_image_grid.num_cols])

    else:
        dst_points_2d = point_projector_or_dst_points_2d
        assert len(dst_points_2d) == src_image_grid.num_rows
        assert len(dst_points_2d[0]) == src_image_grid.num_cols

    y_min = dst_points_2d[0][0].y
    y_max = y_min
    x_min = dst_points_2d[0][0].x
    x_max = x_min

    for point in chain.from_iterable(dst_points_2d):
        y_min = min(y_min, point.y)
        y_max = max(y_max, point.y)
        x_min = min(x_min, point.x)
        x_max = max(x_max, point.x)

    shift_amount_y = y_min
    shift_amount_x = x_min

    for point in chain.from_iterable(dst_points_2d):
        point.y -= shift_amount_y
        point.x -= shift_amount_x

    src_image_height = src_image_grid.image_height
    src_image_width = src_image_grid.image_width

    rescale_ratio_y = 1.0
    rescale_ratio_x = 1.0

    if rescale_as_src:
        raw_dst_image_grid = VImageGrid(points_2d=dst_points_2d)
        raw_dst_image_height = raw_dst_image_grid.image_height
        raw_dst_image_width = raw_dst_image_grid.image_width
        del raw_dst_image_grid

        rescale_ratio_y = (src_image_height - 1) / (raw_dst_image_height - 1)
        rescale_ratio_x = (src_image_width - 1) / (raw_dst_image_width - 1)

        for point in chain.from_iterable(dst_points_2d):
            if raw_dst_image_height != src_image_height:
                point.y = round(point.y * rescale_ratio_y)
            if raw_dst_image_width != src_image_width:
                point.x = round(point.x * rescale_ratio_x)

    dst_image_grid = VImageGrid(points_2d=dst_points_2d)

    if rescale_as_src:
        assert dst_image_grid.image_height == src_image_height
        assert dst_image_grid.image_width == src_image_width

    shift_amounts = (shift_amount_y, shift_amount_x)
    rescale_ratios = (rescale_ratio_y, rescale_ratio_x)
    return dst_image_grid, shift_amounts, rescale_ratios


def create_dst_image_grid(
    src_image_grid,
    point_projector_or_dst_points_2d,
    rescale_as_src=True,
):
    dst_image_grid, _, _ = create_dst_image_grid_and_shift_amounts_and_rescale_ratios(
        src_image_grid=src_image_grid,
        point_projector_or_dst_points_2d=point_projector_or_dst_points_2d,
        rescale_as_src=rescale_as_src,
    )
    return dst_image_grid
