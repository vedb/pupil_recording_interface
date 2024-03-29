import logging
from concurrent.futures import Future

from pupil_recording_interface.base import BaseConfigurable
from pupil_recording_interface.decorators import process
from pupil_recording_interface.utils import DroppingThreadPoolExecutor

logger = logging.getLogger(__name__)


class BaseProcess(BaseConfigurable):
    """ Base class for all processes. """

    def __init__(
        self,
        process_name=None,
        paused=False,
        block=True,
        listen_for=None,
        context=None,
    ):
        """ Constructor. """
        self.process_name = process_name or type(self).__name__
        self.paused = paused
        self.block = block
        self.listen_for = listen_for or []
        self.context = context

        self._packet_executor = DroppingThreadPoolExecutor(maxsize=10)
        self._notification_executor = DroppingThreadPoolExecutor(maxsize=10)

        logger.debug(f"Initialized process {self.process_name}")

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
        cls_kwargs = cls.get_constructor_args(config)
        # TODO this has to be duplicated if the sub-class overrides from_config
        if stream_config.name is not None:
            cls_kwargs["process_name"] = ".".join(
                (
                    stream_config.name,
                    cls_kwargs["process_name"] or cls.__name__,
                )
            )

        return cls(**cls_kwargs)

    def start(self):
        """ Start the process"""

    def process(self, packet, notifications):
        """ Process new data. """
        if len(notifications) > 0:
            self.process_notifications(notifications)

        return self.process_packet(packet)

    def call(self, fn, *args, block=None, return_if_full=None, **kwargs):
        """ Call a function, either blocking or non-blocking. """
        if block is None:
            block = self.block

        if block:
            return fn(*args, **kwargs)
        else:
            return self._packet_executor.submit(
                fn, *args, return_if_full=return_if_full, **kwargs
            )

    def process_notifications(self, notifications):
        """ Process new notifications. """
        for notification in notifications:
            if (
                "pause_process" in notification
                and notification["pause_process"] == self.process_name
            ):
                logger.debug(f"Pausing process {self.process_name}")
                self.paused = True
            if (
                "resume_process" in notification
                and notification["resume_process"] == self.process_name
            ):
                logger.debug(f"Resuming process {self.process_name}")
                self.paused = False

        if not self.paused:
            if self.block:
                return self._process_notifications(notifications, block=True)
            else:
                return self._notification_executor.submit(
                    self._process_notifications, notifications, block=True
                )

    def _process_notifications(self, notifications, block=None):
        """ Process new notifications. """

    def process_packet(self, packet):
        """ Process a new packet. """
        if self.paused:
            return packet

        # TODO use per-attribute future mechanism of Packet
        if isinstance(packet, Future):
            packet = packet.result()

        if self.block:
            return self._process_packet(packet, block=True)
        else:
            return self._packet_executor.submit(
                self._process_packet, packet, block=True
            )

    def _process_packet(self, packet, block=None):
        """ Process a new packet. """
        return packet

    def stop(self):
        """ Stop the process. """
