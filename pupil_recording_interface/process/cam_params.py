""""""
from queue import Queue, Full
import logging

import cv2

from pupil_recording_interface.decorators import process
from pupil_recording_interface.process import BaseProcess

logger = logging.getLogger(__name__)


@process("circle_grid_detector")
class CircleGridDetector(BaseProcess):
    """ Detector for circle grids. """

    def __init__(
        self, grid_shape=(4, 11), stereo=False, block=False, **kwargs
    ):
        """ Constructor. """
        self.grid_shape = grid_shape
        self.stereo = stereo

        super().__init__(block=block, **kwargs)

    def detect_grid(self, packet):
        """"""
        frame = packet["frame"]

        if self.stereo:
            status_left, grid_points_left = cv2.findCirclesGrid(
                frame[:, : frame.shape[1] // 2],
                self.grid_shape,
                flags=cv2.CALIB_CB_ASYMMETRIC_GRID,
            )
            status_right, grid_points_right = cv2.findCirclesGrid(
                frame[:, frame.shape[1] // 2 :],
                self.grid_shape,
                flags=cv2.CALIB_CB_ASYMMETRIC_GRID,
            )
            if status_right:
                grid_points_right[:, :, 0] += frame.shape[1] // 2

            status = status_left and status_right
            grid_points = [grid_points_left, grid_points_right]
        else:
            status, grid_points = cv2.findCirclesGrid(
                frame, self.grid_shape, flags=cv2.CALIB_CB_ASYMMETRIC_GRID,
            )

        if status:
            return grid_points
        else:
            return None

    def _process_packet(self, packet, block=None):
        """ Process a new packet. """
        packet.grid_points = self.call(self.detect_grid, packet, block=block)

        # TODO maybe don't broadcast on every single packet
        packet.broadcasts.append("grid_points")

        return packet


@process("cam_param_estimator")
class CamParamEstimator(BaseProcess):
    """"""

    def __init__(self, streams, block=False, num_patterns=10, **kwargs):
        """ Constructor. """
        self.streams = streams
        self.num_patterns = num_patterns

        super().__init__(block=block, listen_for=["grid_points"], **kwargs)

        self._pattern_queue = Queue(maxsize=self.num_patterns)
        self._acquire_pattern = False

    def _add_pattern(self, grid_points):
        """"""
        self._pattern_queue.put(grid_points, False)
        logger.info(
            f"Captured pattern {self._pattern_queue.qsize()} of "
            f"{self.num_patterns}"
        )

    def _estimate_params(self):
        """"""
        logger.debug("Estimating camera parameters")
        patterns = []
        while not self._pattern_queue.empty():
            patterns.append(self._pattern_queue.get())

        # TODO
        import time

        time.sleep(5)

        logger.info("Successfully estimated camera parameters")

    def _process_notifications(self, notifications, block=None):
        """ Process new notifications. """
        for notification in notifications:
            if (
                "acquire_pattern" in notification
                and notification["acquire_pattern"]
            ):
                # TODO with Lock?
                self._acquire_pattern = True
            if self._acquire_pattern and all(
                stream in notification for stream in self.streams
            ):
                try:
                    self._add_pattern(
                        [
                            notification[stream]["grid_points"]
                            for stream in self.streams
                        ]
                    )
                    # TODO with Lock?
                    self._acquire_pattern = False
                except KeyError:
                    pass
                except Full:
                    self._estimate_params()
                    break
