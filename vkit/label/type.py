from typing import Any, Optional, Dict, List, Sequence, Tuple, Iterable
import enum
import copy

import attr
import numpy as np
import numpy.typing as npt
import cv2 as cv

from vkit.image.type import VImage


def point_attr_converter(val):
    return round(float(val))


@attr.define
class VPoint:
    y: int = attr.ib(converter=point_attr_converter)
    x: int = attr.ib(converter=point_attr_converter)

    def clone(self):
        return attr.evolve(self)

    def to_xy_pair(self):
        return (self.x, self.y)

    def to_clipped_point(self, image: VImage):
        return VPoint(
            y=np.clip(self.y, 0, image.height - 1),
            x=np.clip(self.x, 0, image.width - 1),
        )

    def to_rescaled_point(self, image: VImage, rescaled_height: int, rescaled_width: int):
        y = round(rescaled_height * self.y / image.height)
        y = int(np.clip(y, 0, rescaled_height - 1))

        x = round(rescaled_width * self.x / image.width)
        x = int(np.clip(x, 0, rescaled_width - 1))

        return VPoint(y=y, x=x)


class VPointList(List[VPoint]):

    @staticmethod
    def from_np_array(np_points: npt.NDArray):
        points = VPointList()
        for np_point in np_points:
            x, y = np_point
            points.append(VPoint(y=y, x=x))
        return points

    @staticmethod
    def from_xy_pairs(xy_pairs: Iterable[Tuple[int, int]]):
        return VPointList(VPoint(y=y, x=x) for x, y in xy_pairs)

    @staticmethod
    def from_flatten_xy_pairs(flatten_xy_pairs: Sequence[int]):
        # [x0, y0, x1, y1, ...]
        flatten_xy_pairs = tuple(flatten_xy_pairs)
        assert flatten_xy_pairs and len(flatten_xy_pairs) % 2 == 0

        points = VPointList()
        idx = 0
        while idx < len(flatten_xy_pairs):
            x = flatten_xy_pairs[idx]
            y = flatten_xy_pairs[idx + 1]
            points.append(VPoint(y=y, x=x))
            idx += 2

        return points

    @staticmethod
    def from_point(point: VPoint):
        return VPointList((point,))

    def clone(self):
        points = VPointList()
        for point in self:
            points.append(point.clone())
        return points

    def to_xy_pairs(self):
        return [point.to_xy_pair() for point in self]

    def to_np_array(self):
        return np.array(self.to_xy_pairs(), dtype=np.int32)

    def to_clipped_points(self, image: VImage):
        return VPointList(point.to_clipped_point(image) for point in self)

    def to_rescaled_points(self, image: VImage, rescaled_height: int, rescaled_width: int):
        points = VPointList()
        for point in self:
            points.append(point.to_rescaled_point(image, rescaled_height, rescaled_width))
        return points


@attr.define
class VBox:
    up: int
    down: int
    left: int
    right: int

    @property
    def height(self):
        return self.down + 1 - self.up

    @property
    def width(self):
        return self.right + 1 - self.left

    @property
    def shape(self):
        return self.height, self.width

    def to_clipped_box(self, image: VImage):
        return VBox(
            up=np.clip(self.up, 0, image.height - 1),
            down=np.clip(self.down, 0, image.height - 1),
            left=np.clip(self.left, 0, image.width - 1),
            right=np.clip(self.right, 0, image.width - 1),
        )

    def clone(self):
        return attr.evolve(self)

    def extract_image(self, image: VImage):
        return attr.evolve(
            image,
            mat=image.mat[self.up:self.down + 1, self.left:self.right + 1],
        )


@attr.define
class VPolygon:
    points: VPointList = attr.ib(converter=VPointList)

    def __attrs_post_init__(self):
        assert self.points

    @staticmethod
    def from_np_array(np_points: npt.NDArray):
        return VPolygon(points=VPointList.from_np_array(np_points))

    @staticmethod
    def from_xy_pairs(xy_pairs: Iterable[Tuple[int, int]]):
        return VPolygon(points=VPointList.from_xy_pairs(xy_pairs))

    @staticmethod
    def from_flatten_xy_pairs(flatten_xy_pairs: Sequence[int]):
        return VPolygon(points=VPointList.from_flatten_xy_pairs(flatten_xy_pairs))

    def to_xy_pairs(self):
        return self.points.to_xy_pairs()

    def to_np_array(self):
        return self.points.to_np_array()

    def to_clipped_points(self, image: VImage):
        return self.points.to_clipped_points(image)

    def to_clipped_polygon(self, image: VImage):
        return VPolygon(points=self.to_clipped_points(image))

    def to_bounding_box_with_np_points(self, shift_np_points: bool = False):
        xy_pairs = self.to_xy_pairs()

        x_min = xy_pairs[0][0]
        x_max = x_min
        y_min = xy_pairs[0][1]
        y_max = y_min
        for x, y in xy_pairs:
            x_min = min(x_min, x)
            x_max = max(x_max, x)
            y_min = min(y_min, y)
            y_max = max(y_max, y)

        np_points = np.array(xy_pairs, dtype=np.int32)

        if shift_np_points:
            np_points[:, 0] -= x_min
            np_points[:, 1] -= y_min

        bounding_box = VBox(up=y_min, down=y_max, left=x_min, right=x_max)
        return bounding_box, np_points

    def to_bounding_box(self):
        bounding_box, _ = self.to_bounding_box_with_np_points()
        return bounding_box

    def to_rescaled_polygon(
        self,
        image: VImage,
        rescaled_height: int,
        rescaled_width: int,
    ):
        return VPolygon(
            points=self.points.to_rescaled_points(image, rescaled_height, rescaled_width)
        )

    def clone(self):
        return VPolygon(points=self.points.clone())


@attr.define
class VTextPolygon:
    text: str
    polygon: VPolygon
    meta: Optional[Dict[str, Any]] = None

    def __attrs_post_init__(self):
        assert self.text

    def to_rescaled_text_polygon(
        self,
        image: VImage,
        rescaled_height: int,
        rescaled_width: int,
    ):
        new_polygon = self.polygon.to_rescaled_polygon(image, rescaled_height, rescaled_width)
        return attr.evolve(self, polygon=new_polygon)

    def clone(self):
        return attr.evolve(
            self,
            polygon=self.polygon.clone(),
            meta=None if not self.meta else copy.deepcopy(self.meta),
        )


def extract_rect_area(mat: npt.NDArray, polygon: VPolygon):
    box, np_points = polygon.to_bounding_box_with_np_points(shift_np_points=True)

    rect_polygon_mask_mat = np.zeros(box.shape, dtype=np.uint8)
    cv.fillPoly(rect_polygon_mask_mat, [np_points], 1)
    rect_polygon_mask_mat = rect_polygon_mask_mat.astype(np.bool8)

    rect_mask_mat = mat[box.up:box.down + 1, box.left:box.right + 1]

    return rect_mask_mat, rect_polygon_mask_mat


def fill_mat_opt(mat, polygon, value):
    rect_mask_mat, rect_polygon_mask_mat = extract_rect_area(mat, polygon)
    np.putmask(rect_mask_mat, rect_polygon_mask_mat, value)


class VImageMaskPolygonsMergeMode(enum.Enum):
    UNION = enum.auto()
    DISTINCT = enum.auto()
    INTERSECTION = enum.auto()


@attr.define
class VImageMask:
    mat: npt.NDArray

    def __attrs_post_init__(self):
        if self.mat.dtype != np.uint8:
            raise RuntimeError('mat.dtype != np.uint8')
        if self.mat.ndim != 2:
            raise RuntimeError('ndim should == 2.')

    @staticmethod
    def from_shape(height: int, width: int):
        mat = np.zeros((height, width), dtype=np.uint8)
        return VImageMask(mat=mat)

    @staticmethod
    def from_shape_and_polygons(
        height: int,
        width: int,
        polygons: Iterable[VPolygon],
        mode: VImageMaskPolygonsMergeMode = VImageMaskPolygonsMergeMode.UNION,
    ):
        if mode != VImageMaskPolygonsMergeMode.UNION:
            mask_mat = np.zeros((height, width), dtype=np.uint32)
            for polygon in polygons:
                rect_mask_mat, rect_polygon_mask_mat = extract_rect_area(mask_mat, polygon)
                rect_mask_mat[rect_polygon_mask_mat] += 1

            if mode == VImageMaskPolygonsMergeMode.DISTINCT:
                mask_mat = (mask_mat == 1).astype(np.uint8)

            elif mode == VImageMaskPolygonsMergeMode.INTERSECTION:
                mask_mat = (mask_mat > 1).astype(np.uint8)

            else:
                raise NotImplementedError()

            return VImageMask(mat=mask_mat)  # type: ignore

        else:
            image_mask = VImageMask.from_shape(height, width)
            for polygon in polygons:
                fill_mat_opt(image_mask.mat, polygon, 1)
            return image_mask

    @staticmethod
    def from_image_and_polygons(
        image: VImage,
        polygons: Iterable[VPolygon],
        mode: VImageMaskPolygonsMergeMode = VImageMaskPolygonsMergeMode.UNION,
    ):
        return VImageMask.from_shape_and_polygons(image.height, image.width, polygons, mode)

    @property
    def height(self):
        return self.mat.shape[0]

    @property
    def width(self):
        return self.mat.shape[1]

    @property
    def shape(self):
        return self.height, self.width

    def to_rescaled_image_mask(
        self,
        height: int,
        width: int,
        cv_resize_interpolation: int = cv.INTER_NEAREST_EXACT,
    ):
        mat = cv.resize(self.mat, (width, height), cv_resize_interpolation)
        return VImageMask(mat=mat)

    def clone(self):
        return attr.evolve(self, mat=self.mat.copy())


@attr.define
class VImageScoreMap:
    mat: npt.NDArray

    def __attrs_post_init__(self):
        if self.mat.dtype != np.float32:
            raise RuntimeError('mat.dtype != np.float32')
        if self.mat.ndim != 2:
            raise RuntimeError('ndim should == 2.')

    @staticmethod
    def from_image_mask(image_mask: VImageMask):
        mat = image_mask.mat.astype(np.float32)
        return VImageScoreMap(mat=mat)  # type: ignore

    @staticmethod
    def from_shape_and_polygon_value_pairs(
        height: int,
        width: int,
        polygon_value_pairs: Iterable[Tuple[VPolygon, float]],
    ):
        score_map_mat = np.zeros((height, width), dtype=np.float32)
        for polygon, value in polygon_value_pairs:
            fill_mat_opt(score_map_mat, polygon, value)
        return VImageScoreMap(mat=score_map_mat)

    @staticmethod
    def from_image_and_polygon_value_pairs(
        image: VImage,
        polygon_value_pairs: Iterable[Tuple[VPolygon, float]],
    ):
        return VImageScoreMap.from_shape_and_polygon_value_pairs(
            image.height,
            image.width,
            polygon_value_pairs,
        )

    @property
    def height(self):
        return self.mat.shape[0]

    @property
    def width(self):
        return self.mat.shape[1]

    @property
    def shape(self):
        return self.height, self.width

    def to_rescaled_image_score_map(self, height, width):
        mat = cv.resize(self.mat, (width, height), cv.INTER_LINEAR)
        return VImageScoreMap(mat=mat)

    def clone(self):
        return attr.evolve(self, mat=self.mat.copy())
