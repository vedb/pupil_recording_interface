""""""
import abc


class BaseDevice(object):
    """ Base class for all devices. """

    def __init__(self, uid):
        """ Constructor. """
        self.uid = uid

    @property
    @abc.abstractmethod
    def is_started(self):
        """ Whether this device has been started. """

    @abc.abstractmethod
    def start(self):
        """ Start this device. """

    @abc.abstractmethod
    def stop(self):
        """ Stop this device. """
