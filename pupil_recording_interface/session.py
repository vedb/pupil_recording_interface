""""""
from warnings import warn


class Session:
    """ Context manager for devices, streams and processes. """

    def __init__(self, *instances):
        """ Constructor.

        Parameters
        ----------
        instances: iterable of any
            Any object(s) with a start and a stop method. The objects' start
            methods will be called on entry in the specified order, the stop
            methods will be called on exit in opposite order.
        """
        warn(
            "The Session context manager is deprecated, you can now use "
            "devices, streams and processes directly as context managers.",
            DeprecationWarning,
        )
        self.instances = instances

    def __enter__(self):
        for instance in self.instances:
            instance.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        for instance in reversed(self.instances):
            instance.stop()
