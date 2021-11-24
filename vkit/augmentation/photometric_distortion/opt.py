import numpy as np


def extract_mat_from_image(image, dtype):
    return image.mat.astype(dtype)


def clip_mat_back_to_uint8(mat):
    return np.clip(mat, 0, 255).astype(np.uint8)
