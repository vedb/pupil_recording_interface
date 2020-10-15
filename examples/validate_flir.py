import sys
import logging
import datetime

import pupil_recording_interface as pri

logger = logging.getLogger(__name__)
# Generation of your pupil device (1, 2 or 3)
pupil_gen = 2

# recording folder
folder = f"~/recordings/{datetime.datetime.today():%Y_%m_%d_%H_%M_%S}"

if __name__ == "__main__":

    # stream configurations
    configs = [
        pri.VideoStream.Config(
            device_type="flir",
            # Todo: Read from config
            device_uid="19208347",
            name="world",
            resolution=(2048, 1536),
            fps=30,
            pipeline=[
                pri.CircleDetector.Config(
                    scale=0.5,
                    paused=True,
                    detection_method="vedb",
                    marker_size=(5, 300),
                    threshold_window_size=13,
                    min_area=200,
                    max_area=4000,
                    circularity=0.8,
                    convexity=0.7,
                    inertia=0.4,
                ),
                pri.Validation.Config(save=True, folder=folder),
                pri.VideoDisplay.Config(
                    overlay_circle_marker=True, overlay_gaze=True
                ),
            ],
        ),
        pri.VideoStream.Config(
            device_type="uvc",
            device_uid=f"Pupil Cam{pupil_gen} ID0",
            name="eye0",
            resolution=(320, 240) if pupil_gen == 1 else (192, 192),
            fps=120,
            color_format="gray",
            pipeline=[
                pri.PupilDetector.Config(),
                pri.VideoDisplay.Config(flip=True, overlay_pupil=True),
            ],
        ),
        pri.VideoStream.Config(
            device_type="uvc",
            device_uid=f"Pupil Cam{pupil_gen} ID1",
            name="eye1",
            resolution=(320, 240) if pupil_gen == 1 else (192, 192),
            fps=120,
            color_format="gray",
            pipeline=[
                pri.PupilDetector.Config(),
                pri.VideoDisplay.Config(flip=True, overlay_pupil=True),
            ],
        ),
    ]

    # set up logger
    logging.basicConfig(
        stream=sys.stdout, level=logging.INFO, format="%(message)s"
    )

    validation_counter = 0
    # run manager
    with pri.StreamManager(configs) as manager:
        while not manager.stopped:
            if manager.all_streams_running:
                print("Data Validation Started! ...")
                # Collect data

                response = input(
                    "Press enter to start validation or type 'a' to abort: "
                )
                if response == "a":
                    break
                else:
                    while validation_counter < 5:
                        logger.info(
                            f"\nCollecting calibration data "
                            f"{validation_counter}..."
                        )
                        manager.send_notification(
                            {"resume_process": "world.CircleDetector"},
                            streams=["world"],
                        )
                        manager.send_notification(
                            {"collect_calibration_data": True},
                            streams=["world"],
                        )
                        manager.await_status("world", collected_markers=None)

                        # Calculate calibration
                        response = input(
                            "Press enter to proceed or type 'a' to abort: "
                        )
                        if response == "a":
                            break
                        else:
                            manager.send_notification(
                                {"pause_process": "world.CircleDetector"},
                                streams=["world"],
                            )
                        validation_counter += 1

                    manager.send_notification({"calculate_calibration": True})
                    manager.await_status("world", calibration_calculated=True)
                    break

    print("\nStopped")
