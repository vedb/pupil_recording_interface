from __future__ import print_function

import sys
import logging

from pupil_recording_interface.config import VideoConfig
from pupil_recording_interface import MultiStreamRecorder


if __name__ == "__main__":

    # recording folder
    folder = "~/recordings/test"

    # camera configurations
    configs = [
        VideoConfig(
            "uvc",
            "Pupil Cam1 ID2",
            name="world",
            resolution=(1280, 720),
            fps=60,
        ),
        VideoConfig(
            "uvc",
            "Pupil Cam1 ID0",
            name="eye0",
            resolution=(320, 240),
            fps=120,
            color_format="gray",
        ),
        VideoConfig(
            "uvc",
            "Pupil Cam1 ID1",
            name="eye1",
            resolution=(320, 240),
            fps=120,
            color_format="gray",
        ),
    ]

    # set up logger
    logging.basicConfig(
        stream=sys.stdout, level=logging.INFO, format="%(message)s"
    )

    # start recorder
    recorder = MultiStreamRecorder(folder, configs, show_video=True)
    for fps_dict in recorder.run():
        fps_str = recorder.format_fps(fps_dict)
        if fps_str is not None:
            print("\rSampling rates: " + fps_str, end="")
