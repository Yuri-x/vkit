from typing import Sequence, Tuple

import numpy as np
import attr

from vkit.image.type import VImage
from vkit.label.type import VPoint
from .grid_rendering.interface import PointProjector
from .grid_rendering.grid_creator import create_src_image_grid
from .interface import GeometricDistortionImageGridBased, StateImageGridBased


@attr.define
class SimilarityMlsConfig:
    src_handle_points: Sequence[VPoint]
    dst_handle_points: Sequence[VPoint]
    grid_size: int
    rescale_as_src: bool = False


class SimilarityMlsPointProjector(PointProjector):

    def __init__(self, src_handle_points: Sequence[VPoint], dst_handle_points: Sequence[VPoint]):
        self.src_handle_points = src_handle_points
        self.dst_handle_points = dst_handle_points

        self.src_xy_pair_to_dst_point = {
            (src_point.x, src_point.y): dst_point
            for src_point, dst_point in zip(src_handle_points, dst_handle_points)
        }

        self.src_handle_np_points = np.asarray(
            [(point.x, point.y) for point in src_handle_points],
            dtype=np.int32,
        )
        self.dst_handle_np_points = np.asarray(
            [(point.x, point.y) for point in dst_handle_points],
            dtype=np.int32,
        )

    def project_point(self, src_point):
        '''
        Calculate the corresponding dst point given the src point.
        Paper: https://people.engr.tamu.edu/schaefer/research/mls.pdf
        '''
        src_xy_pair = (src_point.x, src_point.y)

        if src_xy_pair in self.src_xy_pair_to_dst_point:
            # Identity.
            # NOTE: clone is important since this point could be changed later.
            # TODO: re-think the immutable design.
            return self.src_xy_pair_to_dst_point[src_xy_pair].clone()

        # Calculate the distance to src handles.
        src_distance_squares = self.src_handle_np_points.copy()
        src_distance_squares[:, 0] -= src_point.x
        src_distance_squares[:, 1] -= src_point.y
        np.square(src_distance_squares, out=src_distance_squares)
        # (N), and should not contain 0.0.
        src_distance_squares = np.sum(src_distance_squares, axis=1)

        # Calculate weights based on distances.
        # (N), and should not contain inf.
        with np.errstate(divide='raise'):
            src_distance_squares_inverse = 1 / src_distance_squares
            weights = src_distance_squares_inverse / np.sum(src_distance_squares_inverse)

        # (2), the weighted centroids.
        src_centroid = np.matmul(weights, self.src_handle_np_points)
        dst_centroid = np.matmul(weights, self.dst_handle_np_points)

        # (N, 2)
        src_hat = self.src_handle_np_points - src_centroid
        dst_hat = self.dst_handle_np_points - dst_centroid

        # (N, 2)
        src_hat_vert = src_hat[:, [1, 0]]
        src_hat_vert[:, 0] *= -1

        # Calculate matrix A.
        src_centroid_x, src_centroid_y = src_centroid
        src_mat_anchor = np.transpose(
            np.array(
                [
                    # v - p*
                    (
                        src_point.x - src_centroid_x,
                        src_point.y - src_centroid_y,
                    ),
                    # -(v - p*)^vert
                    (
                        src_point.y - src_centroid_y,
                        -(src_point.x - src_centroid_x),
                    ),
                ],
                dtype=np.float32,
            )
        )
        # (N, 2)
        src_mat_row0 = np.matmul(src_hat, src_mat_anchor)
        src_mat_row1 = np.matmul(-src_hat_vert, src_mat_anchor)
        # (N, 2, 2)
        src_mat = (
            np.expand_dims(np.expand_dims(src_distance_squares_inverse, axis=1), axis=1)
            * np.stack((src_mat_row0, src_mat_row1), axis=1)
        )

        # Calculate the point in dst.
        # (N, 2)
        dst_prod = np.squeeze(
            # (N, 1, 2)
            np.matmul(
                # (N, 1, 2)
                np.expand_dims(dst_hat, axis=1),
                # (N, 2, 2)
                src_mat,
            ),
            axis=1,
        )
        mu = np.sum(src_distance_squares_inverse * np.sum(src_hat * src_hat, axis=1))
        dst_x, dst_y = np.sum(dst_prod, axis=0) / mu + dst_centroid

        return VPoint(y=round(dst_y), x=round(dst_x))


class SimilarityMlsState(StateImageGridBased):

    def __init__(self, config: SimilarityMlsConfig, shape: Tuple[int, int]):
        height, width = shape

        super().__init__(
            src_image_grid=create_src_image_grid(height, width, config.grid_size),
            point_projector=SimilarityMlsPointProjector(
                config.src_handle_points,
                config.dst_handle_points,
            ),
        )

        self.dst_handle_points = list(map(self.shift_and_rescale_point, config.dst_handle_points))


similarity_mls = GeometricDistortionImageGridBased(
    config_cls=SimilarityMlsConfig,
    state_cls=SimilarityMlsState,
)


def debug():
    from vkit.opt import get_data_folder
    folder = get_data_folder(__file__)

    from vkit.label.type import VPolygon, VPointList
    from .interface import debug_geometric_distortion

    config = SimilarityMlsConfig(
        src_handle_points=[
            VPoint(y=10, x=10),
            VPoint(y=10, x=200),
            VPoint(y=200, x=200),
            VPoint(y=200, x=10),
        ],
        dst_handle_points=[
            VPoint(y=10, x=10),
            VPoint(y=10, x=550),
            VPoint(y=200, x=150),
            VPoint(y=200, x=10),
        ],
        grid_size=20,
        rescale_as_src=True,
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
        'similarity-mls',
        similarity_mls,
        config,
        src_polygon,
        folder,
        'Lenna.png',
    )
    assert state

    from .grid_rendering.visualization \
        import visualize_image_grid
    from vkit.label.visualization import visualize_points

    visualize_points(
        visualize_image_grid(state.src_image_grid),
        config.src_handle_points,
        style='circle-3',
    ).to_file(f'{folder}/similarity-mls-src-grid.png')
    visualize_points(
        visualize_image_grid(state.dst_image_grid),
        state.dst_handle_points,
        style='circle-3',
    ).to_file(f'{folder}/similarity-mls-dst-grid.png')


def debug_video_frames():
    from vkit.opt import get_data_folder
    folder = get_data_folder(__file__)

    from .grid_rendering.visualization import visualize_image_grid
    from vkit.label.visualization import visualize_points

    src_image = VImage.from_file(f'{folder}/Lenna.png')

    num_frames = 200
    for idx in range(num_frames):
        print(idx)
        ratio = (num_frames - 1 - idx) / (num_frames - 1)

        config = SimilarityMlsConfig(
            src_handle_points=[
                VPoint(y=100, x=100),
                VPoint(y=100, x=340),
                VPoint(y=340, x=340),
                VPoint(y=340, x=100),
            ],
            dst_handle_points=[
                VPoint(y=100, x=100),
                VPoint(y=100, x=340),
                VPoint(y=220 + round((340 - 220) * ratio), x=220 + round((340 - 220) * ratio)),
                VPoint(y=340, x=100),
            ],
            grid_size=15,
            rescale_as_src=True,
        )

        state = similarity_mls.generate_state(config, src_image)
        assert state
        dst_image = similarity_mls.distort_image(config, src_image, state)
        dst_image.to_file(f'{folder}/frames/{idx}.png')
        visualize_points(
            visualize_image_grid(state.dst_image_grid),
            state.dst_handle_points,
            style='circle-3',
        ).to_file(f'{folder}/grid-frames/{idx}.png')


def debug_create_video():
    from vkit.opt import get_data_folder
    folder = get_data_folder(__file__)

    combined_mats = []
    for idx in range(200):
        image = VImage.from_file(f'{folder}/frames/{idx}.png')
        grid = VImage.from_file(f'{folder}/grid-frames/{idx}.png')

        assert image.shape == grid.shape
        combined_mat = np.zeros((image.height * 2, image.width, 3), dtype=np.uint8)
        combined_mat[:image.height, :] = image.mat
        combined_mat[image.height:, :] = grid.mat

        combined_mats.append(combined_mat)

    from moviepy.editor import ImageSequenceClip
    clip = ImageSequenceClip(combined_mats, fps=30)
    clip.write_videofile(f'{folder}/video.mp4')
