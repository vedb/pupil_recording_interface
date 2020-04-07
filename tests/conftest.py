import os
import shutil

import pytest

from pupil_recording_interface import DATA_DIR
from pupil_recording_interface.config import VideoConfig
from pupil_recording_interface.stream import VideoStream
from pupil_recording_interface.pipeline import Pipeline
from pupil_recording_interface.process import VideoDisplay


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
def video_config():
    """"""
    return VideoConfig("uvc", "test_cam", (1280, 720), 30)


@pytest.fixture()
def pipeline():
    """"""
    return Pipeline([VideoDisplay("test")])


@pytest.fixture()
def video_stream(pipeline):
    """"""
    return VideoStream(None, pipeline, "test_stream")


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
