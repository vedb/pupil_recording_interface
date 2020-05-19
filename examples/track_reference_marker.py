import sys
import logging

import pupil_recording_interface as pri


if __name__ == "__main__":

    # stream configurations
    configs = [
        pri.VideoStream.Config(
            device_type="flir",
            device_uid=None,
            name="world",
            resolution=(1280, 1024),
            fps=30,
            settings={
                "GainAuto": "Off",
                "Gain": 15.0,
                "ExposureAuto": "Off",
                "ExposureTime": 16000.0,
            },
            color_format="bayer_rggb8",
            pipeline=[
                pri.CircleDetector.Config(scale=0.4),
                pri.VideoDisplay.Config(overlay_circle_marker=True),
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
                    "fps", format="{:.2f} Hz", max_cols=72, sleep=0.1
                )
                print("\r" + status, end="")

    print("\nStopped")
