import sys
import logging

from pupil_recording_interface.config import (
    VideoConfig,
    OdometryConfig,
    VideoDisplayConfig,
    VideoRecorderConfig,
)
from pupil_recording_interface.stream import StreamManager

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
            pipeline=[VideoDisplayConfig(), VideoRecorderConfig()],
        ),
        VideoConfig(
            "uvc",
            "Pupil Cam1 ID0",
            name="eye0",
            resolution=(320, 240),
            fps=120,
            color_format="gray",
            pipeline=[VideoDisplayConfig(), VideoRecorderConfig()],
        ),
        VideoConfig(
            "uvc",
            "Pupil Cam1 ID1",
            name="eye1",
            resolution=(320, 240),
            fps=120,
            color_format="gray",
            pipeline=[VideoDisplayConfig(), VideoRecorderConfig()],
        ),
        VideoConfig(
            "t265",
            "t265",
            resolution=(1696, 800),
            fps=30,
            color_format="gray",
            pipeline=[VideoDisplayConfig(), VideoRecorderConfig()],
        ),
        OdometryConfig("t265", "t265", name="odometry"),
    ]

    # set up logger
    logging.basicConfig(
        stream=sys.stdout, level=logging.DEBUG, format="%(message)s"
    )

    # start stream
    manager = StreamManager(configs, folder, policy="overwrite")
    for status_dict in manager.run():
        status = manager.format_status(status_dict)
        if status is not None:
            print("\r" + status, end="")
