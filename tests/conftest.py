import os
import shutil

import pytest

from pupil_recording_interface import TEST_RECORDING
from pupil_recording_interface import VideoConfig, OdometryConfig


@pytest.fixture()
def folder():
    """"""
    return TEST_RECORDING


@pytest.fixture()
def output_folder():
    """"""
    output_folder = os.path.join(os.path.dirname(__file__), 'out')
    yield output_folder
    shutil.rmtree(output_folder, ignore_errors=True)


@pytest.fixture()
def export_folder(folder):
    """"""
    export_folder = os.path.join(folder, 'exports')
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
        "system_info": "User: test_user, Platform: Linux"
    }


@pytest.fixture()
def uvc_config():
    """"""
    return [
        VideoConfig(
            'uvc', 'Pupil Cam1 ID2', name='world',
            resolution=(1280, 720), fps=60),
        VideoConfig(
            'uvc', 'Pupil Cam1 ID0', name='eye0',
            resolution=(320, 240), fps=120, color_format='gray'),
        VideoConfig(
            'uvc', 'Pupil Cam1 ID1', name='eye1',
            resolution=(320, 240), fps=120, color_format='gray'),
    ]


@pytest.fixture()
def t265_config():
    """"""
    return [
        VideoConfig(
            't265', 't265',
            resolution=(1696, 800), fps=30, color_format='gray'),
        OdometryConfig(
            't265', 't265', name='odometry')
    ]
