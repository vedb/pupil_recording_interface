""""""
import cv2

from pupil_recording_interface.decorators import process
from pupil_recording_interface.process import BaseProcess


@process("circle_grid_detector")
class CircleGridDetector(BaseProcess):
    """ Detector for circle grids. """

    def __init__(self, grid_shape=(4, 11), block=False, **kwargs):
        """ Constructor. """
        self.grid_shape = grid_shape

        super().__init__(block=block, **kwargs)

    def _process_packet(self, packet):
        """ Process a new packet. """
        status, grid_points = cv2.findCirclesGrid(
            packet.frame, self.grid_shape, flags=cv2.CALIB_CB_ASYMMETRIC_GRID,
        )

        if status:
            packet.grid_points = grid_points

        return packet
