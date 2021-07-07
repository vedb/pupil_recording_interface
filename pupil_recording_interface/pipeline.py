""""""
import logging

from pupil_recording_interface.process import BaseProcess

logger = logging.getLogger(__name__)


class Pipeline:
    """ Pipeline for different processing steps. """

    def __init__(self, steps, context=None):
        """ Constructor.

        Parameters
        ----------
        steps : iterable of BaseProcess
            Processing steps for this pipeline.

        context : BaseStream, optional
            The stream this pipeline is attached to, if applicable.
        """
        self.steps = list(steps)
        self.set_context(context)

    @property
    def listen_for(self):
        return [
            notification_type
            for step in self.steps
            for notification_type in step.listen_for
        ]

    @classmethod
    def from_config(cls, config, device, folder=None):
        """ Create an instance from a StreamConfig. """
        if config.pipeline is not None:
            steps = []
            for process_config in config.pipeline:
                steps.append(
                    BaseProcess.from_config(
                        process_config, config, device, folder=folder
                    )
                )
            return cls(steps)
        else:
            return None

    def set_context(self, context):
        """ Set the stream this pipeline is attached to. """
        self.context = context
        for step in self.steps:
            step.context = self.context

    def start(self):
        """ Start the pipeline. """
        logger.debug(f"Starting pipeline with steps: {self.steps}")
        for step in self.steps:
            step.start()

    def stop(self):
        """ Stop the pipeline. """
        for step in self.steps:
            step.stop()

    def __enter__(self):
        self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def process(self, packet, notifications=None):
        """ Process new data. """
        for step in self.steps:
            packet = step.process(packet, notifications or [])

        return packet
