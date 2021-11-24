from enum import Enum

import attr
import numpy as np
import numpy.typing as npt
from PIL import Image, ImageOps
import cv2 as cv

from vkit.type import PathType


class VImageKind(Enum):
    RGB = 'rgb'
    RGB_GCN = 'rgb-gcn'
    RGBA = 'rgba'
    HSV = 'hsv'
    HSV_GCN = 'hsv-gcn'
    GRAYSCALE = 'grayscale'
    GRAYSCALE_GCN = 'grayscale-gcn'
    NONE = 'none'

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

    def to_rgb_image(self):
        image = self
        skip_clone = False
        if VImageKind.is_gcn(image.kind):
            image = image.to_non_gcn_image()
            skip_clone = True

        if image.kind == VImageKind.RGB:
            return image if skip_clone else image.clone()

        elif image.kind == VImageKind.HSV:
            # NOTE: H range [0, 255]
            mat = cv.cvtColor(image.mat, cv.COLOR_HSV2RGB_FULL)
            return VImage(mat=mat, kind=VImageKind.RGB)

        elif image.kind == VImageKind.GRAYSCALE:
            mat = cv.cvtColor(image.mat, cv.COLOR_GRAY2RGB)
            return VImage(mat=mat, kind=VImageKind.RGB)

        else:
            raise NotImplementedError()

    def to_hsv_image(self):
        image = self
        skip_clone = False
        if VImageKind.is_gcn(image.kind):
            image = image.to_non_gcn_image()
            skip_clone = True

        if image.kind == VImageKind.HSV:
            return image if skip_clone else image.clone()

        elif image.kind == VImageKind.RGB:
            # NOTE: H range [0, 255]
            mat = cv.cvtColor(image.mat, cv.COLOR_RGB2HSV_FULL)
            return VImage(mat=mat, kind=VImageKind.HSV)

        elif image.kind == VImageKind.GRAYSCALE:
            mat = cv.cvtColor(image.mat, cv.COLOR_GRAY2RGB)
            return VImage(mat=mat, kind=VImageKind.RGB).to_hsv_image()

        else:
            raise NotImplementedError()

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

    def to_rescaled_image(self, height: int, width: int, cv_resize_interpolation=cv.INTER_CUBIC):
        mat = cv.resize(self.mat, (width, height), cv_resize_interpolation)
        return attr.evolve(self, mat=mat)

    @staticmethod
    def from_file(path: PathType, disable_exif_orientation=False):
        pil_img = Image.open(path)  # type: ignore
        pil_img.load()

        if not disable_exif_orientation:
            # https://exiftool.org/TagNames/EXIF.html
            # https://github.com/python-pillow/Pillow/blob/main/src/PIL/ImageOps.py#L571
            # Avoid unnecessary copy.
            if pil_img.getexif().get(0x0112):
                pil_img = ImageOps.exif_transpose(pil_img)

        return VImage.from_pil_image(pil_img)

    def to_file(self, path: PathType):
        pil_img = self.to_rgb_image().to_pil_image()
        pil_img.save(path)  # type: ignore


def debug():
    from vkit.opt import get_data_folder
    folder = get_data_folder(__file__)

    VImage.from_file(f'{folder}/Lenna.png').to_gcn_image().to_file(f'{folder}/Lenna-gcn.png')
    VImage.from_file(f'{folder}/contrast_0.5-gcn.png'
                     ).to_gcn_image().to_file(f'{folder}/contrast_0.5.png')
    VImage.from_file(f'{folder}/saturation_m_100-gcn.png'
                     ).to_gcn_image().to_file(f'{folder}/saturation_m_100.png')
