from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    Iterable,
    Type,
    TypeVar,
    Union,
    Sequence,
    Tuple,
    Optional,
)

import attr
import numpy as np

from vkit.image.type import VImage
from vkit.label.type import (
    VPoint,
    VPointList,
    VPolygon,
    VImageMask,
    VImageScoreMap,
)
from vkit.augmentation.opt import (
    T_CONFIG,
    handle_config_and_rnd,
)
from .grid_rendering.grid_creator import create_dst_image_grid_and_shift_amounts_and_rescale_ratios
from .grid_rendering.grid_blender import (
    blend_src_to_dst_image,
    blend_src_to_dst_image_score_map,
    blend_src_to_dst_image_mask,
)

T_STATE = TypeVar('T_STATE')
T_CALL_FUNC_X_RETURN = TypeVar('T_CALL_FUNC_X_RETURN')


@attr.define
class GeometricDistortionResult:
    image: VImage
    image_mask: Optional[VImageMask] = None
    image_score_map: Optional[VImageScoreMap] = None
    active_image_mask: Optional[VImageMask] = None
    point: Optional[VPoint] = None
    points: Optional[VPointList] = None
    polygon: Optional[VPolygon] = None
    polygons: Optional[Sequence[VPolygon]] = None
    config: Optional[Any] = None
    state: Optional[Any] = None


class GeometricDistortion(Generic[T_CONFIG, T_STATE, T_CALL_FUNC_X_RETURN]):

    def __init__(
        self,
        config_cls: Type[T_CONFIG],
        state_cls: Optional[Type[T_STATE]],
        func_image: Callable[..., VImage],
        func_image_mask: Callable[..., VImageMask],
        func_image_score_map: Callable[..., VImageScoreMap],
        func_active_image_mask: Optional[Callable[..., VImageMask]],
        func_point: Optional[Callable[..., VPoint]],
        func_points: Optional[Callable[..., VPointList]],
        func_polygon: Optional[Callable[..., VPolygon]],
        func_polygons: Optional[Callable[..., Sequence[VPolygon]]],
    ):
        self.config_cls = config_cls
        self.state_cls = state_cls

        self.func_image = func_image
        self.func_image_score_map = func_image_score_map
        self.func_image_mask = func_image_mask
        self.func_active_image_mask = func_active_image_mask

        self.func_point = func_point
        self.func_points = func_points
        self.func_polygon = func_polygon
        self.func_polygons = func_polygons

    def generate_config_and_state_and_image_x_and_shape(
        self,
        config_or_config_generator: Union[T_CONFIG,
                                          Callable[[Tuple[int, int], np.random.RandomState],
                                                   T_CONFIG]],
        image_x_or_shape: Union[VImage, VImageMask, VImageScoreMap, Tuple[int, int]],
        rnd: Optional[np.random.RandomState] = None,
    ):
        if isinstance(image_x_or_shape, (list, tuple)):
            assert len(image_x_or_shape) == 2
            image_x = None
            shape = image_x_or_shape
        else:
            image_x = image_x_or_shape
            shape = image_x.shape

        config, rnd = handle_config_and_rnd(
            self.config_cls,
            config_or_config_generator,
            shape,
            rnd,
        )

        state: Optional[T_STATE] = None

        if self.state_cls:
            kwargs = {
                'config': config,
                'shape': shape,
            }
            if rnd:
                kwargs['rnd'] = rnd
            state = self.state_cls(**kwargs)
        else:
            state = None

        return config, state, image_x, shape

    def generate_config_and_state(
        self,
        config_or_config_generator: Union[T_CONFIG,
                                          Callable[[Tuple[int, int], np.random.RandomState],
                                                   T_CONFIG]],
        image_x_or_shape: Union[VImage, VImageMask, VImageScoreMap, Tuple[int, int]],
        rnd: Optional[np.random.RandomState] = None,
    ):
        config, state, _, _ = self.generate_config_and_state_and_image_x_and_shape(
            config_or_config_generator,
            image_x_or_shape,
            rnd,
        )
        return config, state

    def generate_config(
        self,
        config_or_config_generator: Union[T_CONFIG,
                                          Callable[[Tuple[int, int], np.random.RandomState],
                                                   T_CONFIG]],
        image_x_or_shape: Union[VImage, VImageMask, VImageScoreMap, Tuple[int, int]],
        rnd: Optional[np.random.RandomState] = None,
    ):
        config, _, _, _ = self.generate_config_and_state_and_image_x_and_shape(
            config_or_config_generator,
            image_x_or_shape,
            rnd,
        )
        return config

    def generate_state(
        self,
        config_or_config_generator: Union[T_CONFIG,
                                          Callable[[Tuple[int, int], np.random.RandomState],
                                                   T_CONFIG]],
        image_x_or_shape: Union[VImage, VImageMask, VImageScoreMap, Tuple[int, int]],
        rnd: Optional[np.random.RandomState] = None,
    ):
        _, state, _, _ = self.generate_config_and_state_and_image_x_and_shape(
            config_or_config_generator,
            image_x_or_shape,
            rnd,
        )
        return state

    def handle_config_and_state_and_rnd(
        self,
        config_or_config_generator,
        state,
        shape,
        rnd,
    ):
        config, rnd = handle_config_and_rnd(
            self.config_cls,
            config_or_config_generator,
            shape,
            rnd,
        )

        if self.state_cls:
            if not state:
                kwargs = {
                    'config': config,
                    'shape': shape,
                }
                if rnd:
                    kwargs['rnd'] = rnd
                state = self.state_cls(**kwargs)
        else:
            state = None

        return config, state, rnd

    def call_func_x(
        self,
        func: Callable[..., T_CALL_FUNC_X_RETURN],
        config_or_config_generator,
        state: Optional[T_STATE],
        image_x_name,
        image_x_or_shape,
        rnd,
        **extra_kwargs,
    ) -> T_CALL_FUNC_X_RETURN:
        config, state, image_x, shape = self.generate_config_and_state_and_image_x_and_shape(
            config_or_config_generator,
            image_x_or_shape,
            rnd,
        )

        kwargs: Dict[str, Any] = {
            'config': config,
        }

        if image_x_name == 'shape':
            kwargs['shape'] = shape
        else:
            assert image_x
            kwargs[image_x_name] = image_x

        if state:
            kwargs['state'] = state
        if rnd:
            kwargs['rnd'] = rnd

        kwargs.update(extra_kwargs)

        return func(**kwargs)

    def distort_image(
        self,
        config_or_config_generator: Union[T_CONFIG,
                                          Callable[[Tuple[int, int], np.random.RandomState],
                                                   T_CONFIG]],
        image: VImage,
        state: Optional[T_STATE] = None,
        rnd: Optional[np.random.RandomState] = None,
    ):
        return self.call_func_x(
            func=self.func_image,
            config_or_config_generator=config_or_config_generator,
            state=state,
            image_x_name='image',
            image_x_or_shape=image,
            rnd=rnd,
        )

    def distort_image_score_map(
        self,
        config_or_config_generator: Union[T_CONFIG,
                                          Callable[[Tuple[int, int], np.random.RandomState],
                                                   T_CONFIG]],
        image_score_map: VImageScoreMap,
        state: Optional[T_STATE] = None,
        rnd: Optional[np.random.RandomState] = None,
    ):
        return self.call_func_x(
            func=self.func_image_score_map,
            config_or_config_generator=config_or_config_generator,
            state=state,
            image_x_name='image_score_map',
            image_x_or_shape=image_score_map,
            rnd=rnd,
        )

    def distort_image_mask(
        self,
        config_or_config_generator: Union[T_CONFIG,
                                          Callable[[Tuple[int, int], np.random.RandomState],
                                                   T_CONFIG]],
        image_mask: VImageMask,
        state: Optional[T_STATE] = None,
        rnd: Optional[np.random.RandomState] = None,
    ):
        return self.call_func_x(
            func=self.func_image_mask,
            config_or_config_generator=config_or_config_generator,
            state=state,
            image_x_name='image_mask',
            image_x_or_shape=image_mask,
            rnd=rnd,
        )

    def get_active_image_mask(
        self,
        config_or_config_generator: Union[T_CONFIG,
                                          Callable[[Tuple[int, int], np.random.RandomState],
                                                   T_CONFIG]],
        image: VImage,
        state: Optional[T_STATE] = None,
        rnd: Optional[np.random.RandomState] = None,
    ):
        if self.func_active_image_mask:
            return self.call_func_x(
                func=self.func_active_image_mask,
                config_or_config_generator=config_or_config_generator,
                state=state,
                image_x_name='image',
                image_x_or_shape=image,
                rnd=rnd,
            )

        else:
            image_mask = VImageMask.from_shape(image.height, image.width)
            image_mask.mat.fill(1)
            return self.distort_image_mask(
                config_or_config_generator=config_or_config_generator,
                state=state,
                image_mask=image_mask,
                rnd=rnd,
            )

    def distort_point(
        self,
        config_or_config_generator: Union[T_CONFIG,
                                          Callable[[Tuple[int, int], np.random.RandomState],
                                                   T_CONFIG]],
        image_x_or_shape: Union[VImage, VImageMask, VImageScoreMap, Tuple[int, int]],
        point: VPoint,
        state: Optional[T_STATE] = None,
        rnd: Optional[np.random.RandomState] = None,
    ):
        if self.func_point:
            return self.call_func_x(
                func=self.func_point,
                config_or_config_generator=config_or_config_generator,
                state=state,
                image_x_name='shape',
                image_x_or_shape=image_x_or_shape,
                rnd=rnd,
                point=point,
            )

        elif self.func_points:
            new_points = self.call_func_x(
                func=self.func_points,
                config_or_config_generator=config_or_config_generator,
                state=state,
                image_x_name='shape',
                image_x_or_shape=image_x_or_shape,
                rnd=rnd,
                points=[point],
            )
            return new_points[0]

        else:
            raise RuntimeError('Neither func_point nor func_points is provided.')

    def distort_points(
        self,
        config_or_config_generator: Union[T_CONFIG,
                                          Callable[[Tuple[int, int], np.random.RandomState],
                                                   T_CONFIG]],
        image_x_or_shape: Union[VImage, VImageMask, VImageScoreMap, Tuple[int, int]],
        points: Union[VPointList, Iterable[VPoint]],
        state: Optional[T_STATE] = None,
        rnd: Optional[np.random.RandomState] = None,
    ):
        points = VPointList(points)

        if self.func_points:
            return self.call_func_x(
                func=self.func_points,
                config_or_config_generator=config_or_config_generator,
                state=state,
                image_x_name='shape',
                image_x_or_shape=image_x_or_shape,
                rnd=rnd,
                points=points,
            )

        elif self.func_point:
            # NOTE: config_generator will only be called once.
            config, state = self.generate_config_and_state(
                config_or_config_generator=config_or_config_generator,
                image_x_or_shape=image_x_or_shape,
                rnd=rnd,
            )

            new_points = VPointList()
            for point in points:
                new_point = self.distort_point(
                    config_or_config_generator=config,
                    image_x_or_shape=image_x_or_shape,
                    point=point,
                    state=state,
                    rnd=rnd,
                )
                new_points.append(new_point)
            return new_points

        else:
            raise RuntimeError('Neither func_point nor func_points is provided.')

    def distort_polygon(
        self,
        config_or_config_generator: Union[T_CONFIG,
                                          Callable[[Tuple[int, int], np.random.RandomState],
                                                   T_CONFIG]],
        image_x_or_shape: Union[VImage, VImageMask, VImageScoreMap, Tuple[int, int]],
        polygon: VPolygon,
        state: Optional[T_STATE] = None,
        rnd: Optional[np.random.RandomState] = None,
    ):
        if self.func_polygon:
            return self.call_func_x(
                func=self.func_polygon,
                config_or_config_generator=config_or_config_generator,
                state=state,
                image_x_name='shape',
                image_x_or_shape=image_x_or_shape,
                rnd=rnd,
                polygon=polygon,
            )

        elif self.func_polygons:
            new_polygons = self.call_func_x(
                func=self.func_polygons,
                config_or_config_generator=config_or_config_generator,
                state=state,
                image_x_name='shape',
                image_x_or_shape=image_x_or_shape,
                rnd=rnd,
                polygons=[polygon],
            )
            return new_polygons[0]

        elif self.func_points:
            new_points = self.distort_points(
                config_or_config_generator=config_or_config_generator,
                image_x_or_shape=image_x_or_shape,
                points=polygon.points,
                state=state,
                rnd=rnd,
            )
            return VPolygon(points=new_points)

        elif self.func_point:
            # NOTE: config_generator will only be called once.
            config, state = self.generate_config_and_state(
                config_or_config_generator=config_or_config_generator,
                image_x_or_shape=image_x_or_shape,
                rnd=rnd,
            )

            new_points = VPointList()
            for point in polygon.points:
                new_point = self.distort_point(
                    config_or_config_generator=config,
                    image_x_or_shape=image_x_or_shape,
                    point=point,
                    state=state,
                    rnd=rnd,
                )
                new_points.append(new_point)

            return VPolygon(points=new_points)

        else:
            raise RuntimeError('No valid function.')

    def distort_polygons(
        self,
        config_or_config_generator: Union[T_CONFIG,
                                          Callable[[Tuple[int, int], np.random.RandomState],
                                                   T_CONFIG]],
        image_x_or_shape: Union[VImage, VImageMask, VImageScoreMap, Tuple[int, int]],
        polygons: Iterable[VPolygon],
        state: Optional[T_STATE] = None,
        rnd: Optional[np.random.RandomState] = None,
    ):
        if self.func_polygons:
            return self.call_func_x(
                func=self.func_polygons,
                config_or_config_generator=config_or_config_generator,
                state=state,
                image_x_name='shape',
                image_x_or_shape=image_x_or_shape,
                rnd=rnd,
                polygons=polygons,
            )

        else:
            # NOTE: config_generator will only be called once.
            config, state = self.generate_config_and_state(
                config_or_config_generator=config_or_config_generator,
                image_x_or_shape=image_x_or_shape,
                rnd=rnd,
            )

            new_polygons = []
            for polygon in polygons:
                new_polygon = self.distort_polygon(
                    config_or_config_generator=config,
                    image_x_or_shape=image_x_or_shape,
                    polygon=polygon,
                    state=state,
                    rnd=rnd,
                )
                new_polygons.append(new_polygon)

            return new_polygons

    def distort(
        self,
        config_or_config_generator: Union[T_CONFIG,
                                          Callable[[Tuple[int, int], np.random.RandomState],
                                                   T_CONFIG]],
        image: VImage,
        image_mask: Optional[VImageMask] = None,
        image_score_map: Optional[VImageScoreMap] = None,
        point: Optional[VPoint] = None,
        points: Optional[VPointList] = None,
        polygon: Optional[VPolygon] = None,
        polygons: Optional[Iterable[VPolygon]] = None,
        get_active_image_mask: bool = False,
        get_config: bool = False,
        get_state: bool = False,
        rnd: Optional[np.random.RandomState] = None,
    ):
        config, state = self.generate_config_and_state(
            config_or_config_generator,
            image,
            rnd,
        )
        result = GeometricDistortionResult(
            image=self.distort_image(
                config,
                image,
                state=state,
                rnd=rnd,
            )
        )
        if image_mask:
            result.image_mask = self.distort_image_mask(
                config,
                image_mask,
                state=state,
                rnd=rnd,
            )
        if image_score_map:
            result.image_score_map = self.distort_image_score_map(
                config,
                image_score_map,
                state=state,
                rnd=rnd,
            )
        if point:
            result.point = self.distort_point(
                config,
                image,
                point,
                state=state,
                rnd=rnd,
            )
        if points:
            result.points = self.distort_points(
                config,
                image,
                points,
                state=state,
                rnd=rnd,
            )
        if polygon:
            result.polygon = self.distort_polygon(
                config,
                image,
                polygon,
                state=state,
                rnd=rnd,
            )
        if polygons:
            result.polygons = self.distort_polygons(
                config,
                image,
                polygons,
                state=state,
                rnd=rnd,
            )
        if get_active_image_mask:
            result.active_image_mask = self.get_active_image_mask(
                config,
                image,
                state=state,
                rnd=rnd,
            )
        if get_config:
            result.config = config
        if get_state:
            result.state = state
        return result


class StateImageGridBased:

    def __init__(self, src_image_grid, point_projector):
        self.src_image_grid = src_image_grid
        self.point_projector = point_projector

        (
            self.dst_image_grid,
            (self.shift_amount_y, self.shift_amount_x),
            (self.rescale_ratio_y, self.rescale_ratio_x),
        ) = create_dst_image_grid_and_shift_amounts_and_rescale_ratios(
            self.src_image_grid,
            self.point_projector,
            rescale_as_src=False,
        )

    def shift_and_rescale_point(self, point):
        return VPoint(
            y=(point.y - self.shift_amount_y) * self.rescale_ratio_y,
            x=(point.x - self.shift_amount_x) * self.rescale_ratio_x,
        )


def geometric_distortion_image_grid_based_image(config, state, image):
    return blend_src_to_dst_image(
        image,
        state.src_image_grid,
        state.dst_image_grid,
    )


def geometric_distortion_image_grid_based_image_score_map(config, state, image_score_map):
    return blend_src_to_dst_image_score_map(
        image_score_map,
        state.src_image_grid,
        state.dst_image_grid,
    )


def geometric_distortion_image_grid_based_image_mask(config, state, image_mask):
    return blend_src_to_dst_image_mask(image_mask, state.src_image_grid, state.dst_image_grid)


def geometric_distortion_image_grid_based_active_image_mask(config, state, image):
    border_polygon = state.dst_image_grid.generate_border_polygon()
    return VImageMask.from_shape_and_polygons(
        state.dst_image_grid.image_height,
        state.dst_image_grid.image_width,
        [border_polygon],
    )


def geometric_distortion_image_grid_based_point(config, state, shape, point):
    return state.shift_and_rescale_point(state.point_projector.project_point(point))


class GeometricDistortionImageGridBased(
    GeometricDistortion[T_CONFIG, T_STATE, T_CALL_FUNC_X_RETURN]
):

    def __init__(
        self,
        config_cls: Type[T_CONFIG],
        state_cls: Type[T_STATE],
        func_image: Callable[..., VImage] = geometric_distortion_image_grid_based_image,
        func_image_mask: Callable[...,
                                  VImageMask] = geometric_distortion_image_grid_based_image_mask,
        func_image_score_map: Callable[
            ..., VImageScoreMap] = geometric_distortion_image_grid_based_image_score_map,
        func_active_image_mask: Optional[Callable[
            ..., VImageMask]] = geometric_distortion_image_grid_based_active_image_mask,
        func_point: Optional[Callable[..., VPoint]] = geometric_distortion_image_grid_based_point,
        func_points: Optional[Callable[..., VPointList]] = None,
        func_polygon: Optional[Callable[..., VPolygon]] = None,
        func_polygons: Optional[Callable[..., Sequence[VPolygon]]] = None,
    ):
        assert issubclass(state_cls, StateImageGridBased)
        super().__init__(
            config_cls=config_cls,
            state_cls=state_cls,
            func_image=func_image,
            func_image_mask=func_image_mask,
            func_image_score_map=func_image_score_map,
            func_active_image_mask=func_active_image_mask,
            func_point=func_point,
            func_points=func_points,
            func_polygon=func_polygon,
            func_polygons=func_polygons,
        )


def debug_geometric_distortion(
    tag: str,
    geometric_distortion: GeometricDistortion[T_CONFIG, T_STATE, Any],
    config: T_CONFIG,
    src_polygon: VPolygon,
    folder: str,
    src_image_name: str,
) -> Optional[T_STATE]:
    from vkit.image.type import VImage

    from vkit.label.visualization import (
        visualize_image_mask,
        visualize_image_score_map,
        visualize_polygons,
    )

    src_image = VImage.from_file(f'{folder}/{src_image_name}')

    # Test distort_image.
    state = geometric_distortion.generate_state(config, src_image)
    dst_image = geometric_distortion.distort_image(config, src_image, state=state)
    dst_image.to_file(f'{folder}/{tag}-dst-image.png')

    # Test distort_image_mask.
    src_image_mask = VImageMask.from_image_and_polygons(src_image, [src_polygon])
    visualize_image_mask(src_image_mask).to_file(f'{folder}/{tag}-src-image-mask.png')

    dst_image_mask = geometric_distortion.distort_image_mask(config, src_image_mask, state=state)
    visualize_image_mask(dst_image_mask).to_file(f'{folder}/{tag}-dst-image-mask.png')

    # Test get_active_image_mask.
    active_image_mask = geometric_distortion.get_active_image_mask(config, src_image, state=state)
    visualize_image_mask(active_image_mask).to_file(f'{folder}/{tag}-active-image-mask.png')

    # Test distort_image_score_map.
    src_image_score_map = VImageScoreMap.from_image_and_polygon_value_pairs(
        src_image,
        [(src_polygon, 1.0)],
    )
    visualize_image_score_map(src_image_score_map).to_file(f'{folder}/{tag}-src-score-map.png')

    dst_image_score_map = geometric_distortion.distort_image_score_map(
        config, src_image_score_map, state=state
    )
    assert dst_image_score_map.mat.max() == 1.0
    visualize_image_score_map(dst_image_score_map).to_file(f'{folder}/{tag}-dst-score-map.png')

    # Test distort_polygons.
    visualize_polygons(src_image, [src_polygon]).to_file(f'{folder}/{tag}-src-polygon.png')

    dst_polygons = geometric_distortion.distort_polygons(
        config, src_image, [src_polygon], state=state
    )
    visualize_polygons(dst_image, dst_polygons).to_file(f'{folder}/{tag}-dst-polygon.png')

    return state
