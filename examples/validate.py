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
                pri.CircleDetector.Config(scale=0.8, paused=True),
                pri.VideoDisplay.Config(
                    overlay_circle_marker=True, overlay_gaze=True
                ),
                pri.Validation.Config(save=True, folder="~/recordings"),
                # pri.GazeMapper.Config(),
            ],
        ),
    ]

    # set up logger
    logging.basicConfig(
        stream=sys.stdout, level=logging.DEBUG, format="%(message)s"
    )

    validation_counter = 0
    # run manager
    with pri.StreamManager(configs) as manager:
        print("MS: ", manager.stopped)
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
                    while validation_counter < 10:
                        print(
                            "\nCollecting calibration data{:d}...".format(
                                validation_counter
                            )
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

    print("\nStopped")
