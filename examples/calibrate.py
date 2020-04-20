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
                pri.CircleDetector.Config(paused=True),
                pri.Calibration.Config(save=True, folder="~/recordings"),
                pri.GazeMapper.Config(),
                pri.VideoDisplay.Config(
                    overlay_circle_marker=True, overlay_gaze=True
                ),
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
                pri.VideoDisplay.Config(flip=True, overlay_pupil=True),
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
                # Collect data
                response = input(
                    "Press enter to start calibration or type 'a' to abort: "
                )
                if response == "a":
                    break
                else:
                    print("Collecting calibration data...")
                    manager.send_notification(
                        {"resume_process": "world.CircleDetector"},
                        streams=["world"],
                    )
                    manager.send_notification(
                        {"collect_calibration_data": True}, streams=["world"],
                    )
                    manager.await_status("world", collected_markers=None)

                # Calculate calibration
                response = input(
                    "Press enter to stop calibration or type 'a' to abort: "
                )
                if response == "a":
                    break
                else:
                    manager.send_notification(
                        {"pause_process": "world.CircleDetector"},
                        streams=["world"],
                    )
                    manager.send_notification({"calculate_calibration": True})
                    manager.await_status("world", calibration_calculated=True)

    print("\nStopped")
