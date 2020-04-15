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
            fps=60,
            color_format="gray",
            pipeline=[
                pri.CircleDetector.Config(),
                pri.VideoDisplay.Config(overlay_circle_marker=True),
            ],
        ),
        pri.VideoStream.Config(
            device_type="uvc",
            device_uid="Pupil Cam1 ID0",
            name="eye0",
            resolution=(320, 240),
            fps=120,
            color_format="gray",
            pipeline=[
                pri.PupilDetector.Config(),
                pri.VideoDisplay.Config(overlay_pupil=True),
            ],
        ),
        pri.VideoStream.Config(
            device_type="uvc",
            device_uid="Pupil Cam1 ID1",
            name="eye1",
            resolution=(320, 240),
            fps=120,
            color_format="gray",
            pipeline=[
                pri.PupilDetector.Config(),
                pri.VideoDisplay.Config(overlay_pupil=True),
            ],
        ),
    ]

    # set up logger
    logging.basicConfig(
        stream=sys.stdout, level=logging.DEBUG, format="%(message)s"
    )

    # run manager
    with pri.StreamManager(configs) as manager:
        while not manager.stopped:
            if manager.all_streams_running:
                status = manager.format_status(
                    "fps", format="{:.2f} Hz", max_cols=72
                )
                print("\r" + status, end="")

    print("\nStopped")
