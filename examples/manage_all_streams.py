from __future__ import print_function

import sys
import logging

from pupil_recording_interface import (
    VideoConfig,
    OdometryConfig,
    VideoDisplayConfig,
    VideoRecorderConfig,
    OdometryRecorderConfig,
    PupilDetectorConfig,
    StreamManager,
)


if __name__ == "__main__":

    # recording folder
    folder = "~/recordings/test"

    # camera configurations
    configs = [
        VideoConfig(
            device_type="uvc",
            device_uid="Pupil Cam1 ID2",
            name="world",
            resolution=(1280, 720),
            fps=60,
            pipeline=[VideoDisplayConfig(), VideoRecorderConfig()],
        ),
        VideoConfig(
            device_type="uvc",
            device_uid="Pupil Cam1 ID0",
            name="eye0",
            resolution=(320, 240),
            fps=120,
            color_format="gray",
            pipeline=[
                VideoRecorderConfig(),
                PupilDetectorConfig(overlay=True),
                VideoDisplayConfig(),
            ],
        ),
        VideoConfig(
            device_type="uvc",
            device_uid="Pupil Cam1 ID1",
            name="eye1",
            resolution=(320, 240),
            fps=120,
            color_format="gray",
            pipeline=[
                VideoRecorderConfig(),
                PupilDetectorConfig(overlay=True),
                VideoDisplayConfig(),
            ],
        ),
        VideoConfig(
            device_type="t265",
            device_uid="t265",
            resolution=(1696, 800),
            fps=30,
            color_format="gray",
            pipeline=[VideoDisplayConfig(), VideoRecorderConfig()],
        ),
        OdometryConfig(
            device_type="t265",
            device_uid="t265",
            name="odometry",
            pipeline=[OdometryRecorderConfig()],
        ),
    ]

    # set up logger
    logging.basicConfig(
        stream=sys.stdout, level=logging.INFO, format="%(message)s"
    )

    # start stream
    manager = StreamManager(configs, folder, policy="overwrite")
    for status_dict in manager.run():
        status = manager.format_status(status_dict)
        if status is not None:
            print("\r" + status, end="")

    print("\nStopped")
