import numpy as np
import cv2 as cv

from vkit.image.type import (
    VImage,
    VImageKind,
)
from vkit.label.type import (
    VPointList,
    VPolygon,
    VImageScoreMap,
    VImageMask,
)
from .type import VImageGrid


def create_image_from_image_grid(image_grid: VImageGrid, image_kind: VImageKind):
    ndim = VImageKind.to_ndim(image_kind)
    if ndim == 2:
        shape = (image_grid.image_height, image_grid.image_width)
    elif ndim == 3:
        num_channels = VImageKind.to_num_channels(image_kind)
        assert num_channels
        shape = (image_grid.image_height, image_grid.image_width, num_channels)
    else:
        raise NotImplementedError()

    dtype = VImageKind.to_dtype(image_kind)
    mat = np.zeros(shape, dtype=dtype)
    return VImage(mat=mat, kind=image_kind)


def create_image_score_map_from_image_grid(image_grid):
    shape = (image_grid.image_height, image_grid.image_width)
    mat = np.zeros(shape, dtype=np.float32)
    return VImageScoreMap(mat=mat)


def create_image_mask_from_image_grid(image_grid):
    shape = (image_grid.image_height, image_grid.image_width)
    mat = np.zeros(shape, dtype=np.uint8)
    return VImageMask(mat=mat)


def get_np_y_x_points_within_polygon(polygon: VPolygon):
    box, np_points = polygon.to_bounding_box_with_np_points(shift_np_points=True)

    mask = np.zeros(box.shape, dtype=np.uint8)
    cv.fillPoly(mask, [np_points], 1)

    y, x = mask.nonzero()
    y += box.up
    x += box.left
    return y, x


def bilinear_interpolation(x, y, v11, v12, v21, v22):
    # https://en.wikipedia.org/wiki/Bilinear_interpolation
    # Normalized: x, y in [0.0, 1.0]; x1 = 0, y1 = 0, x2 = 1, y2 = 1.
    row0 = v11 * (1 - y) + v12 * y
    row1 = v21 * (1 - y) + v22 * y
    return (1 - x) * row0 + x * row1


def blend_polygon_from_src_to_dst_mat(
    src_mat,
    src_polygon: VPolygon,
    dst_mat,
    dst_polygon: VPolygon,
):
    src_polygon_points = src_polygon.to_np_array()
    dst_polygon_points = dst_polygon.to_np_array()

    # Only support 4-points polygon.
    assert src_polygon_points.shape == dst_polygon_points.shape == (4, 2)
    # Only support source polygon that is a box.
    assert src_polygon_points[0][1] == src_polygon_points[1][1]
    assert src_polygon_points[2][1] == src_polygon_points[3][1]
    assert src_polygon_points[0][0] == src_polygon_points[3][0]
    assert src_polygon_points[1][0] == src_polygon_points[2][0]

    # Calculate the corresponding points in the source.
    # https://docs.opencv.org/4.5.3/da/d54/group__imgproc__transform.html#ga20f62aa3235d869c9956436c870893ae
    trans_mat = cv.getPerspectiveTransform(
        dst_polygon_points.astype(np.float32),
        src_polygon_points.astype(np.float32),
        cv.DECOMP_SVD,
    )
    # (*, 2)
    dst_y, dst_x = get_np_y_x_points_within_polygon(dst_polygon)
    # (3, *)
    dst_for_trans_all_points = np.vstack((dst_x, dst_y, np.ones_like(dst_y)))
    # (3, *)
    src_all_points = np.matmul(trans_mat, dst_for_trans_all_points)

    # denominator could be zero, ignore the warning.
    denominator = src_all_points[2, :]
    with np.errstate(divide='ignore', invalid='ignore'):
        # (2, *)
        src_all_points = src_all_points[:2, :] / denominator
    # (*, 2)
    src_all_points = src_all_points.transpose()

    zero_mask = (denominator == 0).transpose()
    if zero_mask.any():
        non_zero_mask = ~zero_mask
        src_all_points = src_all_points[non_zero_mask]
        dst_y = dst_y[non_zero_mask]
        dst_x = dst_x[non_zero_mask]

    # Split to x/y array.
    src_y = src_all_points[:, 1]
    src_x = src_all_points[:, 0]

    # Clip to avoid out-of-bound.
    src_height = src_mat.shape[0]
    src_width = src_mat.shape[1]
    src_y = np.clip(src_y, 0, src_height - 1)
    src_x = np.clip(src_x, 0, src_width - 1)

    # Get floor & ceil for interpolation.
    src_y_floor = np.floor(src_y).astype(np.int32)
    src_x_floor = np.floor(src_x).astype(np.int32)

    src_y_ceil = np.ceil(src_y).astype(np.int32)
    src_x_ceil = np.ceil(src_x).astype(np.int32)

    src_ratio_y = src_y - src_y_floor
    src_ratio_x = src_x - src_x_floor

    if src_mat.ndim == 3:
        num_channels = src_mat.shape[2]
        src_ratio_y = np.tile(np.expand_dims(src_ratio_y, axis=-1), (1, 1, num_channels))
        src_ratio_x = np.tile(np.expand_dims(src_ratio_x, axis=-1), (1, 1, num_channels))

    dst_mat[dst_y, dst_x] = bilinear_interpolation(
        x=src_ratio_x,
        y=src_ratio_y,
        # Four images.
        v11=src_mat[src_y_floor, src_x_floor],
        v12=src_mat[src_y_ceil, src_x_floor],
        v21=src_mat[src_y_floor, src_x_ceil],
        v22=src_mat[src_y_ceil, src_x_ceil],
    )


def blend_src_to_dst_image(src_image, src_image_grid, dst_image_grid):
    dst_image = create_image_from_image_grid(dst_image_grid, src_image.kind)

    for _, src_polygon, dst_polygon in src_image_grid.zip_polygons(dst_image_grid):
        blend_polygon_from_src_to_dst_mat(
            src_image.mat,
            src_polygon,
            dst_image.mat,
            dst_polygon,
        )

    return dst_image


def blend_src_to_dst_image_score_map(src_image_score_map, src_image_grid, dst_image_grid):
    dst_image_score_map = create_image_score_map_from_image_grid(dst_image_grid)

    for _, src_polygon, dst_polygon in src_image_grid.zip_polygons(dst_image_grid):
        blend_polygon_from_src_to_dst_mat(
            src_image_score_map.mat,
            src_polygon,
            dst_image_score_map.mat,
            dst_polygon,
        )

    return dst_image_score_map


def blend_src_to_dst_image_mask(src_image_mask, src_image_grid, dst_image_grid):
    dst_image_mask = create_image_mask_from_image_grid(dst_image_grid)

    for _, src_polygon, dst_polygon in src_image_grid.zip_polygons(dst_image_grid):
        blend_polygon_from_src_to_dst_mat(
            src_image_mask.mat,
            src_polygon,
            dst_image_mask.mat,
            dst_polygon,
        )

    return dst_image_mask


def debug():
    from vkit.opt import get_data_folder
    folder = get_data_folder(__file__)

    from vkit.label.type import VPolygon, VPoint
    from vkit.label.visualization import visualize_points

    src_image = VImage.from_file(f'{folder}/Lenna.png')
    dst_image = src_image.clone()
    dst_image.mat.fill(255)

    blend_polygon_from_src_to_dst_mat(
        src_image.mat,
        VPolygon(
            points=VPointList([
                VPoint(y=10, x=10),
                VPoint(y=10, x=60),
                VPoint(y=60, x=60),
                VPoint(y=60, x=10),
            ]),
        ),
        dst_image.mat,
        VPolygon(
            points=VPointList([
                VPoint(y=10, x=50),
                VPoint(y=10, x=150),
                VPoint(y=60, x=60),
                VPoint(y=60, x=10),
            ]),
        ),
    )

    dst_image.to_file(f'{folder}/dst.png')

    # Mock grid.
    from .type import VImageGrid

    ys = list(range(0, src_image.height, src_image.height // 25))
    if ys[-1] != src_image.height - 1:
        ys.append(src_image.height - 1)
    xs = list(range(0, src_image.width, src_image.width // 25))
    if xs[-1] != src_image.width - 1:
        xs.append(src_image.width - 1)

    src_image_grid = VImageGrid(points_2d=[])
    for y in ys:
        points = []
        for x in xs:
            points.append(VPoint(y=y, x=x))
        src_image_grid.points_2d.append(points)

    import itertools

    visualize_points(src_image, itertools.chain.from_iterable(src_image_grid.points_2d
                                                              )).to_file(f'{folder}/src-grid.png')

    # Check identity.
    dst_image = blend_src_to_dst_image(src_image, src_image_grid, src_image_grid)
    # assert (dst_image.mat == src_image.mat).all()
    print(
        'identity ratio',
        (dst_image.mat == src_image.mat).sum() / (src_image.height * src_image.width * 3),
    )
    dst_image.to_file(f'{folder}/identity.png')

    # Random grid.
    import random

    # for idx, y in enumerate(ys):
    #     if idx == 0 or idx == len(ys) - 1:
    #         continue
    #     if random.random() < 0.5:
    #         ys[idx] = y + src_image.height // 50
    #     else:
    #         ys[idx] = y - src_image.height // 50

    # for idx, x in enumerate(xs):
    #     if idx == 0 or idx == len(xs) - 1:
    #         continue
    #     if random.random() < 0.5:
    #         xs[idx] = x + src_image.width // 50
    #     else:
    #         xs[idx] = x - src_image.width // 50

    # dst_image_grid = VImageGrid(points_2d=[])
    # for y in ys:
    #     points = []
    #     for x in xs:
    #         points.append(VPoint(y=y, x=x))
    #     dst_image_grid.points_2d.append(points)

    dst_image_grid = VImageGrid(points_2d=[])
    for y in ys:
        points = []
        for x in xs:
            if 0 < y < src_image.height - 1:
                if random.random() < 0.5:
                    ry = y + src_image.height // 150
                else:
                    ry = y - src_image.height // 150
            else:
                ry = y

            if 0 < x < src_image.width - 1:
                if random.random() < 0.5:
                    rx = x + src_image.width // 150
                else:
                    rx = x - src_image.width // 150
            else:
                rx = x
            points.append(VPoint(y=ry, x=rx))

        dst_image_grid.points_2d.append(points)

    dst_image = blend_src_to_dst_image(src_image, src_image_grid, dst_image_grid)
    dst_image.to_file(f'{folder}/random.png')

    dst_image = blend_src_to_dst_image(src_image, src_image_grid, dst_image_grid)
    visualize_points(
        dst_image,
        itertools.chain.from_iterable(dst_image_grid.points_2d),
    ).to_file(f'{folder}/random-grid.png')


def debug_cv():
    dst_polygon_points = np.array(
        [
            [51., 90.],
            [60., 90.],
            [61., 100.],
            [51., 100.],
        ],
        dtype=np.float32,
    )

    src_polygon_points = np.array(
        [
            [50., 90.],
            [60., 90.],
            [60., 100.],
            [50., 100.],
        ],
        dtype=np.float32,
    )
    trans_mat = cv.getPerspectiveTransform(
        dst_polygon_points,
        src_polygon_points,
        # cv.DECOMP_SVD,
    )
    print(trans_mat)
