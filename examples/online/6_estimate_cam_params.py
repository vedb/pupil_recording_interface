"""
Estimate camera parameters
==========================

This examples shows how to estimate the intrinsic parameters of a connected
Pupil Core world camera.

.. note::

    This example requires the dependencies for
    :ref:`streaming<streaming_dependencies>`.

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
# Set folder for saving camera parameter
# --------------------------------------
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
        color_format="gray",
        pipeline=[
            pri.CircleGridDetector.Config(),
            pri.CamParamEstimator.Config(folder=folder, streams=("world",)),
            pri.VideoDisplay.Config(),
        ],
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
            response = input(
                "Press enter to capture a pattern or type 's' to stop: "
            )
            if response == "s":
                break
            else:
                manager.send_notification({"acquire_pattern": True})
                manager.await_status("world", pattern_acquired=True)

print("\nStopped")
