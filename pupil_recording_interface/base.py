""""""
import abc

from pupil_recording_interface.utils import get_params


class BaseConfig:
    """ Base class for all configurations. """

    def __init__(self, **kwargs):
        """ Constructor. """
        # TODO Replace with self.kwargs = kwargs?
        for k, v in kwargs.items():
            setattr(self, k, v)


def config_factory(name, config_args, config_kwargs, config_attrs):
    """ Create a new config type with arguments and attributes. """

    def __init__(self, *args, **kwargs):
        """ Constructor. """
        # check if positional arguments are in kwargs
        args = list(args)
        for idx, arg_name in enumerate(config_args):
            if arg_name in kwargs:
                args.insert(idx, kwargs.pop(arg_name))

        # check that all positional arguments are specified
        if len(args) != len(config_args):
            raise TypeError(
                f"{self.__class__.__name__} expected {len(config_args)} "
                f"positional arguments, got {len(args)}"
            )

        # set positional arguments
        for arg_name, value in zip(config_args, args):
            setattr(self, arg_name, value)

        # set keyword arguments
        for arg_name, value in config_kwargs.items():
            if not hasattr(self, arg_name):
                setattr(self, arg_name, value)

        BaseConfig.__init__(self, **kwargs)

    attrs = {"__init__": __init__}
    attrs.update(config_attrs)

    return type(name, (BaseConfig,), attrs)


class BaseConfigurable:
    """ Base class for all configurables. """

    _config_attrs = {}
    _ignore_args = tuple()  # ignore these positional constructor args
    _additional_args = tuple()  # add these positional constructor args
    _optional_args = tuple()  # make these positional constructor args optional

    @classmethod
    def Config(cls, *args, **kwargs):
        """ Configuration for this class. """
        cls_args, cls_kwargs = get_params(cls)

        for arg in cls._ignore_args:
            cls_args.remove(arg)

        for arg in cls._additional_args:
            cls_args.append(arg)

        for arg in cls._optional_args:
            kwargs[arg] = None

        config_type = config_factory(
            cls.__name__ + "Config", cls_args, cls_kwargs, cls._config_attrs
        )

        return config_type(*args, **kwargs)

    @classmethod
    @abc.abstractmethod
    def from_config(cls, config, *args, **kwargs):
        """ Create an instance from a Config. """
