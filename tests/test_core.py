import os
import shutil

from unittest import TestCase

import numpy as np
import xarray as xr

from pupil_exporter.core import Exporter

test_data_dir = os.path.join(os.path.dirname(__file__), 'test_data')


class TestExporter(TestCase):

    def setUp(self):
        """"""
        self.folder = os.path.join(test_data_dir, 'test_recording')
        self.n_samples = 4220

    def test_constructor(self):
        """"""
        exporter = Exporter(self.folder)
        assert exporter.folder == self.folder

        with self.assertRaises(FileNotFoundError):
            Exporter('not_a_folder')

    def test_load_info(self):
        """"""
        self.assertDictEqual(Exporter._load_info(self.folder), {
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
            Exporter._load_info(self.folder, 'not_a_file')

    def test_load_odometry(self):
        """"""
        t, c, p, q, v, w = Exporter._load_odometry(self.folder)

        assert t.shape == (self.n_samples,)
        assert c.shape == (self.n_samples,)
        assert c.dtype == int
        assert p.shape == (self.n_samples, 3)
        assert q.shape == (self.n_samples, 4)
        assert v.shape == (self.n_samples, 3)
        assert w.shape == (self.n_samples, 3)

        with self.assertRaises(FileNotFoundError):
            Exporter._load_odometry(self.folder, 'not_a_topic')

    def test_get_encoding(self):
        """"""
        encoding = Exporter._get_encoding(['test_var'])

        self.assertDictEqual(encoding['test_var'], {
            'zlib': True,
            'dtype': 'int32',
            'scale_factor': 0.0001,
            '_FillValue': np.iinfo('int32').min
        })

    def test_create_export_folder(self):
        """"""
        export_folder = os.path.join(self.folder, 'exports')
        Exporter._create_export_folder(os.path.join(export_folder, 'test.nc'))

        assert os.path.exists(export_folder)
        os.removedirs(export_folder)

    def test_load_odometry_dataset(self):
        """"""
        ds = Exporter(self.folder).load_odometry_dataset()

        self.assertDictEqual(dict(ds.sizes), {
            'time': self.n_samples,
            'cartesian_axis': 3,
            'quaternion_axis': 4})

        assert list(ds.data_vars) == [
            'confidence', 'linear_velocity', 'angular_velocity',
            'linear_position', 'angular_position']

    def test_write_odometry_dataset(self):
        """"""
        Exporter(self.folder).write_odometry_dataset()

        ds = xr.open_dataset(
            os.path.join(self.folder, 'exports', 'odometry.nc'))

        assert list(ds.data_vars) == [
            'confidence', 'linear_velocity', 'angular_velocity',
            'linear_position', 'angular_position']

        ds.close()
        shutil.rmtree(os.path.join(self.folder, 'exports'))
