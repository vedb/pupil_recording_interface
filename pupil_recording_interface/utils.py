""""""
import inspect
from collections import deque
from multiprocessing.managers import SyncManager

SyncManager.register("deque", deque)


def get_params(cls):
    """ Get constructor parameters for a class. """
    signature = inspect.signature(cls.__init__)

    args = [
        name
        for name, param in signature.parameters.items()
        if param.kind is param.POSITIONAL_OR_KEYWORD
        and param.default is inspect._empty
    ]

    # remove instance parameter
    args = args[1:]

    kwargs = {
        name: param.default
        for name, param in signature.parameters.items()
        if param.kind is param.POSITIONAL_OR_KEYWORD
        and param.default is not inspect._empty
    }

    return args, kwargs


def get_constructor_args(cls, config, **kwargs):
    """ Construct and instance of a class from a Config. """
    # get constructor signature
    cls_args, cls_kwargs = get_params(cls)

    # update matching keyword arguments
    for name, param in cls_kwargs.items():
        cls_kwargs[name] = getattr(config, name, None) or param

    # update matching positional arguments
    for name in cls_args:
        if name not in cls_kwargs:
            try:
                cls_kwargs[name] = getattr(config, name)
            except AttributeError:
                raise ValueError(
                    f"The supplied config does not specify the argument "
                    f"{name} required for constructing an instance of "
                    f"{cls}"
                )
    cls_kwargs.update(kwargs)

    return cls_kwargs


def multiprocessing_deque(maxlen=None):
    """"""
    manager = SyncManager()
    manager.start()
    return manager.deque(maxlen=maxlen)
