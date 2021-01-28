"""
.. _stream_recording_example:

Stream from a recording
=======================

This example shows a dummy streaming setup that uses the recording included
in the package.
"""
import sys
import logging

import pupil_recording_interface as pri


# %%
# Set recording folder
# --------------------
folder = pri.DATA_DIR / "test_recording"

# %%
# Set up stream configurations
# ----------------------------
configs = [
    pri.VideoStream.Config(
        device_type="video_file",
        device_uid="world",
        resolution=(1280, 720),
        pipeline=[pri.GazeMapper.Config(), pri.VideoDisplay.Config()],
    ),
    pri.VideoStream.Config(
        device_type="video_file",
        device_uid="eye0",
        resolution=(192, 192),
        pipeline=[
            pri.VideoFileSyncer.Config("world"),
            pri.PupilDetector.Config(),
            pri.VideoDisplay.Config(flip=True),
        ],
    ),
    pri.VideoStream.Config(
        device_type="video_file",
        device_uid="eye1",
        resolution=(192, 192),
        pipeline=[
            pri.VideoFileSyncer.Config("world"),
            pri.PupilDetector.Config(),
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
#
# .. note::
#
#     When running the script from the command line, press 'Ctrl+C' to stop the
#     manager. When running from a Jupyter notebook, interrupt the kernel
#     (*Kernel > Interrupt Kernel* or press 'Esc' and then twice 'i').
with pri.StreamManager(configs, folder=folder, policy="read") as manager:
    while not manager.stopped:
        if manager.all_streams_running:
            status = manager.format_status(
                "fps", format="{:.2f} Hz", max_cols=72, sleep=0.1
            )
            print("\r" + status, end="")

print("\nStopped")
