""""""
import logging

from pupil_recording_interface.process import BaseProcess

logger = logging.getLogger(__name__)


class Pipeline(object):
    """ Pipeline for different processing steps. """

    def __init__(self, steps):
        """ Constructor. """
        self.steps = steps

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

    def start(self):
        """ Start the pipeline. """
        logger.debug(f"Starting pipeline with steps: {self.steps}")
        for step in self.steps:
            step.start()

    def flush(self, packet):
        """ Flush the pipeline with new data. """
        for step in self.steps:
            packet = step.process_packet(packet)

        return packet

    def stop(self):
        """ Stop the pipeline. """
        for step in self.steps:
            step.stop()
