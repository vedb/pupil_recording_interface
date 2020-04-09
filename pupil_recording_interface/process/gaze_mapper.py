""""""
from queue import Queue

from pupil_recording_interface.decorators import process
from pupil_recording_interface.process import BaseProcess


@process("gaze_mapper")
class GazeMapper(BaseProcess):
    """ Gaze mapper. """

    def __init__(self, block=False, left="eye0", right="eye1", **kwargs):
        """ Constructor. """
        self.left = left
        self.right = right

        super().__init__(block=block, listen_for=["pupil"], **kwargs)

        self._gaze_queue = Queue()

    def map_gaze(self, left_pupil, right_pupil):
        """ Map gaze. """
        # TODO implement this
        return left_pupil["location"]

    def _process_notifications(self, notifications, block=None):
        """ Process new notifications. """
        for notification in notifications:
            try:
                self._gaze_queue.put(
                    self.map_gaze(
                        notification[self.left]["pupil"],
                        notification[self.right]["pupil"],
                    )
                )
            except KeyError:
                pass

    def _process_packet(self, packet, block=None):
        """ Process new data. """
        packet.gaze_points = []

        while not self._gaze_queue.empty():
            packet.gaze_points.append(self._gaze_queue.get())

        packet.broadcasts.append("gaze_points")

        return packet
