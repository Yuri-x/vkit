from typing import Any

import attr
import numpy as np

from vkit.image.type import VImage, VImageKind
from .opt import extract_mat_from_image, clip_mat_back_to_uint8
from .interface import PhotometricDistortion


@attr.define
class BrightnessShiftConfig:
    delta: int


def brightness_shift_image(config, image):
    # Change mean.
    mat = extract_mat_from_image(image, np.int16) + config.delta
    mat = clip_mat_back_to_uint8(mat)
    return attr.evolve(image, mat=mat)


brightness_shift = PhotometricDistortion(BrightnessShiftConfig, brightness_shift_image)


@attr.define
class ContrastShiftConfig:
    scale: float


def contrast_shift_image(config, image):
    # Change std.
    assert config.scale > 0
    mat = extract_mat_from_image(image, np.float32) * config.scale
    mat = clip_mat_back_to_uint8(mat)
    return attr.evolve(image, mat=mat)


contrast_shift = PhotometricDistortion(ContrastShiftConfig, contrast_shift_image)


@attr.define
class LightingShiftConfig:
    rnd_state: Any = None


def lighting_shift_image(config, image, rnd):
    indices = rnd.permutation(image.num_channels)
    mat = image.mat[:, :, indices]
    return attr.evolve(image, mat=mat)


lighting_shift = PhotometricDistortion(LightingShiftConfig, lighting_shift_image)


@attr.define
class HueShiftConfig:
    delta: int


def hue_shift_image(config, image):
    assert image.kind == VImageKind.HSV
    mat = extract_mat_from_image(image, np.int16)

    # Cyclic.
    mat[:, :, 0] += config.delta
    mat = mat % 256
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

    config = BrightnessShiftConfig(delta=100)
    brightness_shift.distort_image(config, image).to_file(f'{folder}/brightness_p_100.png')

    config = BrightnessShiftConfig(delta=-100)
    brightness_shift.distort_image(config, image).to_file(f'{folder}/brightness_m_100.png')

    config = ContrastShiftConfig(scale=2)
    contrast_shift.distort_image(config, image).to_file(f'{folder}/contrast_2.png')

    config = ContrastShiftConfig(scale=0.5)
    contrast_shift.distort_image(config, image).to_file(f'{folder}/contrast_0.5.png')

    config = LightingShiftConfig()
    lighting_shift.distort_image(config, image, rnd).to_file(f'{folder}/lighting_0.png')
    lighting_shift.distort_image(config, image, rnd).to_file(f'{folder}/lighting_1.png')

    image_hsv = image.to_hsv_image()

    config = HueShiftConfig(delta=100)
    hue_shift.distort_image(config, image_hsv).to_file(f'{folder}/hue_p_100.png')

    config = HueShiftConfig(delta=-100)
    hue_shift.distort_image(config, image_hsv).to_file(f'{folder}/hue_m_100.png')

    config = SaturationShiftConfig(delta=100)
    saturation_shift.distort_image(config, image_hsv).to_file(f'{folder}/saturation_p_100.png')

    config = SaturationShiftConfig(delta=-100)
    saturation_shift.distort_image(config, image_hsv).to_file(f'{folder}/saturation_m_100.png')
