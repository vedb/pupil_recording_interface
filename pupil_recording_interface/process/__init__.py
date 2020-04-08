import logging
from concurrent.futures import ThreadPoolExecutor, Future

from pupil_recording_interface.base import BaseConfigurable
from pupil_recording_interface.decorators import process
from pupil_recording_interface.utils import get_constructor_args

logger = logging.getLogger(__name__)


class BaseProcess(BaseConfigurable):
    """ Base class for all processes. """

    def __init__(self, block=True, listen_for=None, **kwargs):
        """ Constructor. """
        self.block = block
        self.listen_for = listen_for or []

        self._executor = ThreadPoolExecutor()

    @classmethod
    def from_config(cls, config, stream_config, device, **kwargs):
        """ Create a process from a ProcessConfig. """
        try:
            return process.registry[config.process_type]._from_config(
                config, stream_config, device, **kwargs
            )
        except KeyError:
            raise ValueError(
                f"No such process type: {config.process_type}. "
                f"If you are implementing a custom process, remember to use "
                f"the @pupil_recording_interface.process class decorator."
            )

    @classmethod
    def _from_config(cls, config, stream_config, device, **kwargs):
        """ Per-class implementation of from_config. """
        cls_kwargs = get_constructor_args(cls, config)

        return cls(**cls_kwargs)

    def start(self):
        """ Start the process"""

    def process(self, packet, notifications):
        """ Process new data. """
        self.process_notifications(notifications)

        return self.process_packet(packet)

    def process_notifications(self, notifications):
        """ Process new notifications. """

    def process_packet(self, packet):
        """ Process a new packet. """
        # TODO Packet class should support Future attributes that each
        #  process resolves if it needs them
        if isinstance(packet, Future):
            # TODO timeout?
            packet = packet.result()

        if self.block:
            return self._process_packet(packet)
        else:
            # TODO this still doesn't help if the processing takes longer
            #  than the packet interval
            return self._executor.submit(self._process_packet, packet)

    def _process_packet(self, packet):
        """ Process a new packet. """
        return packet

    def stop(self):
        """ Stop the process. """
