import numpy as np
from shapely.geometry import Polygon
import pyclipper

from vkit.label.type import VPolygon


def remove_duplicated_xy_pairs(xy_pairs):
    xy_pairs = tuple(map(tuple, xy_pairs))
    unique_xy_pairs = []

    idx = 0
    while idx < len(xy_pairs):
        unique_xy_pairs.append(xy_pairs[idx])

        next_idx = idx + 1
        while next_idx < len(xy_pairs) and xy_pairs[idx] == xy_pairs[next_idx]:
            next_idx += 1
        idx = next_idx

    # Check head & tail.
    if len(unique_xy_pairs) > 1 and unique_xy_pairs[0] == unique_xy_pairs[-1]:
        unique_xy_pairs.pop()

    assert len(unique_xy_pairs) >= 3
    return unique_xy_pairs


def vatti_clip(polygon: VPolygon, ratio, shrink):
    xy_pairs = polygon.to_xy_pairs()

    shapely_polygon = Polygon(xy_pairs)
    assert shapely_polygon.area > 0

    distance = shapely_polygon.area * (1 - np.power(ratio, 2)) / shapely_polygon.length
    if shrink:
        distance *= -1

    clipper = pyclipper.PyclipperOffset()  # type: ignore
    clipper.AddPath(xy_pairs, pyclipper.JT_ROUND, pyclipper.ET_CLOSEDPOLYGON)  # type: ignore

    clipped_paths = clipper.Execute(distance)
    assert clipped_paths
    clipped_path = clipped_paths[0]

    clipped_xy_pairs = remove_duplicated_xy_pairs(clipped_path)
    clipped_polygon = VPolygon.from_xy_pairs(clipped_xy_pairs)

    return clipped_polygon, distance


def shrink_polygon(polygon, ratio):
    return vatti_clip(polygon, ratio, True)


def dilate_polygon(polygon, ratio):
    return vatti_clip(polygon, ratio, False)
