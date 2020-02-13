import sys

sys.path.append("/home/veddy/Code/pupil_recording_interface/")

from pupil_recording_interface.config import VideoConfig
from pupil_recording_interface import MultiStreamRecorder

if __name__ == "__main__":

    # recording folder
    folder = "~/recordings/test"

    # camera configurations
    configs = [
        VideoConfig(
            "flir", "<FLIR_S/N>", name="world", resolution=(2048, 1536), fps=60
        ),
        VideoConfig(
            "uvc",
            "Pupil Cam2 ID0",
            name="eye0",
            resolution=(400, 400),
            fps=120,
            color_format="gray",
        ),
        VideoConfig(
            "uvc",
            "Pupil Cam2 ID1",
            name="eye1",
            resolution=(400, 400),
            fps=120,
            color_format="gray",
        ),
    ]

    # start recorder
    recorder = MultiStreamRecorder(folder, configs, show_video=True)
    recorder.run()
