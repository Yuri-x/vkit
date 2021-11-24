from typing import Any

import attr
import numpy as np

from vkit.image.type import VImage
from .opt import extract_mat_from_image, clip_mat_back_to_uint8
from .interface import PhotometricDistortion


@attr.define
class GaussionNoiseConfig:
    std: float
    rnd_state: Any = None


def gaussion_noise_image(config, image, rnd):
    mat = extract_mat_from_image(image, np.int16)
    noise = np.round(rnd.normal(0, config.std, mat.shape)).astype(np.int16)
    mat = clip_mat_back_to_uint8(mat + noise)
    return VImage(mat=mat)


gaussion_noise = PhotometricDistortion(GaussionNoiseConfig, gaussion_noise_image)


@attr.define
class PoissonNoiseConfig:
    rnd_state: Any = None


def poisson_noise_image(config, image, rnd):
    # Follows scikit-image.
    # https://github.com/scikit-image/scikit-image/blob/main/skimage/util/noise.py#L181

    # [1, 256]
    scale = len(np.unique(image.mat))
    scale = 2**np.ceil(np.log2(scale))

    # Max = 255 * 256 < 2^16 - 1.
    mat = rnd.poisson(extract_mat_from_image(image, np.uint16) * scale) / scale
    mat = clip_mat_back_to_uint8(mat)
    return VImage(mat=mat)


poisson_noise = PhotometricDistortion(PoissonNoiseConfig, poisson_noise_image)


@attr.define
class ImpulseNoiseConfig:
    prob_salt: float
    prob_pepper: float
    rnd_state: Any = None


def impulse_noise_image(config, image, rnd):
    # https://www.programmersought.com/article/3363136769/
    prob_presv = 1 - config.prob_salt - config.prob_pepper

    mask = rnd.choice(
        (0, 1, 2),
        size=image.shape,
        p=[prob_presv, config.prob_salt, config.prob_pepper],
    )

    mat = image.mat.copy()
    # Salt.
    mat[mask == 1] = 255
    # Pepper.
    mat[mask == 2] = 0

    return VImage(mat=mat)


impulse_noise = PhotometricDistortion(ImpulseNoiseConfig, impulse_noise_image)


@attr.define
class SpeckleNoiseConfig:
    std: float
    rnd_state: Any = None


def speckle_noise_image(config, image, rnd):
    mat = extract_mat_from_image(image, np.float32)
    noise = rnd.normal(0, config.std, mat.shape)
    mat = clip_mat_back_to_uint8(mat + mat * noise)
    return VImage(mat=mat)


speckle_noise = PhotometricDistortion(SpeckleNoiseConfig, speckle_noise_image)


def debug():
    from vkit.opt import get_data_folder
    folder = get_data_folder(__file__)

    rnd = np.random.RandomState(13370)

    image = VImage.from_file(f'{folder}/Lenna.png')

    config = GaussionNoiseConfig(std=50)
    gaussion_noise.distort_image(config, image, rnd).to_file(f'{folder}/gaussion.png')

    config = PoissonNoiseConfig()
    poisson_noise.distort_image(config, image, rnd).to_file(f'{folder}/poission.png')

    config = ImpulseNoiseConfig(prob_salt=0.1, prob_pepper=0.1)
    impulse_noise.distort_image(config, image, rnd).to_file(f'{folder}/impulse.png')

    config = SpeckleNoiseConfig(std=0.25)
    speckle_noise.distort_image(config, image, rnd).to_file(f'{folder}/speckle.png')
