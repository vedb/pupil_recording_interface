from pupil_recording_interface.decorators import process
from pupil_recording_interface.process import BaseProcess


@process("pupil_detector")
class PupilDetector(BaseProcess):
    """ Pupil detector for eye video streams. """

    def __init__(self, block=True, **kwargs):
        """ Constructor. """
        from pupil_detectors import Detector2D

        self.detector = Detector2D()

        super().__init__(block=block, **kwargs)

    def _process_packet(self, packet):
        """ Process a new packet. """
        packet.pupil = self.detector.detect(packet.frame)
        packet.broadcasts.append("pupil")
        return packet
