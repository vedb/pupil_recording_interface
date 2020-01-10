import os

from .test_base import ReaderTester

import xarray as xr

from pupil_recording_interface import GazeReader

from pupil_recording_interface.errors import FileNotFoundError


class TestGazeReader(ReaderTester):

    def setUp(self):
        """"""
        super(TestGazeReader, self).setUp()
        self.n_gaze = 5160
        self.n_gaze_offline = 5134
        self.gaze_mappers = {'2d': '2d Gaze Mapper ', '3d': '3d Gaze Mapper'}

    def test_load_gaze(self):
        """"""
        t, c, n, p = GazeReader._load_gaze(self.folder)

        assert t.shape == (self.n_gaze,)
        assert c.shape == (self.n_gaze,)
        assert n.shape == (self.n_gaze, 2)
        assert p.shape == (self.n_gaze, 3)

    def test_load_merged_gaze(self):
        """"""
        t, c, n, p = GazeReader._load_merged_gaze(
            self.folder, self.gaze_mappers)

        assert t.shape == (self.n_gaze_offline,)
        assert c[0].shape == (self.n_gaze_offline,)
        assert c[1].shape == (self.n_gaze_offline,)
        assert n.shape == (self.n_gaze_offline, 2)
        assert p.shape == (self.n_gaze_offline, 3)

    def test_get_offline_gaze_mapper(self):
        """"""
        mappers = GazeReader._get_offline_gaze_mappers(self.folder)

        assert set(mappers.keys()) == {'3d Gaze Mapper', '2d Gaze Mapper '}
        for v in mappers.values():
            assert os.path.exists(os.path.join(
                self.folder, 'offline_data', 'gaze-mappings', v + '.pldata'))

        with self.assertRaises(FileNotFoundError):
            GazeReader._get_offline_gaze_mappers('not_a_folder')

    def test_load_dataset(self):
        """"""
        # from recording
        ds = GazeReader(self.folder).load_dataset()

        self.assertDictEqual(dict(ds.sizes), {
            'time': self.n_gaze,
            'cartesian_axis': 3,
            'pixel_axis': 2})

        assert set(ds.data_vars) == {
            'gaze_confidence_3d', 'gaze_point', 'gaze_norm_pos'}

        # offline 2d mapper
        ds = GazeReader(
            self.folder, source=self.gaze_mappers['2d']).load_dataset()

        self.assertDictEqual(dict(ds.sizes), {
            'time': self.n_gaze_offline,
            'pixel_axis': 2})

        assert set(ds.data_vars) == {
            'gaze_confidence_2d', 'gaze_norm_pos'}

        # merged 2d/3d gaze
        ds = GazeReader(
            self.folder, source=self.gaze_mappers).load_dataset()

        self.assertDictEqual(dict(ds.sizes), {
            'time': self.n_gaze_offline,
            'cartesian_axis': 3,
            'pixel_axis': 2})

        assert set(ds.data_vars) == {
            'gaze_confidence_2d', 'gaze_confidence_3d', 'gaze_point',
            'gaze_norm_pos'}

        # bad gaze argument
        with self.assertRaises(ValueError):
            GazeReader(
                self.folder, source='not_gaze_mapper').load_dataset()

    def test_write_netcdf(self):
        """"""
        GazeReader(self.folder).write_netcdf()

        ds = xr.open_dataset(os.path.join(self.export_folder, 'gaze.nc'))

        assert set(ds.data_vars) == {
            'gaze_confidence_3d', 'gaze_point', 'gaze_norm_pos'}

        ds.close()
