""""""
from pupil_recording_interface.base import BaseConfigurable


class _base_decorator:
    """ Base class for decorators. """

    registry: dict
    name: str
    config_attr: str
    ignore = tuple()
    add = tuple()
    add_kwargs = dict()

    def __init__(self, type_name, optional=None):
        """ Constructor. """
        self.type_name = type_name
        self.optional = optional or tuple()

    def __call__(self, decorated_class):
        """ Decorate class. """
        if not issubclass(decorated_class, BaseConfigurable):
            raise TypeError(
                "Decorated class must be a subclass of BaseConfigurable"
            )

        if self.type_name in self.registry:
            raise ValueError(
                f"{self.name} type {self.type_name} is already in use."
            )
        else:
            self.registry[self.type_name] = decorated_class

        setattr(decorated_class, self.config_attr, self.type_name)
        decorated_class._config_attrs = {self.config_attr: self.type_name}
        decorated_class._ignore_args = self.ignore
        decorated_class._additional_args = self.add
        decorated_class._additional_kwargs = self.add_kwargs
        decorated_class._optional_args = self.optional

        return decorated_class


class device(_base_decorator):
    """ Device decorator. """

    registry = {}
    name = "Device"
    config_attr = "device_type"


class stream(_base_decorator):
    """ Stream decorator. """

    registry = {}
    name = "Stream"
    config_attr = "stream_type"
    ignore = ("device",)
    add = ("device_type", "device_uid")


class process(_base_decorator):
    """ Process decorator. """

    registry = {}
    name = "Process"
    config_attr = "process_type"
    add_kwargs = {"process_name": None, "paused": False, "block": False}
