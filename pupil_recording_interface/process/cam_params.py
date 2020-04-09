""""""
import logging

import cv2

from pupil_recording_interface.decorators import process
from pupil_recording_interface.process import BaseProcess

logger = logging.getLogger(__name__)


@process("circle_grid_detector")
class CircleGridDetector(BaseProcess):
    """ Detector for circle grids. """

    def __init__(self, grid_shape=(4, 11), block=False, **kwargs):
        """ Constructor. """
        self.grid_shape = grid_shape

        super().__init__(block=block, **kwargs)

    def detect_grid(self, packet):
        """"""
        frame = packet["frame"]

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

        return packet
