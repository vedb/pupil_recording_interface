""""""
import logging

from pupil_recording_interface.decorators import process
from pupil_recording_interface.process.calibration import Calibration

logger = logging.getLogger(__name__)


@process("validation", optional=("resolution",))
class Validation(Calibration):
    """ Validation during runtime class. """

    def __init__(
        self,
        resolution,
        eye_resolution=None,
        mode="2d",
        min_confidence=0.8,
        left="eye1",
        right="eye0",
        world="world",
        name=None,
        folder=None,
        save=False,
        **kwargs,
    ):
        """ Constructor. """
        super().__init__(
            resolution,
            mode=mode,
            min_confidence=min_confidence,
            left=left,
            right=right,
            world=world,
            name=name,
            folder=folder,
            save=save,
            **kwargs,
        )
        self.eye_resolution = eye_resolution

    def plot_markers(self, circle_marker_list):
        """ Plot marker coverage. """
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
        plt.show()

        return plt.gcf()

    def plot_pupils(self, pupil_list):
        """ Plot pupil coverage. """
        import matplotlib.pyplot as plt

        res = self.eye_resolution or (1.0, 1.0)
        x = [p["norm_pos"][0] * res[0] for p in pupil_list if p["id"] == 0]
        y = [p["norm_pos"][1] * res[1] for p in pupil_list if p["id"] == 0]
        plt.plot(x, y, "*y", markersize=6, alpha=0.4, label="right")

        x = [p["norm_pos"][0] * res[0] for p in pupil_list if p["id"] == 1]
        y = [p["norm_pos"][1] * res[1] for p in pupil_list if p["id"] == 1]
        plt.plot(x, y, "*g", markersize=6, alpha=0.4, label="left")

        plt.xlim(0, res[0])
        plt.ylim(0, res[1])
        plt.grid(True)
        plt.title("Pupil Position", fontsize=18)
        plt.rc("xtick", labelsize=12)
        plt.rc("ytick", labelsize=12)
        if self.eye_resolution is not None:
            plt.xlabel("X (pixels)", fontsize=14)
            plt.ylabel("Y (pixels)", fontsize=14)
        else:
            plt.xlabel("X (normalized position)", fontsize=14)
            plt.ylabel("Y (normalized position)", fontsize=14)
        plt.show()

        return plt.gcf()

    def calculate_calibration(self):
        """ Calculate calibration from collected data. """
        (
            circle_marker_list,
            pupil_list,
            filename,
        ) = super().calculate_calibration()

        marker_fig = self.plot_markers(circle_marker_list)
        pupil_fig = self.plot_pupils(pupil_list)

        if filename is not None:
            marker_fig.savefig(
                filename.parent / (filename.name + "_marker_coverage.png"),
                dpi=200,
            )
            pupil_fig.savefig(
                filename.parent / (filename.name + "_pupil_coverage.png"),
                dpi=200,
            )

        return circle_marker_list, pupil_list, filename
