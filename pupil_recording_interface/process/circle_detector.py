""""""
import cv2

from pupil_recording_interface.decorators import process
from pupil_recording_interface.process import BaseProcess
from pupil_recording_interface.externals.circle_detector import CircleTracker


@process("circle_detector")
class CircleDetector(BaseProcess):
    """ Circle detector for the world video stream. """

    def __init__(self, scale=0.5, **kwargs):
        """ Constructor. """
        super().__init__(**kwargs)

        # Todo: Pass the detection method from config file
        self.circle_tracker = CircleTracker(
            scale=scale, detection_method="VEDB"
        )
        self.scale = scale

    def detect_circle(self, packet):
        """ Detect circle markers. """
        frame = packet["frame"]

        if packet.color_format == "bgr24":
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        elif packet.color_format == "bggr8":
            frame = cv2.cvtColor(frame, cv2.COLOR_BAYER_BG2GRAY)

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
