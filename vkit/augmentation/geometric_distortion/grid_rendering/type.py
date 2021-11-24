from typing import MutableSequence, Optional
from itertools import chain

import attr

from vkit.image.type import VImage
from vkit.label.type import VPoint, VPolygon, VPointList


@attr.define
class VImageGrid:
    points_2d: MutableSequence[MutableSequence[VPoint]]

    _cache_image_height: Optional[int] = None
    _cache_image_width: Optional[int] = None

    @property
    def num_rows(self):
        return len(self.points_2d)

    @property
    def num_cols(self):
        return len(self.points_2d[0])

    @property
    def flatten_points(self):
        return VPointList(chain.from_iterable(self.points_2d))

    @property
    def image_height(self):
        if self._cache_image_height is None:
            assert min(point.y for point in self.flatten_points) == 0
            self._cache_image_height = max(point.y for point in self.flatten_points) + 1
        return self._cache_image_height

    @property
    def image_width(self):
        if self._cache_image_width is None:
            assert min(point.x for point in self.flatten_points) == 0
            self._cache_image_width = max(point.x for point in self.flatten_points) + 1
        return self._cache_image_width

    @property
    def shape(self):
        return self.num_rows, self.num_cols

    def compatible_with(self, other):
        return self.shape == other.shape

    def generate_polygon(self, polygon_row: int, polygon_col: int):
        return VPolygon(
            points=VPointList([
                # Clockwise.
                self.points_2d[polygon_row][polygon_col],
                self.points_2d[polygon_row][polygon_col + 1],
                self.points_2d[polygon_row + 1][polygon_col + 1],
                self.points_2d[polygon_row + 1][polygon_col],
            ]),
        )

    def generate_polygon_row_col(self):
        for polygon_row in range(self.num_rows - 1):
            for polygon_col in range(self.num_cols - 1):
                yield polygon_row, polygon_col

    def zip_polygons(self, other: 'VImageGrid'):
        assert self.compatible_with(other)
        for polygon_row, polygon_col in self.generate_polygon_row_col():
            self_polygon = self.generate_polygon(polygon_row, polygon_col)
            other_polygon = other.generate_polygon(polygon_row, polygon_col)
            yield (polygon_row, polygon_col), self_polygon, other_polygon

    def generate_border_polygon(self):
        # Clockwise.
        points = VPointList()

        for point in self.points_2d[0]:
            points.append(point)
        for row in range(1, self.num_rows):
            points.append(self.points_2d[row][-1])
        for col in reversed(range(self.num_cols - 1)):
            points.append(self.points_2d[-1][col])
        for row in reversed(range(1, self.num_rows - 1)):
            points.append(self.points_2d[row][0])

        return VPolygon(points=points)

    def to_rescaled_image_grid(self, image: VImage, rescaled_height: int, rescaled_width: int):
        new_points_2d: MutableSequence[MutableSequence[VPoint]] = []
        for points in self.points_2d:
            new_points: MutableSequence[VPoint] = []
            for point in points:
                new_points.append(point.to_rescaled_point(image, rescaled_height, rescaled_width))
            new_points_2d.append(new_points)
        return VImageGrid(points_2d=new_points_2d)
