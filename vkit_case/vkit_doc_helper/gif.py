from typing import Sequence
import copy
import multiprocessing

from tqdm import tqdm
import iolite as io
import numpy as np

from vkit.image.type import VImage
from vkit.label.type import VImageMask, VImageScoreMap, VPolygon, VTextPolygon, VPoint
from vkit.label.visualization import (
    visualize_image_mask,
    visualize_scale_image_score_map,
    visualize_polygons,
    visualize_points,
)
from vkit.augmentation.geometric_distortion.grid_rendering.visualization import visualize_image_grid

from vkit.augmentation.geometric_distortion import (
    GeometricDistortion,
    GeometricDistortionResult,
    CameraModelConfig,
    CameraCubicCurveConfig,
    camera_cubic_curve,
    CameraPlaneLineFoldConfig,
    camera_plane_line_fold,
    CameraPlaneLineCurveConfig,
    camera_plane_line_curve,
    SimilarityMlsConfig,
    similarity_mls,
    ShearHoriConfig,
    shear_hori,
    ShearVertConfig,
    shear_vert,
    RotateConfig,
    rotate,
    SkewHoriConfig,
    skew_hori,
    SkewVertConfig,
    skew_vert,
)
from vkit.augmentation.geometric_distortion.mls import SimilarityMlsState

from vkit.augmentation.photometric_distortion import (
    PhotometricDistortion,
    MeanShiftConfig,
    mean_shift,
    StdShiftConfig,
    std_shift,
    ChannelPermutateConfig,
    channel_permutate,
    HueShiftConfig,
    hue_shift,
    SaturationShiftConfig,
    saturation_shift,
    GaussionNoiseConfig,
    gaussion_noise,
    PoissonNoiseConfig,
    poisson_noise,
    ImpulseNoiseConfig,
    impulse_noise,
    SpeckleNoiseConfig,
    speckle_noise,
)


def load_tianchi_ocr_scale_sample_pkl(scale_sample_pkl):
    scale_sample = io.read_joblib(scale_sample_pkl)

    image: VImage = scale_sample.image
    text_polygons: Sequence[VTextPolygon] = scale_sample.text_polygons
    polygons = [text_polygon.polygon for text_polygon in text_polygons]
    image_mask: VImageMask = scale_sample.text_mask
    image_score_map: VImageScoreMap = scale_sample.text_scale_map

    return image, image_mask, image_score_map, polygons


def interpolate_value_ratio(val_src, val_dst, ratio):
    assert type(val_src) is type(val_dst)
    if isinstance(val_src, (int, float)):
        return type(val_src)(val_src + (val_dst - val_src) * ratio)
    elif isinstance(val_src, VPoint):
        y = interpolate_value_ratio(val_src.y, val_dst.y, ratio)  # type: ignore
        x = interpolate_value_ratio(val_src.x, val_dst.x, ratio)  # type: ignore
        return VPoint(y=y, x=x)  # type: ignore
    elif isinstance(val_src, np.ndarray):
        val = interpolate_value_ratio(
            val_src.tolist(),
            val_dst.tolist(),
            ratio,
        )
        return np.asarray(val, dtype=val_src.dtype)
    elif isinstance(val_src, (tuple, list)):
        val_src_list = val_src
        val_dst_list = val_dst
        return [
            interpolate_value_ratio(val_src, val_dst, ratio)
            for val_src, val_dst in zip(val_src_list, val_dst_list)
        ]
    else:
        raise NotImplementedError()


def interpolate_value(val_src, val_dst, frame_idx, num_frames):
    ratio = frame_idx / num_frames
    ratio = 3 * ratio**2 - 2 * ratio**3
    return interpolate_value_ratio(val_src, val_dst, ratio)


def interpolate_config(config_src, config_dst, fields, frame_idx, num_frames):
    config = copy.deepcopy(config_src)
    for field in fields:
        path = field.split('.')

        cur_config = config
        cur_config_src = config_src
        cur_config_dst = config_dst
        for field in path[:-1]:
            cur_config = getattr(cur_config, field)
            cur_config_src = getattr(cur_config_src, field)
            cur_config_dst = getattr(cur_config_dst, field)

        field = path[-1]
        setattr(
            cur_config,
            field,
            interpolate_value(
                getattr(cur_config_src, field),
                getattr(cur_config_dst, field),
                frame_idx,
                num_frames,
            ),
        )
    return config


def generate_frame_configs(configs, fields, num_frames_per_step, drop_last=False):
    frame_configs = []
    for config_idx, config_src in enumerate(configs):
        if config_idx == len(configs) - 1 and drop_last:
            break
        config_dst = configs[(config_idx + 1) % len(configs)]
        for frame_idx in range(num_frames_per_step):
            frame_configs.append(
                interpolate_config(
                    config_src,
                    config_dst,
                    fields,
                    frame_idx,
                    num_frames_per_step,
                )
            )
    return frame_configs


def apply_geometric_distortion(
    frame_config_idx: int,
    frame_config,
    geometric_distortion: GeometricDistortion,
    image: VImage,
    image_mask: VImageMask,
    image_score_map: VImageScoreMap,
    polygons: Sequence[VPolygon],
):
    result = geometric_distortion.distort(
        frame_config,
        image,
        image_mask=image_mask,
        image_score_map=image_score_map,
        polygons=polygons,
        get_active_image_mask=True,
        get_state=True,
    )
    return frame_config_idx, result


def proc_apply_geometric_distortion(args):
    return apply_geometric_distortion(*args)


def apply_geometric_distortion_to_frame_configs(
    frame_configs,
    geometric_distortion: GeometricDistortion,
    image: VImage,
    image_mask: VImageMask,
    image_score_map: VImageScoreMap,
    polygons: Sequence[VPolygon],
) -> Sequence[GeometricDistortionResult]:
    results = [None] * len(frame_configs)
    with multiprocessing.Pool() as pool:
        for frame_config_idx, result in tqdm(
            pool.imap_unordered(
                proc_apply_geometric_distortion, [(
                    frame_config_idx,
                    frame_config,
                    geometric_distortion,
                    image,
                    image_mask,
                    image_score_map,
                    polygons,
                ) for frame_config_idx, frame_config in enumerate(frame_configs)]
            )
        ):
            results[frame_config_idx] = result
    return results  # type: ignore


def generate_gif(
    path,
    results: Sequence[GeometricDistortionResult],
    num_seconds,
):
    height_max = max(result.image.height for result in results)
    width_max = max(result.image.width for result in results)

    mats = []
    for result in results:
        dst_image_grid = None
        assert result.state
        if hasattr(result.state, 'dst_image_grid'):
            dst_image_grid = result.state.dst_image_grid

        if dst_image_grid:
            # image      | polygons
            # image_grid | active_mask
            # image_mask | image_score_map
            mat = np.zeros((height_max * 3, width_max * 2, 3), dtype=np.uint8)
        else:
            # image      | polygons
            # image_mask | image_score_map
            mat = np.zeros((height_max * 2, width_max * 2, 3), dtype=np.uint8)

        height_offset = 0

        # Row.
        image = result.image
        mat[height_offset:height_offset + image.height, :image.width] = image.mat

        polygons = result.polygons
        assert polygons
        vis_polygons = visualize_polygons(image, polygons, show_index=True).to_rgb_image()
        mat[height_offset:height_offset + image.height,
            width_max:width_max + image.width] = vis_polygons.mat

        height_offset += height_max

        if dst_image_grid:
            # Row
            vis_dst_image_grid = visualize_image_grid(dst_image_grid).to_rgb_image()
            if isinstance(result.state, SimilarityMlsState):
                # SimilarityMls customization.
                dst_handle_points = result.state.dst_handle_points
                vis_dst_image_grid = visualize_points(
                    vis_dst_image_grid,
                    dst_handle_points,
                    style='circle-5',
                )

            mat[height_offset:height_offset + image.height, :image.width] = vis_dst_image_grid.mat

            active_image_mask = result.active_image_mask
            assert active_image_mask
            vis_active_image_mask = visualize_image_mask(active_image_mask).to_rgb_image()
            mat[height_offset:height_offset + image.height,
                width_max:width_max + image.width] = vis_active_image_mask.mat

            height_offset += height_max

        # Row.
        image_mask = result.image_mask
        assert image_mask
        vis_image_mask = visualize_image_mask(image_mask).to_rgb_image()
        mat[height_offset:height_offset + image.height, :image.width] = vis_image_mask.mat

        image_score_map = result.image_score_map
        assert image_score_map
        vis_image_score_map = visualize_scale_image_score_map(image_score_map, image_mask)
        mat[height_offset:height_offset + image.height,
            width_max:width_max + image.width] = vis_image_score_map.mat

        mats.append(mat)

    num_frames = len(results)
    from moviepy.editor import ImageSequenceClip
    clip = ImageSequenceClip(mats, fps=num_frames // num_seconds)
    clip.write_gif(path)


def generate_camera_cubic_curve_gif(scale_sample_pkl, output_gif):
    frame_configs = generate_frame_configs(
        [
            CameraCubicCurveConfig(
                curve_alpha=0,
                curve_beta=0,
                curve_direction=0,
                curve_scale=1.0,
                camera_model_config=CameraModelConfig(
                    rotation_unit_vec=[1.0, 0.0, 0.0],
                    rotation_theta=0,
                ),
                grid_size=10,
            ),
            CameraCubicCurveConfig(
                curve_alpha=60,
                curve_beta=-60,
                curve_direction=0,
                curve_scale=1.0,
                camera_model_config=CameraModelConfig(
                    rotation_unit_vec=[1.0, 0.0, 0.0],
                    rotation_theta=30,
                ),
                grid_size=10,
            ),
            CameraCubicCurveConfig(
                curve_alpha=15,
                curve_beta=15,
                curve_direction=0,
                curve_scale=1.0,
                camera_model_config=CameraModelConfig(
                    rotation_unit_vec=[0.0, 1.0, 0.0],
                    rotation_theta=10,
                ),
                grid_size=10,
            ),
        ],
        (
            'curve_alpha',
            'curve_beta',
            'curve_direction',
            'curve_scale',
            'camera_model_config.rotation_unit_vec',
            'camera_model_config.rotation_theta',
        ),
        16,
    )

    (
        image,
        image_mask,
        image_score_map,
        polygons,
    ) = load_tianchi_ocr_scale_sample_pkl(scale_sample_pkl)

    results = apply_geometric_distortion_to_frame_configs(
        frame_configs,
        camera_cubic_curve,
        image,
        image_mask,
        image_score_map,
        polygons,
    )

    generate_gif(output_gif, results, 3)


def generate_camera_plane_line_fold_gif(scale_sample_pkl, output_gif):
    frame_configs = generate_frame_configs(
        [
            CameraPlaneLineFoldConfig(
                fold_point=(200, 200),
                fold_direction=0,
                fold_perturb_vec=(0, 0, 0),
                fold_alpha=1.0,
                camera_model_config=CameraModelConfig(
                    rotation_unit_vec=[1.0, 0.0, 0.0],
                    rotation_theta=0,
                ),
                grid_size=10,
            ),
            CameraPlaneLineFoldConfig(
                fold_point=(200, 200),
                fold_direction=0,
                fold_perturb_vec=(0, 0, 200),
                fold_alpha=0.5,
                camera_model_config=CameraModelConfig(
                    rotation_unit_vec=[1.0, 0.0, 0.0],
                    rotation_theta=30,
                ),
                grid_size=10,
            ),
            CameraPlaneLineFoldConfig(
                fold_point=(200, 200),
                fold_direction=30,
                fold_perturb_vec=(0, 0, -200),
                fold_alpha=0.5,
                camera_model_config=CameraModelConfig(
                    rotation_unit_vec=[0.0, 1.0, 0.0],
                    rotation_theta=10,
                ),
                grid_size=10,
            ),
        ],
        (
            'fold_point',
            'fold_direction',
            'fold_perturb_vec',
            'fold_alpha',
            'camera_model_config.rotation_unit_vec',
            'camera_model_config.rotation_theta',
        ),
        16,
    )

    (
        image,
        image_mask,
        image_score_map,
        polygons,
    ) = load_tianchi_ocr_scale_sample_pkl(scale_sample_pkl)

    results = apply_geometric_distortion_to_frame_configs(
        frame_configs,
        camera_plane_line_fold,
        image,
        image_mask,
        image_score_map,
        polygons,
    )

    generate_gif(output_gif, results, 3)


def generate_camera_plane_line_curve_gif(scale_sample_pkl, output_gif):
    frame_configs = generate_frame_configs(
        [
            CameraPlaneLineCurveConfig(
                curve_point=(200, 200),
                curve_direction=0,
                curve_perturb_vec=(0, 0, 0),
                curve_alpha=3.0,
                camera_model_config=CameraModelConfig(
                    rotation_unit_vec=[1.0, 0.0, 0.0],
                    rotation_theta=0,
                ),
                grid_size=10,
            ),
            CameraPlaneLineCurveConfig(
                curve_point=(200, 200),
                curve_direction=0,
                curve_perturb_vec=(0, 0, 300),
                curve_alpha=2.0,
                camera_model_config=CameraModelConfig(
                    rotation_unit_vec=[1.0, 0.0, 0.0],
                    rotation_theta=30,
                ),
                grid_size=10,
            ),
            CameraPlaneLineCurveConfig(
                curve_point=(200, 200),
                curve_direction=0,
                curve_perturb_vec=(0, 0, 300),
                curve_alpha=2.0,
                camera_model_config=CameraModelConfig(
                    rotation_unit_vec=[0.0, 1.0, 0.0],
                    rotation_theta=30,
                ),
                grid_size=10,
            ),
        ],
        (
            'curve_point',
            'curve_direction',
            'curve_perturb_vec',
            'curve_alpha',
            'camera_model_config.rotation_unit_vec',
            'camera_model_config.rotation_theta',
        ),
        16,
    )

    (
        image,
        image_mask,
        image_score_map,
        polygons,
    ) = load_tianchi_ocr_scale_sample_pkl(scale_sample_pkl)

    results = apply_geometric_distortion_to_frame_configs(
        frame_configs,
        camera_plane_line_curve,
        image,
        image_mask,
        image_score_map,
        polygons,
    )

    generate_gif(output_gif, results, 3)


def generate_similarity_mls_gif(scale_sample_pkl, output_gif):
    frame_configs = generate_frame_configs(
        [
            SimilarityMlsConfig(
                src_handle_points=[
                    VPoint(y=100, x=25),
                    VPoint(y=100, x=85),
                    VPoint(y=100, x=145),
                    VPoint(y=100, x=205),
                    VPoint(y=100, x=265),
                ],
                dst_handle_points=[
                    VPoint(y=100, x=25),
                    VPoint(y=100, x=85),
                    VPoint(y=100, x=145),
                    VPoint(y=100, x=205),
                    VPoint(y=100, x=265),
                ],
                grid_size=20,
            ),
            SimilarityMlsConfig(
                src_handle_points=[
                    VPoint(y=100, x=25),
                    VPoint(y=100, x=85),
                    VPoint(y=100, x=145),
                    VPoint(y=100, x=205),
                    VPoint(y=100, x=265),
                ],
                dst_handle_points=[
                    VPoint(y=100, x=25),
                    VPoint(y=50, x=85),
                    VPoint(y=100, x=145),
                    VPoint(y=150, x=205),
                    VPoint(y=100, x=265),
                ],
                grid_size=20,
            ),
            SimilarityMlsConfig(
                src_handle_points=[
                    VPoint(y=100, x=25),
                    VPoint(y=100, x=85),
                    VPoint(y=100, x=145),
                    VPoint(y=100, x=205),
                    VPoint(y=100, x=265),
                ],
                dst_handle_points=[
                    VPoint(y=100, x=25),
                    VPoint(y=50, x=85),
                    VPoint(y=50, x=145),
                    VPoint(y=150, x=205),
                    VPoint(y=150, x=265),
                ],
                grid_size=20,
            ),
        ],
        ('dst_handle_points',),
        16,
    )

    (
        image,
        image_mask,
        image_score_map,
        polygons,
    ) = load_tianchi_ocr_scale_sample_pkl(scale_sample_pkl)

    results = apply_geometric_distortion_to_frame_configs(
        frame_configs,
        similarity_mls,
        image,
        image_mask,
        image_score_map,
        polygons,
    )

    generate_gif(output_gif, results, 3)


def generate_shear_hori_gif(scale_sample_pkl, output_gif):
    frame_configs = generate_frame_configs(
        [
            ShearHoriConfig(angle=0),
            ShearHoriConfig(angle=30),
            ShearHoriConfig(angle=-30),
        ],
        ('angle',),
        16,
    )

    (
        image,
        image_mask,
        image_score_map,
        polygons,
    ) = load_tianchi_ocr_scale_sample_pkl(scale_sample_pkl)

    results = apply_geometric_distortion_to_frame_configs(
        frame_configs,
        shear_hori,
        image,
        image_mask,
        image_score_map,
        polygons,
    )

    generate_gif(output_gif, results, 3)


def generate_shear_vert_gif(scale_sample_pkl, output_gif):
    frame_configs = generate_frame_configs(
        [
            ShearVertConfig(angle=0),
            ShearVertConfig(angle=30),
            ShearVertConfig(angle=-30),
        ],
        ('angle',),
        16,
    )

    (
        image,
        image_mask,
        image_score_map,
        polygons,
    ) = load_tianchi_ocr_scale_sample_pkl(scale_sample_pkl)

    results = apply_geometric_distortion_to_frame_configs(
        frame_configs,
        shear_vert,
        image,
        image_mask,
        image_score_map,
        polygons,
    )

    generate_gif(output_gif, results, 3)


def generate_rotate_gif(scale_sample_pkl, output_gif):
    frame_configs = generate_frame_configs(
        [
            RotateConfig(angle=0),
            RotateConfig(angle=120),
            RotateConfig(angle=240),
            RotateConfig(angle=360),
        ],
        ('angle',),
        16,
        drop_last=True,
    )

    (
        image,
        image_mask,
        image_score_map,
        polygons,
    ) = load_tianchi_ocr_scale_sample_pkl(scale_sample_pkl)

    results = apply_geometric_distortion_to_frame_configs(
        frame_configs,
        rotate,
        image,
        image_mask,
        image_score_map,
        polygons,
    )

    generate_gif(output_gif, results, 3)


def generate_skew_hori_gif(scale_sample_pkl, output_gif):
    frame_configs = generate_frame_configs(
        [
            SkewHoriConfig(ratio=0.0),
            SkewHoriConfig(ratio=0.2),
            SkewHoriConfig(ratio=-0.2),
        ],
        ('ratio',),
        16,
    )

    (
        image,
        image_mask,
        image_score_map,
        polygons,
    ) = load_tianchi_ocr_scale_sample_pkl(scale_sample_pkl)

    results = apply_geometric_distortion_to_frame_configs(
        frame_configs,
        skew_hori,
        image,
        image_mask,
        image_score_map,
        polygons,
    )

    generate_gif(output_gif, results, 3)


def generate_skew_vert_gif(scale_sample_pkl, output_gif):
    frame_configs = generate_frame_configs(
        [
            SkewVertConfig(ratio=0.0),
            SkewVertConfig(ratio=0.2),
            SkewVertConfig(ratio=-0.2),
        ],
        ('ratio',),
        16,
    )

    (
        image,
        image_mask,
        image_score_map,
        polygons,
    ) = load_tianchi_ocr_scale_sample_pkl(scale_sample_pkl)

    results = apply_geometric_distortion_to_frame_configs(
        frame_configs,
        skew_vert,
        image,
        image_mask,
        image_score_map,
        polygons,
    )

    generate_gif(output_gif, results, 3)


def debug():
    from vkit.opt import get_data_folder
    folder = get_data_folder(__file__)

    # generate_camera_cubic_curve_gif(f'{folder}/1093.pkl', f'{folder}/camera_cubic_curve.gif')
    # generate_camera_plane_line_fold_gif(
    #     f'{folder}/1093.pkl', f'{folder}/camera_plane_line_fold.gif'
    # )
    # generate_camera_plane_line_curve_gif(
    #     f'{folder}/1093.pkl', f'{folder}/camera_plane_line_curve.gif'
    # )
    # generate_similarity_mls_gif(f'{folder}/1093.pkl', f'{folder}/similarity_mls.gif')
    # generate_shear_hori_gif(f'{folder}/1093.pkl', f'{folder}/shear_hori.gif')
    # generate_shear_vert_gif(f'{folder}/1093.pkl', f'{folder}/shear_vert.gif')
    # generate_rotate_gif(f'{folder}/1093.pkl', f'{folder}/rotate.gif')
    # generate_skew_hori_gif(f'{folder}/1093.pkl', f'{folder}/skew_hori.gif')
    generate_skew_vert_gif(f'{folder}/1093.pkl', f'{folder}/skew_vert.gif')


def apply_photometric_distortion(
    frame_config_idx: int,
    frame_config,
    photometric_distortion: PhotometricDistortion,
    image: VImage,
):
    new_image = photometric_distortion.distort_image(
        frame_config,
        image,
        rnd=np.random.RandomState(),
    )
    return frame_config_idx, new_image


def proc_apply_photometric_distortion(args):
    return apply_photometric_distortion(*args)


def apply_photometric_distortion_to_frame_configs(
    frame_configs,
    photometric_distortion: PhotometricDistortion,
    image: VImage,
) -> Sequence[VImage]:
    new_images = [None] * len(frame_configs)
    with multiprocessing.Pool() as pool:
        for frame_config_idx, new_image in tqdm(
            pool.imap_unordered(
                proc_apply_photometric_distortion, [(
                    frame_config_idx,
                    frame_config,
                    photometric_distortion,
                    image,
                ) for frame_config_idx, frame_config in enumerate(frame_configs)]
            )
        ):
            new_images[frame_config_idx] = new_image
    return new_images  # type: ignore


def generate_pho_gif(
    path,
    image: VImage,
    new_images: Sequence[VImage],
    num_seconds,
):
    mats = []
    for new_image in new_images:
        # image      | new_image
        mat = np.zeros((image.height, image.width * 2, 3), dtype=np.uint8)

        mat[:, :image.width] = image.mat
        mat[:, image.width:] = new_image.to_rgb_image().mat

        mats.append(mat)

    num_frames = len(new_images)
    from moviepy.editor import ImageSequenceClip
    clip = ImageSequenceClip(mats, fps=num_frames // num_seconds)
    clip.write_gif(path)


def generate_mean_shift_gif(scale_sample_pkl, output_gif):
    frame_configs = generate_frame_configs(
        [
            MeanShiftConfig(delta=0),
            MeanShiftConfig(delta=100),
            MeanShiftConfig(delta=-100),
        ],
        ('delta',),
        16,
    )

    (
        image,
        _,
        _,
        _,
    ) = load_tianchi_ocr_scale_sample_pkl(scale_sample_pkl)

    new_images = apply_photometric_distortion_to_frame_configs(
        frame_configs,
        mean_shift,
        image,
    )

    generate_pho_gif(
        output_gif,
        image,
        new_images,
        num_seconds=3,
    )


def generate_std_shift_gif(scale_sample_pkl, output_gif):
    frame_configs = generate_frame_configs(
        [
            StdShiftConfig(scale=1.0),
            StdShiftConfig(scale=2.0),
            StdShiftConfig(scale=0.5),
        ],
        ('scale',),
        16,
    )

    (
        image,
        _,
        _,
        _,
    ) = load_tianchi_ocr_scale_sample_pkl(scale_sample_pkl)

    new_images = apply_photometric_distortion_to_frame_configs(
        frame_configs,
        std_shift,
        image,
    )

    generate_pho_gif(
        output_gif,
        image,
        new_images,
        num_seconds=3,
    )


def generate_channel_permutate_gif(scale_sample_pkl, output_gif):
    frame_configs = generate_frame_configs(
        [
            ChannelPermutateConfig(),
            ChannelPermutateConfig(),
        ],
        (),
        16,
    )

    (
        image,
        _,
        _,
        _,
    ) = load_tianchi_ocr_scale_sample_pkl(scale_sample_pkl)

    new_images = apply_photometric_distortion_to_frame_configs(
        frame_configs,
        channel_permutate,
        image,
    )

    generate_pho_gif(
        output_gif,
        image,
        new_images,
        num_seconds=1,
    )


def generate_hue_shift_gif(scale_sample_pkl, output_gif):
    frame_configs = generate_frame_configs(
        [
            HueShiftConfig(delta=0),
            HueShiftConfig(delta=100),
            HueShiftConfig(delta=-100),
        ],
        ('delta',),
        16,
    )

    (
        image,
        _,
        _,
        _,
    ) = load_tianchi_ocr_scale_sample_pkl(scale_sample_pkl)

    new_images = apply_photometric_distortion_to_frame_configs(
        frame_configs,
        hue_shift,
        image.to_hsv_image(),
    )

    generate_pho_gif(
        output_gif,
        image,
        new_images,
        num_seconds=3,
    )


def generate_saturation_shift_gif(scale_sample_pkl, output_gif):
    frame_configs = generate_frame_configs(
        [
            SaturationShiftConfig(delta=0),
            SaturationShiftConfig(delta=100),
            SaturationShiftConfig(delta=-100),
        ],
        ('delta',),
        16,
    )

    (
        image,
        _,
        _,
        _,
    ) = load_tianchi_ocr_scale_sample_pkl(scale_sample_pkl)

    new_images = apply_photometric_distortion_to_frame_configs(
        frame_configs,
        saturation_shift,
        image.to_hsv_image(),
    )

    generate_pho_gif(
        output_gif,
        image,
        new_images,
        num_seconds=3,
    )


def generate_gaussion_noise_gif(scale_sample_pkl, output_gif):
    frame_configs = generate_frame_configs(
        [
            GaussionNoiseConfig(std=0.0),
            GaussionNoiseConfig(std=20.0),
            GaussionNoiseConfig(std=100.0),
        ],
        ('std',),
        8,
    )

    (
        image,
        _,
        _,
        _,
    ) = load_tianchi_ocr_scale_sample_pkl(scale_sample_pkl)

    new_images = apply_photometric_distortion_to_frame_configs(
        frame_configs,
        gaussion_noise,
        image,
    )

    generate_pho_gif(
        output_gif,
        image,
        new_images,
        num_seconds=3,
    )


def generate_poisson_noise_gif(scale_sample_pkl, output_gif):
    frame_configs = generate_frame_configs(
        [
            PoissonNoiseConfig(),
            PoissonNoiseConfig(),
        ],
        (),
        16,
    )

    (
        image,
        _,
        _,
        _,
    ) = load_tianchi_ocr_scale_sample_pkl(scale_sample_pkl)

    # apply_photometric_distortion(
    #     0,
    #     frame_configs[0],
    #     poisson_noise,
    #     image,
    # )

    new_images = apply_photometric_distortion_to_frame_configs(
        frame_configs,
        poisson_noise,
        image,
    )

    generate_pho_gif(
        output_gif,
        image,
        new_images,
        num_seconds=3,
    )


def generate_impulse_noise_gif(scale_sample_pkl, output_gif):
    frame_configs = generate_frame_configs(
        [
            ImpulseNoiseConfig(prob_salt=0.0, prob_pepper=0.0),
            ImpulseNoiseConfig(prob_salt=0.1, prob_pepper=0.0),
            ImpulseNoiseConfig(prob_salt=0.05, prob_pepper=0.05),
            ImpulseNoiseConfig(prob_salt=0.0, prob_pepper=0.1),
        ],
        (
            'prob_salt',
            'prob_pepper',
        ),
        8,
    )

    (
        image,
        _,
        _,
        _,
    ) = load_tianchi_ocr_scale_sample_pkl(scale_sample_pkl)

    new_images = apply_photometric_distortion_to_frame_configs(
        frame_configs,
        impulse_noise,
        image,
    )

    generate_pho_gif(
        output_gif,
        image,
        new_images,
        num_seconds=3,
    )


def generate_speckle_noise_gif(scale_sample_pkl, output_gif):
    frame_configs = generate_frame_configs(
        [
            SpeckleNoiseConfig(std=0.0),
            SpeckleNoiseConfig(std=0.1),
            SpeckleNoiseConfig(std=0.5),
        ],
        ('std',),
        8,
    )

    (
        image,
        _,
        _,
        _,
    ) = load_tianchi_ocr_scale_sample_pkl(scale_sample_pkl)

    new_images = apply_photometric_distortion_to_frame_configs(
        frame_configs,
        speckle_noise,
        image,
    )

    generate_pho_gif(
        output_gif,
        image,
        new_images,
        num_seconds=3,
    )


def debug_pho():
    from vkit.opt import get_data_folder
    folder = get_data_folder(__file__)

    # generate_mean_shift_gif(f'{folder}/1093.pkl', f'{folder}/mean_shift.gif')
    # generate_std_shift_gif(f'{folder}/1093.pkl', f'{folder}/std_shift.gif')
    # generate_channel_permutate_gif(f'{folder}/1093.pkl', f'{folder}/channel_permutate.gif')
    # generate_hue_shift_gif(f'{folder}/1093.pkl', f'{folder}/hue_shift.gif')
    # generate_saturation_shift_gif(f'{folder}/1093.pkl', f'{folder}/saturation_shift.gif')
    # generate_gaussion_noise_gif(f'{folder}/1093.pkl', f'{folder}/gaussion_noise.gif')
    # generate_poisson_noise_gif(f'{folder}/1093.pkl', f'{folder}/poisson_noise.gif')
    # generate_impulse_noise_gif(f'{folder}/1093.pkl', f'{folder}/impulse_noise.gif')
    generate_speckle_noise_gif(f'{folder}/1093.pkl', f'{folder}/speckle_noise.gif')


def debug_block():
    frame_configs = generate_frame_configs(
        [
            CameraPlaneLineFoldConfig(
                fold_point=(200, 200),
                fold_direction=0,
                fold_perturb_vec=(0, 0, 0),
                fold_alpha=1.0,
                camera_model_config=CameraModelConfig(
                    rotation_unit_vec=[1.0, 0.0, 0.0],
                    rotation_theta=0,
                ),
                grid_size=10,
            ),
            CameraPlaneLineFoldConfig(
                fold_point=(200, 200),
                fold_direction=0,
                fold_perturb_vec=(100, 0, 0),
                fold_alpha=0.5,
                camera_model_config=CameraModelConfig(
                    rotation_unit_vec=[1.0, 0.0, 0.0],
                    rotation_theta=30,
                ),
                grid_size=10,
            ),
        ],
        (
            'fold_point',
            'fold_direction',
            'fold_perturb_vec',
            'fold_alpha',
            'camera_model_config.rotation_unit_vec',
            'camera_model_config.rotation_theta',
        ),
        16,
    )

    from vkit.opt import get_data_folder
    folder = get_data_folder(__file__)

    (
        image,
        image_mask,
        image_score_map,
        polygons,
    ) = load_tianchi_ocr_scale_sample_pkl(f'{folder}/1093.pkl')

    # _, result = apply_geometric_distortion(
    #     0,
    #     frame_configs[-1],
    #     camera_plane_line_fold,
    #     image,
    #     image_mask,
    #     image_score_map,
    #     polygons,
    # )

    # result.image.to_file(f'{folder}/debug.png')

    frame_config = frame_configs[-1]
    state = camera_plane_line_fold.generate_state(frame_config, image)
    assert state
    new_image = camera_plane_line_fold.distort_image(frame_configs[-1], image, state=state)
    new_image.to_file(f'{folder}/debug.png')

    scale = 3
    rescaled_height = new_image.height * scale
    rescaled_width = new_image.width * scale
    dst_image_grid = state.dst_image_grid.to_rescaled_image_grid(
        new_image, rescaled_height, rescaled_width
    )
    new_image = new_image.to_rescaled_image(rescaled_height, rescaled_width)

    visualize_image_grid(dst_image_grid, image=new_image, line_color='yellow',
                         show_index=True).to_file(f'{folder}/debug_grid.png')
