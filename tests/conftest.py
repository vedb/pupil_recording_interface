import os
import shutil

import pytest

from pupil_recording_interface import DATA_DIR


@pytest.fixture()
def folder():
    """"""
    return os.path.join(DATA_DIR, 'test_recording')


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
