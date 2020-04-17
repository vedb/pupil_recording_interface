import sys
import logging

import pupil_recording_interface as pri


if __name__ == "__main__":

    # recording folder
    folder = pri.DATA_DIR + "/test_recording"

    # stream configurations
    configs = [
        pri.VideoStream.Config(
            device_type="video_file",
            device_uid="world",
            resolution=(1280, 720),
            pipeline=[
                pri.GazeMapper.Config(),
                pri.VideoDisplay.Config(overlay_gaze=True),
            ],
        ),
        pri.VideoStream.Config(
            device_type="video_file",
            device_uid="eye0",
            resolution=(192, 192),
            pipeline=[
                pri.PupilDetector.Config(),
                pri.VideoDisplay.Config(overlay_pupil=True),
            ],
        ),
        pri.VideoStream.Config(
            device_type="video_file",
            device_uid="eye1",
            resolution=(192, 192),
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
    with pri.StreamManager(configs, folder=folder, policy="read") as manager:
        while not manager.stopped:
            if manager.all_streams_running:
                status = manager.format_status("fps", max_cols=72)
                print("\r" + status, end="")

    print("\nStopped")
