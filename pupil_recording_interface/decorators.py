""""""


class _base_decorator:
    """ Base class for decorators. """

    registry = dict
    name: str

    def __init__(self, type_name):
        """ Constructor. """
        self.type_name = type_name

    def __call__(self, decorated_class):
        """ Decorate class. """
        if self.type_name in self.registry:
            raise ValueError(
                f"{self.name} type {self.type_name} is already in use."
            )
        else:
            self.registry[self.type_name] = decorated_class

        return decorated_class


class device(_base_decorator):
    """ Device decorator. """

    registry = {}
    name = "Device"


class stream(_base_decorator):
    """ Stream decorator. """

    registry = {}
    name = "Stream"


class process(_base_decorator):
    """ Process decorator. """

    registry = {}
    name = "Process"
