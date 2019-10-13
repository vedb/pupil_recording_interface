import os
import shutil

from unittest import TestCase

import numpy as np

from pupil_recording_interface import load_dataset, write_netcdf, \
    OdometryInterface
from pupil_recording_interface.base import \
    BaseInterface

test_data_dir = os.path.join(os.path.dirname(__file__), 'test_data')


class InterfaceTester(TestCase):

    def setUp(self):
        """"""
        self.folder = os.path.join(test_data_dir, 'test_recording')
        self.export_folder = os.path.join(self.folder, 'exports')

    def tearDown(self):
        """"""
        shutil.rmtree(self.export_folder, ignore_errors=True)


class TestBaseInterface(InterfaceTester):

    def test_constructor(self):
        """"""
        exporter = BaseInterface(self.folder)
        assert exporter.folder == self.folder

        with self.assertRaises(FileNotFoundError):
            BaseInterface('not_a_folder')

    def test_load_info(self):
        """"""
        self.assertDictEqual(BaseInterface._load_info(self.folder), {
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
        })

        with self.assertRaises(FileNotFoundError):
            BaseInterface._load_info(self.folder, 'not_a_file')

    def test_pldata_as_dataframe(self):
        """"""
        df = BaseInterface._pldata_as_dataframe(self.folder, 'odometry')

        assert set(df.columns) == {'topic', 'timestamp', 'confidence',
                                   'linear_velocity', 'angular_velocity',
                                   'position', 'orientation'}

        with self.assertRaises(FileNotFoundError):
            BaseInterface._pldata_as_dataframe(self.folder, 'not_a_topic')

    def test_get_encoding(self):
        """"""
        encoding = OdometryInterface._get_encoding(['test_var'])

        self.assertDictEqual(encoding['test_var'], {
            'zlib': True,
            'dtype': 'int32',
            'scale_factor': 0.0001,
            '_FillValue': np.iinfo('int32').min
        })

    def test_create_export_folder(self):
        """"""
        OdometryInterface._create_export_folder(
            os.path.join(self.export_folder, 'test.nc'))

        assert os.path.exists(self.export_folder)


class TestFunctionalInterface(InterfaceTester):

    def test_load_dataset(self):
        """"""
        gaze, odometry = load_dataset(
            self.folder, gaze='recording', odometry='recording')

        assert set(gaze.data_vars) == {
            'gaze_confidence', 'gaze_point', 'gaze_norm_pos'}
        assert set(odometry.data_vars) == {
            'tracker_confidence', 'linear_velocity', 'angular_velocity',
            'linear_position', 'angular_position'}

    def test_write_netcdf(self):
        """"""
        write_netcdf(
            self.folder, gaze='recording', odometry='recording')

        assert os.path.exists(
            os.path.join(self.folder, 'exports', 'odometry.nc'))
        assert os.path.exists(
            os.path.join(self.folder, 'exports', 'gaze.nc'))
