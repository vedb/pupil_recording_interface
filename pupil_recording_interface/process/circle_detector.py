""""""
from pupil_recording_interface.decorators import process
from pupil_recording_interface.process import BaseProcess
from pupil_recording_interface.externals.circle_detector import CircleTracker


@process("circle_detector")
class CircleDetector(BaseProcess):
    """ Circle detector for the world video stream. """

    def __init__(self, block=False, **kwargs):
        """ Constructor. """
        super().__init__(block=block, **kwargs)

        self.circle_tracker = CircleTracker()

    def detect_circle(self, packet):
        """"""
        return self.circle_tracker.update(packet["frame"])

    def _process_packet(self, packet, block=None):
        """ Process a new packet. """
        packet.circle_markers = self.call(
            self.detect_circle, packet, block=block
        )

        packet.broadcasts.append("circle_markers")

        return packet
