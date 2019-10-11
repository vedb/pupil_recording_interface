import os
import shutil

from unittest import TestCase

import numpy as np
import xarray as xr

from pupil_recording_interface.core import \
    write_netcdf, load_dataset, NetcdfInterface

test_data_dir = os.path.join(os.path.dirname(__file__), 'test_data')


class TestNetcdfInterface(TestCase):

    def setUp(self):
        """"""
        self.folder = os.path.join(test_data_dir, 'test_recording')
        self.n_odometry = 4220
        self.n_gaze = 5160
        self.n_gaze_offline = 5134
        self.gaze_mappers = {'2d': '2d Gaze Mapper ', '3d': '3d Gaze Mapper'}
        self.export_folder = os.path.join(self.folder, 'exports')

        shutil.rmtree(self.export_folder, ignore_errors=True)

    def test_constructor(self):
        """"""
        exporter = NetcdfInterface(self.folder)
        assert exporter.folder == self.folder

        with self.assertRaises(FileNotFoundError):
            NetcdfInterface('not_a_folder')

    def test_load_info(self):
        """"""
        self.assertDictEqual(NetcdfInterface._load_info(self.folder), {
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
            NetcdfInterface._load_info(self.folder, 'not_a_file')

    def test_pldata_as_dataframe(self):
        """"""
        df = NetcdfInterface._pldata_as_dataframe(self.folder, 'odometry')

        assert set(df.columns) == {'topic', 'timestamp', 'confidence',
                                   'linear_velocity', 'angular_velocity',
                                   'position', 'orientation'}

        with self.assertRaises(FileNotFoundError):
            NetcdfInterface._pldata_as_dataframe(self.folder, 'not_a_topic')

    def test_load_odometry(self):
        """"""
        t, c, p, q, v, w = NetcdfInterface._load_odometry(self.folder)

        assert t.shape == (self.n_odometry,)
        assert c.shape == (self.n_odometry,)
        assert c.dtype == int
        assert p.shape == (self.n_odometry, 3)
        assert q.shape == (self.n_odometry, 4)
        assert v.shape == (self.n_odometry, 3)
        assert w.shape == (self.n_odometry, 3)

    def test_load_gaze(self):
        """"""
        t, c, n, p = NetcdfInterface._load_gaze(self.folder)

        assert t.shape == (self.n_gaze,)
        assert c.shape == (self.n_gaze,)
        assert n.shape == (self.n_gaze, 2)
        assert p.shape == (self.n_gaze, 3)

    def test_load_merged_gaze(self):
        """"""
        t, c, n, p = NetcdfInterface._load_merged_gaze(
            self.folder, self.gaze_mappers)

        assert t.shape == (self.n_gaze_offline,)
        assert c[0].shape == (self.n_gaze_offline,)
        assert c[1].shape == (self.n_gaze_offline,)
        assert n.shape == (self.n_gaze_offline, 2)
        assert p.shape == (self.n_gaze_offline, 3)

    def test_get_offline_gaze_mapper(self):
        """"""
        mappers = NetcdfInterface._get_offline_gaze_mappers(self.folder)

        assert set(mappers.keys()) == {'3d Gaze Mapper', '2d Gaze Mapper '}
        for v in mappers.values():
            assert os.path.exists(os.path.join(
                self.folder, 'offline_data', 'gaze-mappings', v + '.pldata'))

        with self.assertRaises(FileNotFoundError):
            NetcdfInterface._get_offline_gaze_mappers('not_a_folder')

    def test_get_encoding(self):
        """"""
        encoding = NetcdfInterface._get_encoding(['test_var'])

        self.assertDictEqual(encoding['test_var'], {
            'zlib': True,
            'dtype': 'int32',
            'scale_factor': 0.0001,
            '_FillValue': np.iinfo('int32').min
        })

    def test_create_export_folder(self):
        """"""
        NetcdfInterface._create_export_folder(
            os.path.join(self.export_folder, 'test.nc'))

        assert os.path.exists(self.export_folder)

    def test_load_gaze_dataset(self):
        """"""
        # no gaze
        assert NetcdfInterface(
            self.folder, gaze=None).load_gaze_dataset() is None

        # from recording
        ds = NetcdfInterface(self.folder).load_gaze_dataset()

        self.assertDictEqual(dict(ds.sizes), {
            'time': self.n_gaze,
            'cartesian_axis': 3,
            'pixel_axis': 2})

        assert set(ds.data_vars) == {
            'gaze_confidence', 'gaze_point', 'gaze_norm_pos'}

        # offline 2d mapper
        ds = NetcdfInterface(
            self.folder, gaze=self.gaze_mappers['2d']).load_gaze_dataset()

        self.assertDictEqual(dict(ds.sizes), {
            'time': self.n_gaze_offline,
            'pixel_axis': 2})

        assert set(ds.data_vars) == {
            'gaze_confidence', 'gaze_norm_pos'}

        # merged 2d/3d gaze
        ds = NetcdfInterface(
            self.folder, gaze=self.gaze_mappers).load_gaze_dataset()

        self.assertDictEqual(dict(ds.sizes), {
            'time': self.n_gaze_offline,
            'cartesian_axis': 3,
            'pixel_axis': 2})

        assert set(ds.data_vars) == {
            'gaze_confidence_2d', 'gaze_confidence_3d', 'gaze_point',
            'gaze_norm_pos'}

        # bad gaze argument
        with self.assertRaises(ValueError):
            NetcdfInterface(
                self.folder, gaze='not_gaze_mapper').load_gaze_dataset()

    def test_write_gaze_dataset(self):
        """"""
        NetcdfInterface(self.folder).write_gaze_dataset()

        ds = xr.open_dataset(os.path.join(self.export_folder, 'gaze.nc'))

        assert set(ds.data_vars) == {
            'gaze_confidence', 'gaze_point', 'gaze_norm_pos'}

        ds.close()

    def test_load_odometry_dataset(self):
        """"""
        # no odometry
        assert NetcdfInterface(
            self.folder, odometry=None).load_odometry_dataset() is None

        # from recording
        ds = NetcdfInterface(
            self.folder, odometry='recording').load_odometry_dataset()

        self.assertDictEqual(dict(ds.sizes), {
            'time': self.n_odometry,
            'cartesian_axis': 3,
            'quaternion_axis': 4})

        assert set(ds.data_vars) == {
            'tracker_confidence', 'linear_velocity', 'angular_velocity',
            'linear_position', 'angular_position'}

        # bad odometry argument
        with self.assertRaises(ValueError):
            NetcdfInterface(
                self.folder, odometry='not_supported').load_odometry_dataset()

    def test_write_odometry_dataset(self):
        """"""
        NetcdfInterface(
            self.folder, odometry='recording').write_odometry_dataset()

        ds = xr.open_dataset(os.path.join(self.export_folder, 'odometry.nc'))

        assert set(ds.data_vars) == {
            'tracker_confidence', 'linear_velocity', 'angular_velocity',
            'linear_position', 'angular_position'}

        ds.close()

    def test_load_dataset(self):
        """"""
        gaze, odometry = load_dataset(self.folder, odometry='recording')

        assert set(gaze.data_vars) == {
            'gaze_confidence', 'gaze_point', 'gaze_norm_pos'}
        assert set(odometry.data_vars) == {
            'tracker_confidence', 'linear_velocity', 'angular_velocity',
            'linear_position', 'angular_position'}

    def test_write_netcdf(self):
        """"""
        write_netcdf(self.folder, odometry='recording')

        assert os.path.exists(
            os.path.join(self.folder, 'exports', 'odometry.nc'))
        assert os.path.exists(
            os.path.join(self.folder, 'exports', 'gaze.nc'))
