from pupil_recording_interface.decorators import process
from pupil_recording_interface.process import BaseProcess


@process("gaze_mapper")
class GazeMapper(BaseProcess):
    """ Gaze mapper. """

    def __init__(self, left="eye0", right="eye1", **kwargs):
        """ Constructor. """
        super().__init__(listen_for=["pupil"], **kwargs)
        self.left = left
        self.right = right

    def map_gaze(self, left_pupil, right_pupil):
        """ Map gaze. """
        # TODO implement this
        return left_pupil["location"]

    def process(self, packet, notifications):
        """ Process new data. """
        packet.gaze_points = []
        for notification in notifications:
            try:
                packet.gaze_points.append(
                    self.map_gaze(
                        notification[self.left]["pupil"],
                        notification[self.right]["pupil"],
                    )
                )
            except KeyError:
                pass

        return packet
