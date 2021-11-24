from typing import Iterable, List, Union

from PIL import ImageDraw
import numpy as np
import cv2 as cv

from vkit.image.type import VImage
from .type import (
    VPoint,
    VPointList,
    VImageMask,
    VImageScoreMap,
    VPolygon,
)

# https://mokole.com/palette.html
_DISTINT_OUTLINES = [
    # darkgreen
    '#006400',
    # darkblue
    '#00008b',
    # maroon3
    '#b03060',
    # red
    '#ff0000',
    # yellow
    '#ffff00',
    # burlywood
    '#deb887',
    # lime
    '#00ff00',
    # aqua
    '#00ffff',
    # fuchsia
    '#ff00ff',
    # cornflower
    '#6495ed',
]


def visualize_points(
    image: VImage,
    points: Union[VPointList, Iterable[VPoint]],
    style: str = 'circle-1',
):
    pil_image = image.to_pil_image()
    draw = ImageDraw.Draw(pil_image)

    if style == 'point':
        flatten_points = []
        for point in points:
            flatten_points.append((point.x, point.y))

        draw.point(flatten_points, fill='red')

    elif style.startswith('circle-'):
        radius = int(style[len('circle-'):])
        for point in points:
            up = max(point.y - radius, 0)
            down = min(point.y + radius, image.height - 1)
            left = max(point.x - radius, 0)
            right = min(point.x + radius, image.width - 1)
            draw.ellipse((left, up, right, down), fill='red')

    else:
        raise NotImplementedError()

    return VImage.from_pil_image(pil_image)


def visualize_polygons(
    image: VImage,
    polygons: Iterable[VPolygon],
    outline: str = 'distint',
    show_index: bool = False,
):
    pil_image = image.to_pil_image()
    draw = ImageDraw.Draw(pil_image)

    for idx, polygon in enumerate(polygons):
        flatten_points: List[int] = []
        for point in polygon.points:
            flatten_points.extend([point.x, point.y])

        if outline == 'distint':
            cur_outline = _DISTINT_OUTLINES[idx % len(_DISTINT_OUTLINES)]
        else:
            cur_outline = outline

        draw.polygon(tuple(flatten_points), outline=cur_outline)
        if show_index:
            draw.text((flatten_points[0], flatten_points[1]), str(idx))

    return VImage.from_pil_image(pil_image)


def visualize_image_score_map(image_score_map: VImageScoreMap):
    mat = image_score_map.mat.copy()

    # Rescale to [0, 255]
    val_min = np.min(mat)
    mat -= val_min
    val_max = np.max(mat)
    mat *= 255.0
    mat /= val_max

    mat = np.clip(mat, 0, 255).astype(np.uint8)

    # Apply color map.
    color_mat = cv.applyColorMap(mat, cv.COLORMAP_JET)
    color_mat = cv.cvtColor(color_mat, cv.COLOR_BGR2RGB)

    return VImage(mat=color_mat)


def visualize_scale_image_score_map(image_score_map: VImageScoreMap, image_mask: VImageMask):
    # (0, +)
    mat = image_score_map.mat.copy()

    # Scale to 127.5.
    mat *= 127.5  # type: ignore

    # Clip [0, 255].
    mat = np.clip(mat, 0, 255)
    # To grayscale.
    mat = mat.astype(np.uint8)

    # Apply color map.
    color_mat = cv.applyColorMap(mat, cv.COLORMAP_JET)
    color_mat = cv.cvtColor(color_mat, cv.COLOR_BGR2RGB)

    # Set background as black.
    color_mat[image_mask.mat == 0] = 0

    return VImage(mat=color_mat)


def visualize_image_mask(image_mask: VImageMask):
    mat = image_mask.mat

    new_mat = np.zeros_like(mat)
    np.putmask(new_mat, mat > 0, 255)  # type: ignore

    return VImage(mat=new_mat)


def blend_image_with_image_mask(
    foreground_image: VImage,
    foreground_image_mask: VImageMask,
    background_image: VImage,
    foreground_alpha: float = 0.5,
):
    fg_mask_mat = (foreground_image_mask.mat > 0)  # type: ignore
    fg_mask_mat = fg_mask_mat.astype(np.float32) * foreground_alpha
    bg_mask_mask = 1.0 - fg_mask_mat

    fg_img_mat = foreground_image.mat.astype(np.float32) / 255.0  # type: ignore
    bg_img_mat = background_image.mat.astype(np.float32) / 255.0  # type: ignore

    mat = cv.addWeighted(
        fg_img_mat * np.expand_dims(fg_mask_mat, -1),
        255.0,
        bg_img_mat * np.expand_dims(bg_mask_mask, -1),
        255.0,
        0.0,
    )
    mat = mat.astype(np.uint8)
    return VImage(mat=mat)
