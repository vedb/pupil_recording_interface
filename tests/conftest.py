import os
import shutil

import pytest
import numpy as np

from pupil_recording_interface import DATA_DIR
from pupil_recording_interface.stream import VideoStream
from pupil_recording_interface.packet import Packet
from pupil_recording_interface.pipeline import Pipeline
from pupil_recording_interface.process.display import VideoDisplay
from pupil_recording_interface.process.cam_params import CamParamEstimator


@pytest.fixture()
def folder():
    """"""
    return os.path.join(DATA_DIR, "test_recording")


@pytest.fixture()
def export_folder(folder):
    """"""
    export_folder = os.path.join(folder, "exports")
    yield export_folder
    shutil.rmtree(export_folder, ignore_errors=True)


@pytest.fixture()
def info():
    """"""
    return {
        "duration_s": 21.111775958999715,
        "meta_version": "2.0",
        "min_player_version": "1.16",
        "recording_name": "2019_10_10",
        "recording_software_name": "Pupil Capture",
        "recording_software_version": "1.16.95",
        "recording_uuid": "e5059604-26f1-42ed-8e35-354198b56021",
        "start_time_synced_s": 2294.807856069,
        "start_time_system_s": 1570725800.220913,
        "system_info": "User: test_user, Platform: Linux",
    }


@pytest.fixture()
def statuses():
    """"""
    return {
        "world": {
            "name": "world",
            "timestamp": 1.0,
            "last_timestamp": 0.0,
            "fps": 30.0,
        },
        "eye0": {
            "name": "eye0",
            "timestamp": 1.0,
            "last_timestamp": 0.0,
            "fps": 120.0,
            "pupil": {
                "ellipse": {
                    "center": (0.0, 0.0),
                    "axes": (0.0, 0.0),
                    "angle": -90.0,
                },
                "diameter": 0.0,
                "location": (0.0, 0.0),
                "confidence": 0.0,
            },
        },
    }


@pytest.fixture()
def packet():
    """"""
    return Packet(
        0.0,
        frame=np.zeros((1280, 720), dtype=np.uint8),
        display_frame=np.zeros((1280, 720), dtype=np.uint8),
        pupil={
            "ellipse": {
                "center": (0.0, 0.0),
                "axes": (0.0, 0.0),
                "angle": -90.0,
            },
            "diameter": 0.0,
            "location": (0.0, 0.0),
            "confidence": 0.0,
        },
        gaze_points=[(0.5, 0.5), (0.6, 0.6)],
        circle_markers=[
            {
                "ellipses": [
                    (
                        (399.16404724121094, 215.4773941040039),
                        (7.052967071533203, 8.333015441894531),
                        43.05573272705078,
                    ),
                    (
                        (399.69960021972656, 215.33668518066406),
                        (53.05698776245117, 67.6202621459961),
                        8.497730255126953,
                    ),
                    (
                        (400.78492736816406, 215.5298080444336),
                        (109.97621154785156, 137.57115173339844),
                        8.513727188110352,
                    ),
                    (
                        (402.8581237792969, 215.88968658447266),
                        (170.45883178710938, 213.98965454101562),
                        8.824980735778809,
                    ),
                ],
                "img_pos": (399.16404724121094, 215.4773941040039),
                "norm_pos": (0.31184691190719604, 0.7007258415222168),
                "marker_type": "Ref",
            }
        ],
        resolution=(1280, 720),
        grid_points=np.array(
            [
                [[100.0, 100.0]],
                [[100.0, 200.0]],
                [[200.0, 100.0]],
                [[200.0, 200.0]],
            ],
            dtype=np.float32,
        ),
    )


# -- STREAMS -- #
@pytest.fixture()
def video_stream(pipeline):
    """"""
    return VideoStream(None, pipeline, "test_stream")


@pytest.fixture()
def video_config():
    """"""
    return VideoStream.Config(
        "uvc", "test_cam", resolution=(1280, 720), fps=30
    )


# -- PROCESSES -- #
@pytest.fixture()
def video_display():
    """"""
    return VideoDisplay(
        "test", overlay_pupil=True, overlay_gaze=True, overlay_circle_grid=True
    )


@pytest.fixture()
def cam_param_estimator(packet):
    """"""
    estimator = CamParamEstimator(["world", "t265"])
    estimator._pattern_queue.put(
        {
            "world": (packet.resolution, packet.grid_points),
            "t265": (
                packet.resolution,
                [packet.grid_points, packet.grid_points],
            ),
        }
    )

    return estimator


@pytest.fixture()
def pipeline(video_display):
    """"""
    return Pipeline([video_display])
