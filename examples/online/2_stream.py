"""
.. _streaming_example:

Stream from connected devices
=============================

This example shows how to stream video data from a connected Pupil Core
headset.

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
# Set up stream configurations
# ----------------------------
configs = [
    pri.VideoStream.Config(
        device_type="uvc",
        device_uid=f"Pupil Cam{pupil_gen} ID2",
        name="world",
        resolution=(1280, 720),
        fps=30,
        pipeline=[pri.VideoDisplay.Config()],
    ),
    pri.VideoStream.Config(
        device_type="uvc",
        device_uid=f"Pupil Cam{pupil_gen} ID0",
        name="eye0",
        resolution=(320, 240) if pupil_gen == 1 else (192, 192),
        fps=120,
        color_format="gray",
        pipeline=[pri.VideoDisplay.Config(flip=True)],
    ),
    pri.VideoStream.Config(
        device_type="uvc",
        device_uid=f"Pupil Cam{pupil_gen} ID1",
        name="eye1",
        resolution=(320, 240) if pupil_gen == 1 else (192, 192),
        fps=120,
        color_format="gray",
        pipeline=[pri.VideoDisplay.Config()],
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
with pri.StreamManager(configs) as manager:
    while not manager.stopped:
        if manager.all_streams_running:
            status = manager.format_status(
                "fps", format="{:.2f} Hz", max_cols=72, sleep=0.1
            )
            print("\r" + status, end="")

print("\nStopped")
