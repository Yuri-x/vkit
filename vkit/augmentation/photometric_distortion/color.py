from typing import Any

import attr
import numpy as np

from vkit.image.type import VImage, VImageKind
from .opt import extract_mat_from_image, clip_mat_back_to_uint8
from .interface import PhotometricDistortion


@attr.define
class MeanShiftConfig:
    delta: int


def mean_shift_image(config, image):
    # Change mean.
    mat = extract_mat_from_image(image, np.int16) + config.delta
    mat = clip_mat_back_to_uint8(mat)
    return attr.evolve(image, mat=mat)


mean_shift = PhotometricDistortion(MeanShiftConfig, mean_shift_image)


@attr.define
class StdShiftConfig:
    scale: float


def std_shift_image(config, image):
    # Change std while preserve mean.
    assert config.scale > 0
    mat = extract_mat_from_image(image, np.float32)

    if mat.ndim == 2:
        mean = np.mean(mat)
    elif mat.ndim == 3:
        mean = np.mean(mat.reshape(-1, mat.shape[-1]), axis=0)
    else:
        raise NotImplementedError()

    mat = mat * config.scale - mean * (config.scale - 1)

    mat = clip_mat_back_to_uint8(mat)
    return attr.evolve(image, mat=mat)


std_shift = PhotometricDistortion(StdShiftConfig, std_shift_image)


@attr.define
class ChannelPermutateConfig:
    rnd_state: Any = None


def channel_permutate_image(config, image, rnd):
    indices = rnd.permutation(image.num_channels)
    mat = image.mat[:, :, indices]
    return attr.evolve(image, mat=mat)


channel_permutate = PhotometricDistortion(ChannelPermutateConfig, channel_permutate_image)


@attr.define
class HueShiftConfig:
    delta: int


def hue_shift_image(config, image):
    assert image.kind == VImageKind.HSV
    mat = extract_mat_from_image(image, np.int16)

    # Cyclic.
    mat[:, :, 0] += config.delta
    mat = mat % 256  # type: ignore
    mat = mat.astype(np.uint8)

    return attr.evolve(image, mat=mat)


hue_shift = PhotometricDistortion(HueShiftConfig, hue_shift_image)


@attr.define
class SaturationShiftConfig:
    delta: int


def saturation_shift_image(config, image):
    assert image.kind == VImageKind.HSV
    mat = extract_mat_from_image(image, np.int16)
    mat[:, :, 1] += config.delta
    mat = clip_mat_back_to_uint8(mat)
    return attr.evolve(image, mat=mat)


saturation_shift = PhotometricDistortion(SaturationShiftConfig, saturation_shift_image)


def debug():
    from vkit.opt import get_data_folder
    folder = get_data_folder(__file__)

    rnd = np.random.RandomState(13370)

    image = VImage.from_file(f'{folder}/Lenna.png')

    config = MeanShiftConfig(delta=100)
    mean_shift.distort_image(config, image).to_file(f'{folder}/mean_shift_p_100.png')

    config = MeanShiftConfig(delta=-100)
    mean_shift.distort_image(config, image).to_file(f'{folder}/mean_shift_m_100.png')

    config = StdShiftConfig(scale=2)
    std_shift.distort_image(config, image).to_file(f'{folder}/std_shift_2.png')

    config = StdShiftConfig(scale=0.5)
    std_shift.distort_image(config, image).to_file(f'{folder}/std_shift_0.5.png')

    config = ChannelPermutateConfig()
    channel_permutate.distort_image(config, image, rnd).to_file(f'{folder}/channel_permutate_0.png')
    channel_permutate.distort_image(config, image, rnd).to_file(f'{folder}/channel_permutate_1.png')

    image_hsv = image.to_hsv_image()

    config = HueShiftConfig(delta=100)
    hue_shift.distort_image(config, image_hsv).to_file(f'{folder}/hue_p_100.png')

    config = HueShiftConfig(delta=-100)
    hue_shift.distort_image(config, image_hsv).to_file(f'{folder}/hue_m_100.png')

    config = SaturationShiftConfig(delta=100)
    saturation_shift.distort_image(config, image_hsv).to_file(f'{folder}/saturation_p_100.png')

    config = SaturationShiftConfig(delta=-100)
    saturation_shift.distort_image(config, image_hsv).to_file(f'{folder}/saturation_m_100.png')
