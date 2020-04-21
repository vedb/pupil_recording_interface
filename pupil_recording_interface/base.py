""""""
import abc
import inspect


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
                f"positional arguments {config_args}, got {len(args)}"
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
    _additional_kwargs = {}
    _optional_args = tuple()  # make these positional constructor args optional

    @classmethod
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

    @classmethod
    def get_constructor_args(cls, config, **kwargs):
        """ Construct and instance of a class from a Config. """
        # get constructor signature
        cls_args, cls_kwargs = cls.get_params()

        # update from _additional_kwargs
        # TODO we probably should merge this with the Config method
        for name, value in cls._additional_kwargs.items():
            if name not in cls_kwargs:
                cls_kwargs[name] = value

        # update matching keyword arguments
        for name, param in cls_kwargs.items():
            try:
                cls_kwargs[name] = getattr(config, name)
            except AttributeError:
                cls_kwargs[name] = param

        # update matching positional arguments
        for name in cls_args:
            if name not in cls_kwargs:
                try:
                    cls_kwargs[name] = getattr(config, name)
                except AttributeError:
                    # TODO the missing arguments can be supplied by
                    #  kwargs. We should still check if all positional
                    #  arguments are set at the end.
                    pass

        # update from kwargs
        for name in cls_kwargs:
            if name in kwargs:
                cls_kwargs[name] = kwargs[name]

        return cls_kwargs

    @classmethod
    def Config(cls, *args, **kwargs):
        """ Configuration for this class. """
        # TODO also get superclass kwargs?
        cls_args, cls_kwargs = cls.get_params()

        for arg in cls._ignore_args:
            cls_args.remove(arg)

        for arg in cls._additional_args:
            cls_args.append(arg)

        for arg, val in cls._additional_kwargs.items():
            if arg not in cls_kwargs:
                cls_kwargs[arg] = val

        for arg in cls._optional_args:
            if arg not in kwargs:
                kwargs[arg] = None

        config_type = config_factory(
            cls.__name__ + "Config", cls_args, cls_kwargs, cls._config_attrs
        )

        return config_type(*args, **kwargs)

    @classmethod
    @abc.abstractmethod
    def from_config(cls, config, *args, **kwargs):
        """ Create an instance from a Config. """
