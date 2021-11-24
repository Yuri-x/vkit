from typing import Sequence
import math

import attr
import numpy as np
import numpy.typing as npt
import cv2 as cv

from vkit.image.type import VImage
from vkit.label.type import VImageScoreMap, VImageMask, VPointList, VPolygon
from .interface import GeometricDistortion


def affine_mat(state, mat):
    if state.trans_mat.shape[0] == 2:
        return cv.warpAffine(mat, state.trans_mat, state.dsize)
    else:
        assert state.trans_mat.shape[0] == 3
        return cv.warpPerspective(mat, state.trans_mat, state.dsize)


def affine_np_points(state, np_points: npt.NDArray):
    # (*, 2)
    np_points = np_points.transpose()
    # (*, 3)
    np_points = np.concatenate((
        np_points,
        np.ones((1, np_points.shape[1]), dtype=np.int32),
    ))

    new_np_points = np.matmul(state.trans_mat, np_points)
    if state.trans_mat.shape[0] == 2:
        # new_np_points.shape is (2, *), do nothing.
        pass

    else:
        assert state.trans_mat.shape[0] == 3
        new_np_points = new_np_points[:2, :] / new_np_points[2, :]

    return new_np_points.transpose()


def affine_points(state, points: VPointList):
    new_np_points = affine_np_points(state, points.to_np_array())
    return VPointList.from_np_array(new_np_points)


def affine_polygons(state, polygons: Sequence[VPolygon]):
    points_ranges = []
    points = VPointList()
    for polygon in polygons:
        points_ranges.append((len(points), len(points) + len(polygon.points)))
        points.extend(polygon.points)

    new_np_points = affine_np_points(state, points.to_np_array())
    new_polygons = []
    for begin, end in points_ranges:
        new_polygons.append(VPolygon.from_xy_pairs(new_np_points[begin:end]))

    return new_polygons


@attr.define
class ShearHoriConfig:
    # angle: int, [-90, 90], positive value for rightward direction.
    angle: int


class ShearHoriState:

    def __init__(self, config, shape):
        tan_phi = math.tan(math.radians(config.angle))

        height, width = shape
        shift_x = abs(height * tan_phi)
        self.dsize = (math.ceil(width + shift_x), height)

        if config.angle < 0:
            # Shear left & the negative part.
            self.trans_mat = np.array([
                (1, -tan_phi, 0),
                (0, 1, 0),
            ], dtype=np.float32)
        elif config.angle > 0:
            # Shear right.
            self.trans_mat = np.array([
                (1, -tan_phi, shift_x),
                (0, 1, 0),
            ], dtype=np.float32)
        else:
            # No need to transform.
            self.trans_mat = None
            self.dsize = None


def shear_hori_mat(config, state, mat):
    return mat if config.angle == 0 else affine_mat(state, mat)


def shear_hori_image(image, config, state):
    return VImage(mat=shear_hori_mat(config, state, image.mat))


def shear_hori_image_score_map(config, state, image_score_map):
    return VImageScoreMap(mat=shear_hori_mat(config, state, image_score_map.mat))


def shear_hori_image_mask(config, state, image_mask):
    return VImageMask(mat=shear_hori_mat(config, state, image_mask.mat))


def shear_hori_points(config, state, shape, point):
    return point if config.angle == 0 else affine_points(state, point)


def shear_hori_polygons(config, state, shape, polygons):
    return polygons if config.angle == 0 else affine_polygons(state, polygons)


shear_hori = GeometricDistortion(
    config_cls=ShearHoriConfig,
    state_cls=ShearHoriState,
    func_image=shear_hori_image,
    func_image_mask=shear_hori_image_mask,
    func_image_score_map=shear_hori_image_score_map,
    func_active_image_mask=None,
    func_point=None,
    func_points=shear_hori_points,
    func_polygon=None,
    func_polygons=shear_hori_polygons,
)


@attr.define
class ShearVertConfig:
    # angle: int, [-90, 90], positive value for upward direction.
    angle: int


class ShearVertState:

    def __init__(self, config, shape):
        tan_phi = math.tan(math.radians(config.angle))

        height, width = shape
        shift_y = abs(width * tan_phi)
        self.dsize = (width, math.ceil(height + shift_y))

        if config.angle < 0:
            # Shear down & the negative part.
            self.trans_mat = np.array([
                (1, 0, 0),
                (-tan_phi, 1, 0),
            ], dtype=np.float32)
        elif config.angle > 0:
            # Shear up.
            self.trans_mat = np.array([
                (1, 0, 0),
                (-tan_phi, 1, shift_y),
            ], dtype=np.float32)
        else:
            # No need to transform.
            self.trans_mat = None
            self.dsize = None


def shear_vert_mat(config, state, mat):
    return mat if config.angle == 0 else affine_mat(state, mat)


def shear_vert_image(config, state, image):
    return VImage(mat=shear_vert_mat(config, state, image.mat))


def shear_vert_image_score_map(config, state, image_score_map):
    return VImageScoreMap(mat=shear_vert_mat(config, state, image_score_map.mat))


def shear_vert_image_mask(config, state, image_mask):
    return VImageMask(mat=shear_vert_mat(config, state, image_mask.mat))


def shear_vert_points(config, state, shape, point):
    return point if config.angle == 0 else affine_points(state, point)


def shear_vert_polygons(config, state, shape, polygons):
    return polygons if config.angle == 0 else affine_polygons(state, polygons)


shear_vert = GeometricDistortion(
    config_cls=ShearVertConfig,
    state_cls=ShearVertState,
    func_image=shear_vert_image,
    func_image_mask=shear_vert_image_mask,
    func_image_score_map=shear_vert_image_score_map,
    func_active_image_mask=None,
    func_point=None,
    func_points=shear_vert_points,
    func_polygon=None,
    func_polygons=shear_vert_polygons,
)


@attr.define
class RotateConfig:
    # angle: int, [0, 360], clockwise angle.
    angle: int


class RotateState:

    def __init__(self, config, shape):
        height, width = shape

        angle = config.angle % 360
        rad = math.radians(angle)

        shift_x = 0
        shift_y = 0

        if rad <= math.pi / 2:
            # 3-4 quadrant.
            shift_x = height * math.sin(rad)

            dst_width = height * math.sin(rad) + width * math.cos(rad)
            dst_height = height * math.cos(rad) + width * math.sin(rad)

        elif rad <= math.pi:
            # 2-3 quadrant.
            shift_rad = rad - math.pi / 2

            shift_x = width * math.sin(shift_rad) + height * math.cos(shift_rad)
            shift_y = height * math.sin(shift_rad)

            dst_width = shift_x
            dst_height = shift_y + width * math.cos(shift_rad)

        elif rad < math.pi * 3 / 2:
            # 1-2 quadrant.
            shift_rad = rad - math.pi

            shift_x = width * math.cos(shift_rad)
            shift_y = width * math.sin(shift_rad) + height * math.cos(shift_rad)

            dst_width = shift_x + height * math.sin(shift_rad)
            dst_height = shift_y

        else:
            # 1-4 quadrant.
            shift_rad = rad - math.pi * 3 / 2

            shift_y = width * math.cos(shift_rad)

            dst_width = width * math.sin(shift_rad) + height * math.cos(shift_rad)
            dst_height = shift_y + height * math.sin(shift_rad)

        shift_x = math.ceil(shift_x)
        shift_y = math.ceil(shift_y)

        self.trans_mat = np.array(
            [
                (math.cos(rad), -math.sin(rad), shift_x),
                (math.sin(rad), math.cos(rad), shift_y),
            ],
            dtype=np.float32,
        )

        self.dsize = (math.ceil(dst_width), math.ceil(dst_height))


def rotate_mat(config, state, mat):
    return mat if config.angle == 0 else affine_mat(state, mat)


def rotate_image(config, state, image):
    return VImage(mat=rotate_mat(config, state, image.mat))


def rotate_image_score_map(config, state, image_score_map):
    return VImageScoreMap(mat=rotate_mat(config, state, image_score_map.mat))


def rotate_image_mask(config, state, image_mask):
    return VImageMask(mat=rotate_mat(config, state, image_mask.mat))


def rotate_points(config, state, shape, point):
    return point if config.angle == 0 else affine_points(state, point)


def rotate_polygons(config, state, shape, polygons):
    return polygons if config.angle == 0 else affine_polygons(state, polygons)


rotate = GeometricDistortion(
    config_cls=RotateConfig,
    state_cls=RotateState,
    func_image=rotate_image,
    func_image_mask=rotate_image_mask,
    func_image_score_map=rotate_image_score_map,
    func_active_image_mask=None,
    func_point=None,
    func_points=rotate_points,
    func_polygon=None,
    func_polygons=rotate_polygons,
)


@attr.define
class SkewHoriConfig:
    # (-1.0, 0.0], shrink the left side.
    # [0.0, 1.0), shrink the right side.
    # The larger abs(ratio), the more to shrink.
    ratio: float


class SkewHoriState:

    def __init__(self, config, shape):
        height, width = shape

        src_xy_pairs = [
            (0, 0),
            (width - 1, 0),
            (width - 1, height - 1),
            (0, height - 1),
        ]

        shrink_size = round(height * abs(config.ratio))
        shrink_up = shrink_size // 2
        shrink_down = shrink_size - shrink_up

        if config.ratio < 0:
            dst_xy_pairs = [
                (0, shrink_up),
                (width - 1, 0),
                (width - 1, height - 1),
                (0, height - shrink_down - 1),
            ]
        else:
            dst_xy_pairs = [
                (0, 0),
                (width - 1, shrink_up),
                (width - 1, height - shrink_down - 1),
                (0, height - 1),
            ]

        self.trans_mat = cv.getPerspectiveTransform(
            np.array(src_xy_pairs, dtype=np.float32),
            np.array(dst_xy_pairs, dtype=np.float32),
            cv.DECOMP_SVD,
        )
        self.dsize = shape


def skew_hori_mat(config, state, mat):
    return mat if config.ratio == 0 else affine_mat(state, mat)


def skew_hori_image(config, state, image):
    return VImage(mat=skew_hori_mat(config, state, image.mat))


def skew_hori_image_score_map(config, state, image_score_map):
    return VImageScoreMap(mat=skew_hori_mat(config, state, image_score_map.mat))


def skew_hori_image_mask(config, state, image_mask):
    return VImageMask(mat=skew_hori_mat(config, state, image_mask.mat))


def skew_hori_points(config, state, shape, point):
    return point if config.angle == 0 else affine_points(state, point)


def skew_hori_polygons(config, state, shape, polygons):
    return polygons if config.ratio == 0 else affine_polygons(state, polygons)


skew_hori = GeometricDistortion(
    config_cls=SkewHoriConfig,
    state_cls=SkewHoriState,
    func_image=skew_hori_image,
    func_image_mask=skew_hori_image_mask,
    func_image_score_map=skew_hori_image_score_map,
    func_active_image_mask=None,
    func_point=None,
    func_points=skew_hori_points,
    func_polygon=None,
    func_polygons=skew_hori_polygons,
)


@attr.define
class SkewVertConfig:
    # (-1.0, 0.0], shrink the up side.
    # [0.0, 1.0), shrink the down side.
    # The larger abs(ratio), the more to shrink.
    ratio: float


class SkewVertState:

    def __init__(self, config, shape):
        height, width = shape

        src_xy_pairs = [
            (0, 0),
            (width - 1, 0),
            (width - 1, height - 1),
            (0, height - 1),
        ]

        shrink_size = round(width * abs(config.ratio))
        shrink_left = shrink_size // 2
        shrink_right = shrink_size - shrink_left

        if config.ratio < 0:
            dst_xy_pairs = [
                (shrink_left, 0),
                (width - shrink_right - 1, 0),
                (width - 1, height - 1),
                (0, height - 1),
            ]
        else:
            dst_xy_pairs = [
                (0, 0),
                (width - 1, 0),
                (width - shrink_right - 1, height - 1),
                (shrink_right, height - 1),
            ]

        self.trans_mat = cv.getPerspectiveTransform(
            np.array(src_xy_pairs, dtype=np.float32),
            np.array(dst_xy_pairs, dtype=np.float32),
            cv.DECOMP_SVD,
        )
        self.dsize = shape


def skew_vert_mat(config, state, mat):
    return mat if config.ratio == 0 else affine_mat(state, mat)


def skew_vert_image(config, state, image):
    return VImage(mat=skew_vert_mat(config, state, image.mat))


def skew_vert_image_score_map(config, state, image_score_map):
    return VImageScoreMap(mat=skew_vert_mat(config, state, image_score_map.mat))


def skew_vert_image_mask(config, state, image_mask):
    return VImageMask(mat=skew_vert_mat(config, state, image_mask.mat))


def skew_vert_points(config, state, shape, point):
    return point if config.angle == 0 else affine_points(state, point)


def skew_vert_polygons(config, state, shape, polygons):
    return polygons if config.ratio == 0 else affine_polygons(state, polygons)


skew_vert = GeometricDistortion(
    config_cls=SkewVertConfig,
    state_cls=SkewVertState,
    func_image=skew_vert_image,
    func_image_mask=skew_vert_image_mask,
    func_image_score_map=skew_vert_image_score_map,
    func_active_image_mask=None,
    func_point=None,
    func_points=skew_vert_points,
    func_polygon=None,
    func_polygons=skew_vert_polygons,
)


def debug():
    from vkit.opt import get_data_folder
    folder = get_data_folder(__file__)

    from vkit.label.type import VPoint, VPolygon
    from .interface import debug_geometric_distortion

    config = ShearHoriConfig(30)

    src_polygon = VPolygon(
        VPointList([
            VPoint(y=100, x=100),
            VPoint(y=100, x=300),
            VPoint(y=300, x=300),
            VPoint(y=300, x=100),
        ])
    )

    for tag, config, geometric_distortion in [
        ('shear-hori-p-30', ShearHoriConfig(30), shear_hori),
        ('shear-hori-n-30', ShearHoriConfig(-30), shear_hori),
        ('shear-vert-p-30', ShearVertConfig(30), shear_vert),
        ('shear-vert-n-30', ShearVertConfig(-30), shear_vert),
        ('rotate-p-30', RotateConfig(30), rotate),
        ('rotate-p-120', RotateConfig(120), rotate),
        ('rotate-p-210', RotateConfig(210), rotate),
        ('rotate-p-300', RotateConfig(300), rotate),
        ('rotate-n-30', RotateConfig(-30), rotate),
        ('skew-hori-p-0.2', SkewHoriConfig(0.2), skew_hori),
        ('skew-hori-n-0.2', SkewHoriConfig(-0.2), skew_hori),
        ('skew-vert-p-0.2', SkewVertConfig(0.2), skew_vert),
        ('skew-vert-n-0.2', SkewVertConfig(-0.2), skew_vert),
    ]:
        debug_geometric_distortion(
            tag,
            geometric_distortion,
            config,
            src_polygon,
            folder,
            'Lenna.png',
        )
