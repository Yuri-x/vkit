import numpy as np
import numpy.typing as npt

from vkit.image.type import VImage


def extract_mat_from_image(image: VImage, dtype) -> npt.NDArray:
    return image.mat.astype(dtype)


def clip_mat_back_to_uint8(mat: npt.NDArray) -> npt.NDArray:
    return np.clip(mat, 0, 255).astype(np.uint8)
