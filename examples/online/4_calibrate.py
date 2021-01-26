"""
Calibrate gaze mapping
======================

This examples shows how to calibrate the gaze mapper with a connected Pupil
Core headset.


.. note::

    This example requires the dependencies for
    :ref:`streaming<streaming_dependencies>` and
    :ref:`pupil detection<pupil_detection_dependencies>`.

"""
import sys
import logging

import pupil_recording_interface as pri


# %%
# Set Pupil Core generation
# -------------------------
#
# Set the generation of your Pupil Core device (1, 2 or 3)
pupil_gen = 1

# %%
# Set folder for saving calibration
# ---------------------------------
folder = "~/pupil_capture_settings"

# %%
# Set up stream configurations
# ----------------------------
configs = [
    pri.VideoStream.Config(
        device_type="uvc",
        device_uid=f"Pupil Cam{pupil_gen} ID2",
        name="world",
        resolution=(1280, 720),
        fps=30,
        pipeline=[
            pri.CircleDetector.Config(paused=True),
            pri.Calibration.Config(save=True, folder=folder),
            pri.GazeMapper.Config(),
            pri.VideoDisplay.Config(),
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
            pri.VideoDisplay.Config(flip=True),
        ],
    ),
    pri.VideoStream.Config(
        device_type="uvc",
        device_uid=f"Pupil Cam{pupil_gen} ID1",
        name="eye1",
        resolution=(320, 240) if pupil_gen == 1 else (192, 192),
        fps=120,
        color_format="gray",
        pipeline=[pri.PupilDetector.Config(), pri.VideoDisplay.Config()],
    ),
]

# %%
# Set up logger
# -------------
logging.basicConfig(
    stream=sys.stdout, level=logging.INFO, format="%(message)s"
)

# %%
# Run manager
# -----------
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
