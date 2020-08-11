""""""
import logging

from pupil_recording_interface.decorators import process
from pupil_recording_interface.process.calibration import Calibration

logger = logging.getLogger(__name__)


@process("validation", optional=("resolution",))
class Validation(Calibration):
    """ Validation during runtime class. """

    def plot_markers(self, circle_marker_list):
        import matplotlib.pyplot as plt

        x = [c["img_pos"][0] for c in circle_marker_list]
        y = [c["img_pos"][1] for c in circle_marker_list]
        plt.plot(x, y, "ob", markersize=4, alpha=0.4)
        plt.xlim(0, self.resolution[0])
        plt.ylim(0, self.resolution[1])
        plt.grid(True)
        plt.title("Marker Position", fontsize=18)
        plt.rc("xtick", labelsize=12)
        plt.rc("ytick", labelsize=12)
        plt.xlabel("X (pixels)", fontsize=14)
        plt.ylabel("Y (pixels)", fontsize=14)
        # TODO: Save to recording folder
        plt.savefig("covered_marker.png", dpi=200)
        plt.show()

        return True

    def plot_pupils(self, pupil_list):
        import matplotlib.pyplot as plt

        # TODO: get eye video resolution from the config
        resolution = 192.0
        x = [p["norm_pos"][0] * resolution for p in pupil_list if p["id"] == 0]
        y = [p["norm_pos"][1] * resolution for p in pupil_list if p["id"] == 0]
        plt.plot(x, y, "*y", markersize=6, alpha=0.4)

        x = [p["norm_pos"][0] * resolution for p in pupil_list if p["id"] == 1]
        y = [p["norm_pos"][1] * resolution for p in pupil_list if p["id"] == 1]
        plt.plot(x, y, "*g", markersize=6, alpha=0.4)
        # TODO: get the resolution
        plt.xlim(0, resolution)
        plt.ylim(0, resolution)
        plt.grid(True)
        plt.title("Pupil Position", fontsize=18)
        plt.rc("xtick", labelsize=12)
        plt.rc("ytick", labelsize=12)
        plt.xlabel("X (pixels)", fontsize=14)
        plt.ylabel("Y (pixels)", fontsize=14)
        # TODO: Save to recording folder
        plt.savefig("covered_pupil.png", dpi=200)
        plt.show()

        return True

    # Todo: This is just for demo purposes
    def clear_flag_dummy(self, packet):
        packet.calibration_calculated = True
        packet.broadcasts.append("calibration_calculated")

    def calculate_calibration(self):
        """ Calculate calibration from collected data. """
        circle_marker_list, pupil_list = super().calculate_calibration()

        self.plot_markers(circle_marker_list)
        self.plot_pupils(pupil_list)
        logger
