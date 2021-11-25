from typing import Callable, Sequence, Optional, Tuple
import math

import attr
import cv2 as cv
import numpy as np
import numpy.typing as npt

from vkit.label.type import VPoint, VPointList
from .grid_rendering.type import VImageGrid
from .grid_rendering.grid_creator import create_src_image_grid
from .grid_rendering.interface import PointProjector
from .interface import GeometricDistortionImageGridBased, StateImageGridBased


class Point2dTo3dStrategy:

    def generate_np_3d_points(self, points: VPointList) -> npt.NDArray:
        raise NotImplementedError()


@attr.define
class CameraModelConfig:
    rotation_unit_vec: Sequence[float]
    rotation_theta: float
    principal_point: Optional[Sequence[float]] = None
    focal_length: Optional[float] = None
    camera_distance: Optional[float] = None


class CameraModel:

    @staticmethod
    def generate_rotation_vec(rotation_unit_vec, rotation_theta):
        return rotation_unit_vec * rotation_theta

    @staticmethod
    def generate_translation_vec(
        rotation_vec,
        camera_distance,
        principal_point,
        return_rotation_mat=False,
    ):
        rotation_mat, _ = cv.Rodrigues(rotation_vec)
        rotation_mat_inv = rotation_mat.transpose()

        c2pp_vec = np.array([0, 0, camera_distance], dtype=np.float32).reshape(-1, 1)
        c2pp_before_rotation_vec = np.matmul(
            rotation_mat_inv,
            c2pp_vec,
        )
        c2o_before_rotation_vec = c2pp_before_rotation_vec - principal_point

        translation_vec = np.matmul(
            rotation_mat,
            c2o_before_rotation_vec.reshape(-1, 1),
        )
        if return_rotation_mat:
            return translation_vec, rotation_mat
        else:
            return translation_vec

    @staticmethod
    def generate_extrinsic_mat(rotation_unit_vec, rotation_theta, camera_distance, principal_point):
        rotation_vec = CameraModel.generate_rotation_vec(rotation_unit_vec, rotation_theta)
        translation_vec, rotation_mat = CameraModel.generate_translation_vec(
            rotation_vec,
            camera_distance,
            principal_point,
            return_rotation_mat=True,
        )
        extrinsic_mat = np.hstack((rotation_mat, translation_vec.reshape((-1, 1))))
        return extrinsic_mat

    @staticmethod
    def generate_intrinsic_mat(focal_length):
        return np.array(
            [
                [focal_length, 0, 0],
                [0, focal_length, 0],
                [0, 0, 1],
            ],
            dtype=np.float32,
        )

    @staticmethod
    def prep_rotation_unit_vec(rotation_unit_vec):
        return np.asarray(rotation_unit_vec, dtype=np.float32)

    @staticmethod
    def prep_rotation_theta(rotation_theta):
        return np.clip(rotation_theta, -89, 89) / 180 * np.pi

    @staticmethod
    def prep_principal_point(principal_point):
        if len(principal_point) == 2:
            principal_point.append(0)
        principal_point = np.asarray(principal_point, dtype=np.float32).reshape(-1, 1)
        return principal_point

    def __init__(self, config: CameraModelConfig):
        assert config.focal_length
        assert config.camera_distance
        assert config.principal_point

        rotation_unit_vec = self.prep_rotation_unit_vec(config.rotation_unit_vec)
        rotation_theta = self.prep_rotation_theta(config.rotation_theta)
        self.rotation_vec = self.generate_rotation_vec(rotation_unit_vec, rotation_theta)

        principal_point = self.prep_principal_point(list(config.principal_point))

        self.translation_vec = self.generate_translation_vec(
            self.rotation_vec,
            config.camera_distance,
            principal_point,
        )
        self.intrinsic_mat = self.generate_intrinsic_mat(config.focal_length)

    def project_np_points_from_3d_to_2d(self, np_3d_points):
        camera_2d_points, _ = cv.projectPoints(
            np_3d_points,
            self.rotation_vec,
            self.translation_vec,
            self.intrinsic_mat,
            np.zeros(5),
        )
        return camera_2d_points.reshape(-1, 2)


class CameraPointProjector(PointProjector):

    def __init__(self, point_2d_to_3d_strategy, camera_model_config):
        self.point_2d_to_3d_strategy = point_2d_to_3d_strategy
        self.camera_model = CameraModel(camera_model_config)

    def project_points(self, src_points: VPointList):
        np_3d_points = self.point_2d_to_3d_strategy.generate_np_3d_points(src_points)
        camera_2d_points = self.camera_model.project_np_points_from_3d_to_2d(np_3d_points)
        return VPointList.from_np_array(camera_2d_points)

    def project_point(self, src_point: VPoint):
        return self.project_points(VPointList.from_point(src_point))[0]


class CameraOperationState(StateImageGridBased):

    @staticmethod
    def complete_camera_model_config(
        height: int,
        width: int,
        src_image_grid: VImageGrid,
        point_2d_to_3d_strategy: Point2dTo3dStrategy,
        camera_model_config: CameraModelConfig,
    ):
        if camera_model_config.principal_point \
                and camera_model_config.focal_length \
                and camera_model_config.camera_distance:
            return camera_model_config

        # Make a copy.
        camera_model_config = attr.evolve(camera_model_config)

        if not camera_model_config.principal_point:
            camera_model_config.principal_point = [height // 2, width // 2]

        if not camera_model_config.focal_length:
            camera_model_config.focal_length = max(height, width)

        if not camera_model_config.camera_distance:
            # Initial guess.
            camera_distance = camera_model_config.focal_length

            # To camera coordinate.
            extrinsic_mat = CameraModel.generate_extrinsic_mat(
                CameraModel.prep_rotation_unit_vec(camera_model_config.rotation_unit_vec),
                CameraModel.prep_rotation_theta(camera_model_config.rotation_theta),
                camera_distance,
                CameraModel.prep_principal_point(list(camera_model_config.principal_point)),
            )
            intrinsic_mat = CameraModel.generate_intrinsic_mat(camera_model_config.focal_length)

            np_3d_points = point_2d_to_3d_strategy.generate_np_3d_points(
                src_image_grid.flatten_points
            )
            np_3d_points = np.matmul(
                extrinsic_mat,
                np.hstack((np_3d_points, np.ones((np_3d_points.shape[0], 1)))).transpose(),
            )
            np_3d_points = np.matmul(
                intrinsic_mat,
                np_3d_points,
            )

            # Adjust camera distance.
            pos_zs = np_3d_points[2]
            delta = pos_zs.min() - camera_distance
            # Add one to make sure one point touch the plane.
            camera_model_config.camera_distance = camera_distance - delta + 1

        return camera_model_config

    def __init__(
        self,
        height,
        width,
        grid_size,
        point_2d_to_3d_strategy,
        camera_model_config,
    ):
        src_image_grid = create_src_image_grid(height, width, grid_size)

        camera_model_config = self.complete_camera_model_config(
            height,
            width,
            src_image_grid,
            point_2d_to_3d_strategy,
            camera_model_config,
        )
        point_projector = CameraPointProjector(
            point_2d_to_3d_strategy,
            camera_model_config,
        )

        super().__init__(src_image_grid, point_projector)


@attr.define
class CameraCubicCurveConfig:
    curve_alpha: float
    curve_beta: float
    # Clockwise, [0, 180]
    curve_direction: float
    curve_scale: float
    camera_model_config: CameraModelConfig
    grid_size: int


class CameraCubicCurvePoint2dTo3dStrategy(Point2dTo3dStrategy):

    def __init__(self, height, width, curve_alpha, curve_beta, curve_direction, curve_scale):
        # Plane area.
        self.height = height
        self.width = width

        # Curve endpoint slopes.
        self.curve_alpha = math.tan(np.clip(curve_alpha, -80, 80) / 180 * np.pi)
        self.curve_beta = math.tan(np.clip(curve_beta, -80, 80) / 180 * np.pi)

        # Plane projection direction.
        self.curve_direction = (curve_direction % 180) / 180 * np.pi

        self.rotation_mat = np.array(
            [
                [
                    math.cos(self.curve_direction),
                    math.sin(self.curve_direction),
                ],
                [
                    -math.sin(self.curve_direction),
                    math.cos(self.curve_direction),
                ],
            ],
            dtype=np.float32,
        )

        corners = np.array(
            [
                [0, 0],
                [self.width - 1, 0],
                [self.width - 1, self.height - 1],
                [0, self.height - 1],
            ],
            dtype=np.float32,
        )
        rotated_corners = np.matmul(self.rotation_mat, corners.transpose())
        self.plane_projection_min = rotated_corners[0].min()
        self.plane_projection_range = rotated_corners[0].max() - self.plane_projection_min

        self.curve_scale = curve_scale

    def generate_np_3d_points(self, points: VPointList) -> npt.NDArray:
        np_2d_points = points.to_np_array().astype(np.float32)

        # Project based on theta.
        plane_projected_points = np.matmul(self.rotation_mat, np_2d_points.transpose())
        plane_projected_xs = plane_projected_points[0]
        plane_projected_ratios = (
            plane_projected_xs - self.plane_projection_min
        ) / self.plane_projection_range

        # Axis-z.
        poly = np.array([
            self.curve_alpha + self.curve_beta,
            -2 * self.curve_alpha - self.curve_beta,
            self.curve_alpha,
            0,
        ])
        pos_zs = np.polyval(poly, plane_projected_ratios)
        pos_zs = pos_zs * self.plane_projection_range * self.curve_scale

        np_3d_points = np.hstack((np_2d_points, pos_zs.reshape((-1, 1))))
        return np_3d_points


class CameraCubicCurveState(CameraOperationState):

    def __init__(self, config: CameraCubicCurveConfig, shape: Tuple[int, int]):
        height, width = shape

        super().__init__(
            height,
            width,
            config.grid_size,
            CameraCubicCurvePoint2dTo3dStrategy(
                height,
                width,
                config.curve_alpha,
                config.curve_beta,
                config.curve_direction,
                config.curve_scale,
            ),
            config.camera_model_config,
        )


camera_cubic_curve = GeometricDistortionImageGridBased(
    config_cls=CameraCubicCurveConfig,
    state_cls=CameraCubicCurveState,
)


class CameraPlaneLinePoint2dTo3dStrategy(Point2dTo3dStrategy):

    def __init__(
        self,
        height,
        width,
        point: Tuple[float, float],
        direction: float,
        perturb_vec: Tuple[float, float, float],
        alpha: float,
        weights_func: Callable[[npt.NDArray, float], npt.NDArray],
    ):
        # Plane area.
        self.height = height
        self.width = width

        # Define a line.
        self.point = np.array(point, dtype=np.float32)
        direction = (direction % 180) / 180 * np.pi
        cos_theta = np.cos(direction)
        sin_theta = np.sin(direction)
        self.line_params_a_b = np.array([sin_theta, -cos_theta], dtype=np.float32)
        self.line_param_c = -self.point[0] * sin_theta + self.point[1] * cos_theta

        # For weight calculationn.
        self.distance_max = np.sqrt(height**2 + width**2)
        self.alpha = alpha
        self.weights_func = weights_func

        # Deformation vector.
        self.perturb_vec = np.array(perturb_vec, dtype=np.float32)

    def generate_np_3d_points(self, points: VPointList) -> npt.NDArray:
        np_2d_points = points.to_np_array().astype(np.float32)

        # Calculate weights.
        distances = np.abs((np_2d_points * self.line_params_a_b).sum(axis=1) + self.line_param_c)
        norm_distances = distances / self.distance_max
        weights = self.weights_func(norm_distances, self.alpha)

        # Add weighted fold vector.
        np_3d_points = np.hstack(
            (np_2d_points, np.zeros((np_2d_points.shape[0], 1), dtype=np.float32))
        )
        np_3d_points += weights.reshape(-1, 1) * self.perturb_vec
        return np_3d_points


@attr.define
class CameraPlaneLineFoldConfig:
    fold_point: Tuple[float, float]
    # Clockwise, [0, 180]
    fold_direction: float
    fold_perturb_vec: Tuple[float, float, float]
    fold_alpha: float
    camera_model_config: CameraModelConfig
    grid_size: int


class CameraPlaneLineFoldState(CameraOperationState):

    @staticmethod
    def weights_func(norm_distances: npt.NDArray, alpha: float):
        return alpha / (norm_distances + alpha)  # type: ignore

    def __init__(self, config: CameraPlaneLineFoldConfig, shape: Tuple[int, int]):
        height, width = shape

        super().__init__(
            height,
            width,
            config.grid_size,
            CameraPlaneLinePoint2dTo3dStrategy(
                height=height,
                width=width,
                point=config.fold_point,
                direction=config.fold_direction,
                perturb_vec=config.fold_perturb_vec,
                alpha=config.fold_alpha,
                weights_func=self.weights_func,
            ),
            config.camera_model_config,
        )


camera_plane_line_fold = GeometricDistortionImageGridBased(
    config_cls=CameraPlaneLineFoldConfig,
    state_cls=CameraPlaneLineFoldState,
)


@attr.define
class CameraPlaneLineCurveConfig:
    curve_point: Tuple[float, float]
    # Clockwise, [0, 180]
    curve_direction: float
    curve_perturb_vec: Tuple[float, float, float]
    curve_alpha: float
    camera_model_config: CameraModelConfig
    grid_size: int


class CameraPlaneLineCurveState(CameraOperationState):

    @staticmethod
    def weights_func(norm_distances: npt.NDArray, alpha: float):
        return 1 - norm_distances**alpha  # type: ignore

    def __init__(self, config: CameraPlaneLineCurveConfig, shape: Tuple[int, int]):
        height, width = shape

        super().__init__(
            height,
            width,
            config.grid_size,
            CameraPlaneLinePoint2dTo3dStrategy(
                height=height,
                width=width,
                point=config.curve_point,
                direction=config.curve_direction,
                perturb_vec=config.curve_perturb_vec,
                alpha=config.curve_alpha,
                weights_func=self.weights_func,
            ),
            config.camera_model_config,
        )


camera_plane_line_curve = GeometricDistortionImageGridBased(
    config_cls=CameraPlaneLineCurveConfig,
    state_cls=CameraPlaneLineCurveState,
)


def debug_cubic_curve():
    from vkit.opt import get_data_folder
    folder = get_data_folder(__file__)

    from vkit.label.type import VPolygon, VPoint
    from .interface import debug_geometric_distortion

    config = CameraCubicCurveConfig(
        curve_alpha=60,
        curve_beta=-60,
        curve_direction=45,
        curve_scale=1.0,
        camera_model_config=CameraModelConfig(
            # focal_length=200,
            rotation_unit_vec=[1.0, 0.0, 0.0],
            rotation_theta=0,
            # camera_distance=200,
            # principal_point=[220, 220],
        ),
        grid_size=10,
    )

    src_polygon = VPolygon(
        VPointList([
            VPoint(y=100, x=100),
            VPoint(y=100, x=300),
            VPoint(y=300, x=300),
            VPoint(y=300, x=100),
        ])
    )

    state = debug_geometric_distortion(
        'camera_cubic_curve',
        camera_cubic_curve,
        config,
        src_polygon,
        folder,
        'Lenna.png',
    )
    assert state

    from .grid_rendering.visualization import visualize_image_grid

    visualize_image_grid(state.src_image_grid).to_file(f'{folder}/camera_cubic_curve-src-grid.png')
    visualize_image_grid(state.dst_image_grid).to_file(f'{folder}/camera_cubic_curve-dst-grid.png')


def debug_plane_line_fold():
    from vkit.opt import get_data_folder
    folder = get_data_folder(__file__)

    from vkit.label.type import VPolygon, VPoint
    from .interface import debug_geometric_distortion

    config = CameraPlaneLineFoldConfig(
        fold_point=(300, 300),
        fold_direction=30,
        fold_perturb_vec=(50, 0, 200),
        fold_alpha=0.5,
        camera_model_config=CameraModelConfig(
            rotation_unit_vec=[1.0, 0.0, 0.0],
            rotation_theta=30,
        ),
        grid_size=10,
    )

    src_polygon = VPolygon(
        VPointList([
            VPoint(y=100, x=100),
            VPoint(y=100, x=300),
            VPoint(y=300, x=300),
            VPoint(y=300, x=100),
        ])
    )

    state = debug_geometric_distortion(
        'camera_plane_line_fold',
        camera_plane_line_fold,
        config,
        src_polygon,
        folder,
        'Lenna.png',
    )
    assert state

    from .grid_rendering.visualization import visualize_image_grid

    visualize_image_grid(state.src_image_grid
                         ).to_file(f'{folder}/camera_plane_line_fold-src-grid.png')
    visualize_image_grid(state.dst_image_grid
                         ).to_file(f'{folder}/camera_plane_line_fold-dst-grid.png')


def debug_plane_line_curve():
    from vkit.opt import get_data_folder
    folder = get_data_folder(__file__)

    from vkit.label.type import VPolygon, VPoint
    from .interface import debug_geometric_distortion

    config = CameraPlaneLineCurveConfig(
        curve_point=(300, 300),
        curve_direction=0,
        curve_perturb_vec=(0, 0, 300),
        curve_alpha=2,
        camera_model_config=CameraModelConfig(
            rotation_unit_vec=[0.0, 1.0, 0.0],
            rotation_theta=85,
        ),
        grid_size=10,
    )

    src_polygon = VPolygon(
        VPointList([
            VPoint(y=100, x=100),
            VPoint(y=100, x=300),
            VPoint(y=300, x=300),
            VPoint(y=300, x=100),
        ])
    )

    state = debug_geometric_distortion(
        'camera_plane_line_curve',
        camera_plane_line_curve,
        config,
        src_polygon,
        folder,
        'Lenna.png',
    )
    assert state

    from .grid_rendering.visualization import visualize_image_grid

    visualize_image_grid(state.src_image_grid
                         ).to_file(f'{folder}/camera_plane_line_curve-src-grid.png')
    visualize_image_grid(state.dst_image_grid
                         ).to_file(f'{folder}/camera_plane_line_curve-dst-grid.png')
