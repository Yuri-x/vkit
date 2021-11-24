from typing import Type, TypeVar, Callable, Tuple, Union, Optional
import inspect
import numpy as np
import attr

T_CONFIG = TypeVar('T_CONFIG')


def handle_config_and_rnd(
    config_cls: Type[T_CONFIG],
    config_or_config_generator: Union[T_CONFIG, Callable[[Tuple[int, int], np.random.RandomState],
                                                         T_CONFIG]],
    shape: Tuple[int, int],
    rnd: Optional[np.random.RandomState],
) -> Tuple[T_CONFIG, Optional[np.random.RandomState]]:

    if inspect.isfunction(config_or_config_generator):
        config_generator = config_or_config_generator
        if not rnd:
            raise RuntimeError('config_generator but rnd is None.')
        config = config_generator(shape, rnd)

    else:
        config = config_or_config_generator

    if not isinstance(config, config_cls):
        raise RuntimeError(f'config={config} should be instance of {config_cls}.')

    # Handle rnd_state.
    if hasattr(config, 'rnd_state'):
        rnd_state = getattr(config, 'rnd_state')
        if rnd_state:
            # Create/replace rnd.
            rnd = np.random.RandomState()
            rnd.set_state(rnd_state)
        else:
            if not rnd:
                raise RuntimeError('both config.rnd_state and rnd are None.')
            # NOTE: make a copy
            config = attr.evolve(config, rnd_state=rnd.get_state())

    else:
        # Force not passing rnd.
        rnd = None

    return config, rnd
