import os
import shutil

from unittest import TestCase

import numpy as np
import pandas as pd
import xarray as xr

from pupil_recording_interface import GazeInterface, load_dataset, write_netcdf
from pupil_recording_interface.base import BaseInterface

test_data_dir = os.path.join(os.path.dirname(__file__), 'test_data')

from pupil_recording_interface.errors import FileNotFoundError


class InterfaceTester(TestCase):

    def setUp(self):
        """"""
        self.folder = os.path.join(test_data_dir, 'test_recording')
        self.export_folder = os.path.join(self.folder, 'exports')
        self.info = {
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
        info = BaseInterface._load_info(self.folder)
        self.assertDictEqual(info, self.info)

        # legacy format
        info = BaseInterface._load_info(self.folder, 'info.csv')
        self.info['duration_s'] = 21.
        self.assertDictEqual(info, self.info)

        with self.assertRaises(FileNotFoundError):
            BaseInterface._load_info(self.folder, 'not_a_file')

    def test_load_user_info(self):
        """"""
        user_info = BaseInterface._load_user_info(
            self.folder, self.info['start_time_system_s'])
        
        t0 = pd.to_datetime(self.info['start_time_system_s'], unit='s')

        self.assertDictEqual(user_info, {
            'name': 'TEST',
            'pre_calibration_start': t0 + pd.to_timedelta('1s'),
            'pre_calibration_end': t0 + pd.to_timedelta('2s'),
            'experiment_start': t0 + pd.to_timedelta('3s'),
            'experiment_end': t0 + pd.to_timedelta('4s'),
            'post_calibration_start': t0 + pd.to_timedelta('5s'),
            'post_calibration_end': t0 + pd.to_timedelta('6s'),
        })

    def test_timestamps_to_datetimeindex(self):
        """"""
        timestamps = np.array([2295., 2296., 2297.])

        idx = BaseInterface._timestamps_to_datetimeindex(timestamps, self.info)

        assert idx.values[0].astype(float) / 1e9 == 1570725800.4130569

    def test_load_timestamps_as_datetimeindex(self):
        """"""
        idx = BaseInterface._load_timestamps_as_datetimeindex(
            self.folder, 'gaze', self.info)
        assert idx.values[0].astype(float) / 1e9 == 1570725800.149778

        # with offset
        idx_with_offs = BaseInterface._load_timestamps_as_datetimeindex(
            self.folder, 'gaze', self.info, 1.)
        assert np.all(idx_with_offs == idx + pd.to_timedelta('1s'))

        with self.assertRaises(FileNotFoundError):
            BaseInterface._load_timestamps_as_datetimeindex(
                self.folder, 'not_a_topic', self.info)

    def test_load_pldata_as_dataframe(self):
        """"""
        df = BaseInterface._load_pldata_as_dataframe(self.folder, 'odometry')

        assert set(df.columns) == {'topic', 'timestamp', 'confidence',
                                   'linear_velocity', 'angular_velocity',
                                   'position', 'orientation'}

        with self.assertRaises(FileNotFoundError):
            BaseInterface._load_pldata_as_dataframe(self.folder, 'not_a_topic')

    def test_get_encoding(self):
        """"""
        encoding = BaseInterface._get_encoding(['test_var'])

        self.assertDictEqual(encoding['test_var'], {
            'zlib': True,
            'dtype': 'int32',
            'scale_factor': 0.0001,
            '_FillValue': np.iinfo('int32').min
        })

    def test_create_export_folder(self):
        """"""
        BaseInterface._create_export_folder(
            os.path.join(self.export_folder, 'test.nc'))

        assert os.path.exists(self.export_folder)

    def test_write_netcdf(self):
        """"""
        GazeInterface(self.folder).write_netcdf()

        ds = xr.open_dataset(os.path.join(self.export_folder, 'gaze.nc'))

        assert set(ds.data_vars) == {
            'gaze_confidence_3d', 'gaze_point', 'gaze_norm_pos'}

        ds.close()


class TestFunctionalInterface(InterfaceTester):

    def test_load_dataset(self):
        """"""
        gaze, odometry = load_dataset(
            self.folder, gaze='recording', odometry='recording')

        assert set(gaze.data_vars) == {
            'gaze_confidence_3d', 'gaze_point', 'gaze_norm_pos'}
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
