from typing import List, Iterable
import math

from shapely.ops import unary_union
from shapely.geometry import Polygon, MultiPolygon
from shapely.geometry import CAP_STYLE, JOIN_STYLE

from vkit.label.type import VPolygon


def get_line_lengths(shapely_polygon):
    points = tuple(shapely_polygon.exterior.coords)
    for idx, p0 in enumerate(points):
        p1 = points[(idx + 1) % len(points)]
        length = math.sqrt((p0[0] - p1[0])**2 + (p0[1] - p1[1])**2)
        yield length


def estimate_shapely_polygon_height(shapely_polygon):
    length = max(get_line_lengths(shapely_polygon))
    return shapely_polygon.area / length


def calculate_patch_buffer_eps(shapely_polygon):
    return estimate_shapely_polygon_height(shapely_polygon) / 10


def patch_unionized_unionized_shapely_polygon(unionized_shapely_polygon):
    eps = calculate_patch_buffer_eps(unionized_shapely_polygon)
    unionized_shapely_polygon = unionized_shapely_polygon.buffer(
        eps,
        cap_style=CAP_STYLE.round,
        join_style=JOIN_STYLE.round,
    )
    unionized_shapely_polygon = unionized_shapely_polygon.buffer(
        -eps,
        cap_style=CAP_STYLE.round,
        join_style=JOIN_STYLE.round,
    )
    return unionized_shapely_polygon


def unionize_polygons(polygons: Iterable[VPolygon]):
    shapely_polygons = []
    for polygon in polygons:
        xy_pairs = polygon.to_xy_pairs()
        shapely_polygons.append(Polygon(xy_pairs))

    unionized_shapely_polygons = []

    # Patch unary_union.
    unary_union_output = unary_union(shapely_polygons)
    if not isinstance(unary_union_output, MultiPolygon):
        assert isinstance(unary_union_output, Polygon)
        unary_union_output = [unary_union_output]

    for unionized_shapely_polygon in unary_union_output:
        unionized_shapely_polygon = patch_unionized_unionized_shapely_polygon(
            unionized_shapely_polygon
        )
        unionized_shapely_polygons.append(unionized_shapely_polygon)

    unionized_polygons = [
        VPolygon.from_xy_pairs(unionized_shapely_polygon.exterior.coords)
        for unionized_shapely_polygon in unionized_shapely_polygons
    ]

    scatter_indices: List[int] = []
    for shapely_polygon in shapely_polygons:
        best_unionized_polygon_idx = None
        best_area = 0.0
        conflict = False

        for unionized_polygon_idx, unionized_shapely_polygon in enumerate(
            unionized_shapely_polygons
        ):
            if not unionized_shapely_polygon.intersects(shapely_polygon):
                continue
            area = unionized_shapely_polygon.intersection(shapely_polygon).area
            if area > best_area:
                best_area = area
                best_unionized_polygon_idx = unionized_polygon_idx
                conflict = False
            elif area == best_area:
                conflict = True

        assert not conflict
        assert best_unionized_polygon_idx is not None
        scatter_indices.append(best_unionized_polygon_idx)

    return unionized_polygons, scatter_indices
