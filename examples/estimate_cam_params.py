import sys
import logging

import pupil_recording_interface as pri


if __name__ == "__main__":

    # folder for saving parameters
    folder = "~/recordings"

    # stream configurations
    configs = [
        pri.VideoStream.Config(
            device_type="uvc",
            device_uid="Pupil Cam1 ID2",
            name="world",
            resolution=(1280, 720),
            fps=30,
            color_format="gray",
            pipeline=[
                pri.CircleGridDetector.Config(),
                pri.CamParamEstimator.Config(
                    folder=folder, streams=("world", "t265"), extrinsics=True,
                ),
                pri.VideoDisplay.Config(overlay_circle_grid=True),
            ],
        ),
        pri.VideoStream.Config(
            device_type="t265",
            device_uid="t265",
            name="t265",
            resolution=(1696, 800),
            fps=30,
            color_format="gray",
            pipeline=[
                pri.CircleGridDetector.Config(stereo=True),
                pri.VideoDisplay.Config(overlay_circle_grid=True),
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
                response = input(
                    "Press enter to capture a pattern or type 's' to stop: "
                )
                if response == "s":
                    break
                else:
                    manager.send_notification({"acquire_pattern": True})
                    manager.await_status("world", pattern_acquired=True)

    print("\nStopped")
