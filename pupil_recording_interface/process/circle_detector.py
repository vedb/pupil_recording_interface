""""""
import cv2

from pupil_recording_interface.decorators import process
from pupil_recording_interface.process import BaseProcess
from pupil_recording_interface.externals.circle_detector import CircleTracker


@process("circle_detector")
class CircleDetector(BaseProcess):
    """ Circle detector for the world video stream. """

    def __init__(self, **kwargs):
        """ Constructor. """
        super().__init__(**kwargs)

        self.circle_tracker = CircleTracker()

    def detect_circle(self, packet):
        """"""
        frame = packet["frame"]

        if frame.ndim == 3:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        circle_markers = self.circle_tracker.update(frame)

        for marker in circle_markers:
            marker["timestamp"] = packet.timestamp

        return circle_markers

    def _process_packet(self, packet, block=None):
        """ Process a new packet. """
        packet.circle_markers = self.call(
            self.detect_circle, packet, block=block
        )

        packet.broadcasts.append("circle_markers")

        return packet
