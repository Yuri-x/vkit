from typing import Callable, Generic, Type, Union, Tuple, Optional
import numpy as np
from vkit.image.type import VImage
from vkit.augmentation.opt import (
    T_CONFIG,
    handle_config_and_rnd,
)


class PhotometricDistortion(Generic[T_CONFIG]):

    def __init__(self, config_cls: Type[T_CONFIG], func: Callable[..., VImage]):
        self.config_cls = config_cls
        self.func = func

    def __repr__(self):
        return self.func.__name__

    def distort_image(
        self,
        config_or_config_generator: Union[T_CONFIG,
                                          Callable[[Tuple[int, int], np.random.RandomState],
                                                   T_CONFIG]],
        image: VImage,
        rnd: Optional[np.random.RandomState] = None,
    ):
        config, rnd = handle_config_and_rnd(
            self.config_cls,
            config_or_config_generator,
            image.shape,
            rnd,
        )

        kwargs = {
            'image': image,
            'config': config,
        }
        if rnd:
            kwargs['rnd'] = rnd

        return self.func(**kwargs)
