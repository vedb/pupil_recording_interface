"""
.. _gaze_pipeline_example:

Gaze mapping pipeline
=====================

This example shows how to perform post-hoc pupil detection, calibration marker
detection, calibration and gaze mapping.

.. note::

    This example requires the dependencies for
    :ref:`pupil detection<pupil_detection_dependencies>` as well as
    ``matplotlib``.
"""
import pupil_recording_interface as pri


# %%
# Set recording folder
# --------------------
folder = pri.get_test_recording()

# %%
# Create readers for video streams
# --------------------------------
world_reader = pri.VideoReader(folder)
eye0_reader = pri.VideoReader(folder, stream="eye0", color_format="gray")
eye1_reader = pri.VideoReader(folder, stream="eye1", color_format="gray")

# %%
# Detect pupils
# -------------
pupil_detector_eye0 = pri.PupilDetector(camera_id=0)
pupil_list_eye0 = pupil_detector_eye0.batch_run(eye0_reader)

pupil_detector_eye1 = pri.PupilDetector(camera_id=1)
pupil_list_eye1 = pupil_detector_eye1.batch_run(eye1_reader)

# %%
# Detect calibration markers
# --------------------------
marker_detector = pri.CircleDetector()
marker_list = marker_detector.batch_run(world_reader)

# %%
# Merge pupil data and run calibration
# ------------------------------------
calibration = pri.Calibration(resolution=world_reader.resolution)
pupil_list = pri.merge_pupils(pupil_list_eye0, pupil_list_eye1)
calibration_result = calibration.batch_run(pupil_list, marker_list)

# %%
# Map gaze as dataset
# -------------------
gaze_mapper = pri.GazeMapper(calibration=calibration_result)
gaze = gaze_mapper.batch_run(
    pupil_list, return_type="dataset", info=world_reader.info
)

# %%
# Plot gaze
# ---------
norm_pos = gaze.gaze_norm_pos.where(gaze.gaze_confidence_2d > 0.7)
norm_pos.plot.line(x="time")
