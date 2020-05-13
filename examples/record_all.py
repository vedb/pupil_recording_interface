import sys
import logging

import pupil_recording_interface as pri


if __name__ == "__main__":

    # recording folder
    folder = "~/recordings/test"

    # camera configurations
    configs = [
        pri.VideoStream.Config(
            device_type="uvc",
            device_uid="Pupil Cam1 ID2",
            name="world",
            resolution=(1280, 720),
            fps=60,
            pipeline=[pri.VideoRecorder.Config(), pri.VideoDisplay.Config()],
        ),
        pri.VideoStream.Config(
            device_type="uvc",
            device_uid="Pupil Cam1 ID0",
            name="eye0",
            resolution=(320, 240),
            fps=120,
            color_format="gray",
            pipeline=[
                pri.VideoRecorder.Config(),
                pri.VideoDisplay.Config(flip=True),
            ],
        ),
        pri.VideoStream.Config(
            device_type="uvc",
            device_uid="Pupil Cam1 ID1",
            name="eye1",
            resolution=(320, 240),
            fps=120,
            color_format="gray",
            pipeline=[pri.VideoRecorder.Config(), pri.VideoDisplay.Config()],
        ),
        pri.VideoStream.Config(
            device_type="t265",
            device_uid="t265",
            resolution=(1696, 800),
            fps=30,
            color_format="gray",
            pipeline=[pri.VideoRecorder.Config(), pri.VideoDisplay.Config()],
        ),
        pri.MotionStream.Config(
            device_type="t265",
            device_uid="t265",
            motion_type="odometry",
            pipeline=[pri.MotionRecorder.Config()],
        ),
        pri.MotionStream.Config(
            device_type="t265",
            device_uid="t265",
            motion_type="accel",
            pipeline=[pri.MotionRecorder.Config()],
        ),
        pri.MotionStream.Config(
            device_type="t265",
            device_uid="t265",
            motion_type="gyro",
            pipeline=[pri.MotionRecorder.Config()],
        ),
    ]

    # set up logger
    logging.basicConfig(
        stream=sys.stdout, level=logging.DEBUG, format="%(message)s"
    )

    # run manager
    with pri.StreamManager(configs, folder, policy="overwrite") as manager:
        while not manager.stopped:
            if manager.all_streams_running:
                status = manager.format_status(
                    "fps", format="{:.2f} Hz", max_cols=72, sleep=0.1
                )
                print("\r" + status, end="")

    print("\nStopped")
