""""""
import logging

from pupil_recording_interface.process import (
    VideoDisplay,
    VideoRecorder,
    OdometryRecorder,
)
from pupil_recording_interface.config import (
    VideoDisplayConfig,
    VideoRecorderConfig,
    OdometryRecorderConfig,
)

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
            for step in config.pipeline:
                # TODO BaseProcess.from_config(step, config, device, folder)
                if isinstance(step, VideoDisplayConfig):
                    steps.append(VideoDisplay(config.name or device.uid))
                elif isinstance(step, VideoRecorderConfig):
                    steps.append(
                        VideoRecorder(
                            step.folder or folder,
                            step.resolution or device.resolution,
                            step.fps or device.fps,
                            name=config.name or device.uid,
                            color_format=step.color_format
                            or config.color_format,
                            codec=step.codec,
                        )
                    )
                elif isinstance(step, OdometryRecorderConfig):
                    steps.append(OdometryRecorder(step.folder or folder))
                else:
                    raise ValueError(f"Unsupported process type: {type(step)}")
            return cls(steps)
        else:
            return None

    def start(self):
        """ Start the pipeline. """
        logger.debug(f"Starting pipeline with steps: {self.steps}")
        for step in self.steps:
            step.start()

    def flush(self, data, timestamp):
        """ Flush the pipeline with new data. """
        for step in self.steps:
            data, timestamp = step.process_data_and_timestamp(data, timestamp)

        return data, timestamp

    def stop(self):
        """ Stop the pipeline. """
        for step in self.steps:
            step.stop()
