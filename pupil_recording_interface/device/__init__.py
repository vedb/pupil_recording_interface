""""""
import abc

from pupil_recording_interface.base import BaseConfigurable
from pupil_recording_interface.decorators import device
from pupil_recording_interface.utils import get_constructor_args


class BaseDevice(BaseConfigurable):
    """ Base class for all devices. """

    def __init__(self, device_uid):
        """ Constructor. """
        self.device_uid = device_uid

    @classmethod
    def from_config(cls, config, **kwargs):
        """ Create a device from a StreamConfig. """
        try:
            return device.registry[config.device_type]._from_config(
                config, **kwargs
            )
        except KeyError:
            raise ValueError(
                f"No such device type: {config.device_type}. "
                f"If you are implementing a custom device, remember to use "
                f"the @pupil_recording_interface.device class decorator."
            )

    @classmethod
    def _from_config(cls, config, **kwargs):
        """ Per-class implementation of from_config. """
        assert device.registry[config.device_type] is cls

        cls_kwargs = get_constructor_args(cls, config, **kwargs)

        return cls(**cls_kwargs)

    @classmethod
    def from_config_list(cls, config_list):
        """ Create a device from a list of StreamConfigs. """
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def is_started(self):
        """ Whether this device has been started. """

    def start(self):
        """ Start this device. """

    def stop(self):
        """ Stop this device. """

    def run_pre_thread_hooks(self):
        """ Run hook(s) before dispatching processing thread(s). """

    def run_post_thread_hooks(self):
        """ Run hook(s) after processing thread(s) finish(es). """
