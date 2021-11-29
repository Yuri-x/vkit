from enum import Enum, auto
from typing import Dict, Sequence

import attr
import numpy as np
import numpy.typing as npt
from PIL import Image, ImageOps
import cv2 as cv

from vkit.type import PathType


class VImageKind(Enum):
    RGB = auto()
    RGB_GCN = auto()
    RGBA = auto()
    HSV = auto()
    HSV_GCN = auto()
    GRAYSCALE = auto()
    GRAYSCALE_GCN = auto()
    NONE = auto()

    @staticmethod
    def to_ndim(image_kind: 'VImageKind'):
        return _to_ndim(image_kind)

    @staticmethod
    def to_dtype(image_kind: 'VImageKind'):
        return _to_dtype(image_kind)

    @staticmethod
    def to_num_channels(image_kind: 'VImageKind'):
        return _to_num_channels(image_kind)

    @staticmethod
    def support_gcn(image_kind: 'VImageKind'):
        _support_gcn(image_kind)

    @staticmethod
    def to_gcn(image_kind: 'VImageKind'):
        return _to_gcn(image_kind)

    @staticmethod
    def is_gcn(image_kind: 'VImageKind'):
        return _is_gcn(image_kind)

    @staticmethod
    def to_non_gcn(image_kind: 'VImageKind'):
        return _to_non_gcn(image_kind)


_V_IMAGE_KIND_NDIM_3 = {
    VImageKind.RGB,
    VImageKind.RGB_GCN,
    VImageKind.RGBA,
    VImageKind.HSV,
    VImageKind.HSV_GCN,
}

_V_IMAGE_KIND_NDIM_2 = {
    VImageKind.GRAYSCALE,
    VImageKind.GRAYSCALE_GCN,
}


def _to_ndim(image_kind: VImageKind):
    if image_kind in _V_IMAGE_KIND_NDIM_3:
        return 3

    elif image_kind in _V_IMAGE_KIND_NDIM_2:
        return 2

    else:
        raise NotImplementedError()


_V_IMAGE_KIND_DTYPE_UINT8 = {
    VImageKind.RGB,
    VImageKind.RGBA,
    VImageKind.HSV,
    VImageKind.GRAYSCALE,
}

_V_IMAGE_KIND_DTYPE_FLOAT32 = {
    VImageKind.RGB_GCN,
    VImageKind.HSV_GCN,
    VImageKind.GRAYSCALE_GCN,
}


def _to_dtype(image_kind: VImageKind):
    if image_kind in _V_IMAGE_KIND_DTYPE_UINT8:
        return np.uint8

    elif image_kind in _V_IMAGE_KIND_DTYPE_FLOAT32:
        return np.float32

    else:
        raise NotImplementedError()


_V_IMAGE_KIND_NUM_CHANNELS_4 = {
    VImageKind.RGBA,
}

_V_IMAGE_KIND_NUM_CHANNELS_3 = {
    VImageKind.RGB,
    VImageKind.RGB_GCN,
    VImageKind.HSV,
    VImageKind.HSV_GCN,
}

_V_IMAGE_KIND_NUM_CHANNELS_2 = {
    VImageKind.GRAYSCALE,
    VImageKind.GRAYSCALE_GCN,
}


def _to_num_channels(image_kind: VImageKind):
    if image_kind in _V_IMAGE_KIND_NUM_CHANNELS_4:
        return 4

    elif image_kind in _V_IMAGE_KIND_NUM_CHANNELS_3:
        return 3

    elif image_kind in _V_IMAGE_KIND_NUM_CHANNELS_2:
        return None

    else:
        raise NotImplementedError


_V_IMAGE_KIND_NON_GCN_TO_GCN = {
    VImageKind.RGB: VImageKind.RGB_GCN,
    VImageKind.HSV: VImageKind.HSV_GCN,
    VImageKind.GRAYSCALE: VImageKind.GRAYSCALE_GCN,
}


def _support_gcn(image_kind: VImageKind):
    return image_kind not in _V_IMAGE_KIND_NON_GCN_TO_GCN


def _to_gcn(image_kind: VImageKind):
    if _support_gcn(image_kind):
        raise RuntimeError(f'image_kind={image_kind} not supported.')
    return _V_IMAGE_KIND_NON_GCN_TO_GCN[image_kind]


_V_IMAGE_KIND_GCN_TO_NON_GCN = {val: key for key, val in _V_IMAGE_KIND_NON_GCN_TO_GCN.items()}


def _is_gcn(image_kind: VImageKind):
    return image_kind in _V_IMAGE_KIND_GCN_TO_NON_GCN


def _to_non_gcn(image_kind: VImageKind):
    if not _is_gcn(image_kind):
        raise RuntimeError(f'image_kind={image_kind} not supported.')
    return _V_IMAGE_KIND_GCN_TO_NON_GCN[image_kind]


@attr.define
class VImage:
    mat: npt.NDArray
    kind: VImageKind = VImageKind.NONE

    def __attrs_post_init__(self):
        if self.kind != VImageKind.NONE:
            # Validate mat.dtype and kind.
            assert VImageKind.to_dtype(self.kind) == self.mat.dtype
            assert VImageKind.to_ndim(self.kind) == self.mat.ndim
        else:
            # Infer image kind based on mat.
            if self.mat.dtype == np.float32:
                raise NotImplementedError('kind is None and mat.dtype == np.float32.')

            elif self.mat.dtype == np.uint8:
                if self.mat.ndim == 2:
                    # Defaults to GRAYSCALE.
                    self.kind = VImageKind.GRAYSCALE
                elif self.mat.ndim == 3:
                    if self.mat.shape[2] == 4:
                        self.kind = VImageKind.RGBA
                    elif self.mat.shape[2] == 3:
                        # Defaults to RGB.
                        self.kind = VImageKind.RGB
                    else:
                        raise NotImplementedError(f'Invalid num_channels={self.mat.shape[2]}.')

            else:
                raise NotImplementedError(f'Invalid mat.dtype={self.mat.dtype}.')

    @property
    def height(self):
        return self.mat.shape[0]

    @property
    def width(self):
        return self.mat.shape[1]

    @property
    def shape(self):
        return self.height, self.width

    @property
    def num_channels(self):
        if self.mat.ndim == 2:
            return 0
        else:
            assert self.mat.ndim == 3
            return self.mat.shape[2]

    def clone(self):
        mat = self.mat.copy()
        return attr.evolve(self, mat=mat)

    @staticmethod
    def from_pil_image(pil_image: Image.Image):
        mat = np.asarray(pil_image, dtype=np.uint8)
        return VImage(mat=mat)

    def to_pil_image(self):
        return Image.fromarray(self.mat)

    def to_gcn_image(self, lamb=0, eps=1E-8, scale=1.0):
        # Global contrast normalization.
        # https://cedar.buffalo.edu/~srihari/CSE676/12.2%20Computer%20Vision.pdf
        # (H, W) or (H, W, 3)
        kind = VImageKind.to_gcn(self.kind)

        mat = self.mat.astype(np.float32)

        # Normalize mean(contrast).
        mean = np.mean(mat)
        mat -= mean

        # Std normalized.
        std = np.sqrt(lamb + np.mean(mat**2))
        mat /= max(eps, std)
        if scale != 1.0:
            mat *= scale

        return VImage(mat=mat, kind=kind)

    def to_non_gcn_image(self):
        kind = VImageKind.to_non_gcn(self.kind)

        assert self.mat.dtype == np.float32
        val_min = np.min(self.mat)
        mat = self.mat - val_min
        gap = np.max(mat)
        mat = mat / gap * 255.0
        mat = np.round(mat)
        mat = np.clip(mat, 0, 255).astype(np.uint8)

        return VImage(mat=mat, kind=kind)

    @staticmethod
    def convert_image_kind(
        image: 'VImage',
        new_kind: VImageKind,
        kind_to_cv_color_codes: Dict[VImageKind, Sequence[int]],
    ):
        assert new_kind not in kind_to_cv_color_codes

        skip_clone = False
        if VImageKind.is_gcn(image.kind):
            image = image.to_non_gcn_image()
            skip_clone = True

        if image.kind == new_kind:
            return image if skip_clone else image.clone()

        if image.kind in kind_to_cv_color_codes:
            new_mat = image.mat
            for cv_color_code in kind_to_cv_color_codes[image.kind]:
                new_mat = cv.cvtColor(new_mat, cv_color_code)
            return VImage(mat=new_mat, kind=new_kind)
        else:
            raise NotImplementedError(f'{image.kind} -> {new_kind} not supported.')

    def to_grayscale_image(self):
        return self.convert_image_kind(
            self,
            VImageKind.GRAYSCALE,
            {
                VImageKind.RGB: [cv.COLOR_RGB2GRAY],
                VImageKind.RGBA: [cv.COLOR_RGBA2GRAY],
                VImageKind.HSV: [cv.COLOR_HSV2RGB_FULL, cv.COLOR_RGB2GRAY],
            },
        )

    def to_rgb_image(self):
        return self.convert_image_kind(
            self,
            VImageKind.RGB,
            {
                VImageKind.GRAYSCALE: [cv.COLOR_GRAY2RGB],
                VImageKind.RGBA: [cv.COLOR_RGBA2RGB],
                VImageKind.HSV: [cv.COLOR_HSV2RGB_FULL],
            },
        )

    def to_rgba_image(self):
        return self.convert_image_kind(
            self,
            VImageKind.RGBA,
            {
                VImageKind.GRAYSCALE: [cv.COLOR_GRAY2RGBA],
                VImageKind.RGB: [cv.COLOR_RGB2RGBA],
                VImageKind.HSV: [cv.COLOR_HSV2RGB_FULL, cv.COLOR_RGB2RGBA],
            },
        )

    def to_hsv_image(self):
        return self.convert_image_kind(
            self,
            VImageKind.HSV,
            {
                VImageKind.RGB: [cv.COLOR_RGB2HSV_FULL],
                VImageKind.RGBA: [cv.COLOR_RGBA2RGB, cv.COLOR_RGB2HSV_FULL],
                VImageKind.GRAYSCALE: [cv.COLOR_GRAY2RGB, cv.COLOR_RGB2HSV_FULL],
            },
        )

    def to_rescaled_image(
        self,
        height: int,
        width: int,
        cv_resize_interpolation: int = cv.INTER_CUBIC,
    ):
        mat = cv.resize(self.mat, (width, height), cv_resize_interpolation)
        return attr.evolve(self, mat=mat)

    @staticmethod
    def from_file(path: PathType, disable_exif_orientation: bool = False):
        pil_img = Image.open(path)  # type: ignore
        pil_img.load()

        if not disable_exif_orientation:
            # https://exiftool.org/TagNames/EXIF.html
            # https://github.com/python-pillow/Pillow/blob/main/src/PIL/ImageOps.py#L571
            # Avoid unnecessary copy.
            if pil_img.getexif().get(0x0112):
                pil_img = ImageOps.exif_transpose(pil_img)

        return VImage.from_pil_image(pil_img)

    def to_file(self, path: PathType, disable_to_rgb_image: bool = False):
        image = self
        if not disable_to_rgb_image:
            image = image.to_rgb_image()

        pil_img = image.to_pil_image()
        pil_img.save(path)  # type: ignore


def debug():
    from vkit.opt import get_data_folder
    folder = get_data_folder(__file__)

    VImage.from_file(f'{folder}/Lenna.png').to_grayscale_image().to_file(
        f'{folder}/Lenna-gray.png', disable_to_rgb_image=True
    )
    VImage.from_file(f'{folder}/Lenna.png').to_rgba_image().to_file(
        f'{folder}/Lenna-rgba.png', disable_to_rgb_image=True
    )

    VImage.from_file(f'{folder}/Lenna.png').to_gcn_image().to_file(f'{folder}/Lenna-gcn.png')
    VImage.from_file(f'{folder}/contrast_0.5-gcn.png'
                     ).to_gcn_image().to_file(f'{folder}/contrast_0.5.png')
    VImage.from_file(f'{folder}/saturation_m_100-gcn.png'
                     ).to_gcn_image().to_file(f'{folder}/saturation_m_100.png')
