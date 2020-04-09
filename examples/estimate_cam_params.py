import sys
import logging

import pupil_recording_interface as pri


if __name__ == "__main__":

    # stream configurations
    configs = [
        pri.VideoStream.Config(
            device_type="uvc",
            device_uid="Pupil Cam1 ID2",
            name="world",
            resolution=(1280, 720),
            fps=30,
            pipeline=[
                pri.CircleGridDetector.Config(),
                pri.VideoDisplay.Config(overlay_circle_grid=True),
            ],
        ),
        pri.VideoStream.Config(
            device_type="t265",
            device_uid="t265",
            resolution=(1696, 800),
            fps=30,
            color_format="gray",
            pipeline=[
                pri.CircleGridDetector.Config(),
                pri.VideoDisplay.Config(overlay_circle_grid=True),
            ],
        ),
    ]

    # set up logger
    logging.basicConfig(
        stream=sys.stdout, level=logging.DEBUG, format="%(message)s"
    )

    # start stream
    manager = pri.StreamManager(configs)

    for status in manager.run():
        status_str = manager.format_status(status, value="fps", max_cols=72)
        if status_str is not None:
            print("\r" + status_str, end="")

    print("\nStopped")
