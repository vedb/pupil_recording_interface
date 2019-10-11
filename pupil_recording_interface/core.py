""""""
import os
import json
from msgpack import Unpacker

import numpy as np
import pandas as pd
import xarray as xr

from pupil_recording_interface.externals.file_methods import \
    load_pldata_file, load_object


def load(folder, gaze_mapper='recording'):
    """"""
    return Exporter(folder, gaze_mapper=gaze_mapper).load()


def export(folder, gaze_mapper='recording'):
    """"""
    Exporter(folder, gaze_mapper=gaze_mapper).export()


class Exporter(object):

    def __init__(self, folder, gaze_mapper='recording'):
        """"""
        if not os.path.exists(folder):
            raise FileNotFoundError(f'No such folder: {folder}')

        self.folder = folder
        self.gaze_mapper = gaze_mapper
        self.info = self._load_info(self.folder)

    @staticmethod
    def _load_info(folder, filename='info.player.json'):
        """"""
        # TODO maybe support older versions
        if not os.path.exists(os.path.join(folder, filename)):
            raise FileNotFoundError(
                f'File {filename} not found in folder {folder}')

        with open(os.path.join(folder, filename)) as f:
            info = json.load(f)

        return info

    @staticmethod
    def _pldata_as_dataframe(folder, topic):
        """"""
        if not os.path.exists(os.path.join(folder, topic + '.pldata')):
            raise FileNotFoundError(
                f'File {topic}.pldata not found in folder {folder}')

        pldata = load_pldata_file(folder, topic)
        return pd.DataFrame([dict(d) for d in pldata.data])


    @staticmethod
    def _load_odometry(folder, topic='odometry'):
        """"""
        df = Exporter._pldata_as_dataframe(folder, topic)

        t = df.timestamp
        c = df.confidence
        p = np.array(df.position.to_list())
        q = np.array(df.orientation.to_list())
        v = np.array(df.linear_velocity.to_list())
        w = np.array(df.angular_velocity.to_list())

        return t, c, p, q, v, w

    @staticmethod
    def _load_gaze(folder, topic='gaze', is_2d=False):
        """"""
        df = Exporter._pldata_as_dataframe(folder, topic)

        t = df.timestamp
        c = df.confidence
        n = np.array(df.norm_pos.to_list())

        if is_2d:
            p = None
        else:
            p = np.nan * np.ones(t.shape + (3,))
            idx_notnan = df.gaze_point_3d.apply(lambda x: isinstance(x, tuple))
            p[idx_notnan, :] = np.array(df.gaze_point_3d[idx_notnan].to_list())

        return t, c, n, p

    @staticmethod
    def _merge_2d_3d_gaze(gaze_2d, gaze_3d):
        """"""
        t, idx_2d, idx_3d = np.intersect1d(
            gaze_2d[0], gaze_3d[0], assume_unique=True, return_indices=True)

        return t, (gaze_2d[1][idx_2d], gaze_3d[1][idx_3d]), \
               gaze_2d[2][idx_2d], gaze_3d[3][idx_3d]

    @staticmethod
    def _get_offline_gaze_mappers(folder):
        """"""
        filepath = os.path.join(folder, 'offline_data', 'gaze_mappers.msgpack')

        if not os.path.exists(filepath):
            raise FileNotFoundError('No offline gaze mappers found')

        with open(filepath, 'rb') as f:
            gm_data = Unpacker(f, use_list=False).unpack()[b'data']

        def get_topic(name, urn):
            return name.decode().replace(' ', '_') + '-' + urn.decode()

        return {g[1].decode(): get_topic(g[1], g[0]) for g in gm_data}

    @staticmethod
    def _load_merged_gaze(folder, gaze_mapper):
        """"""
        offline_mappers = Exporter._get_offline_gaze_mappers(folder)

        mapper_folder = os.path.join(folder, 'offline_data', 'gaze-mappings')
        gaze_2d = Exporter._load_gaze(
            mapper_folder, offline_mappers[gaze_mapper['2d']], is_2d=True)
        gaze_3d = Exporter._load_gaze(
            mapper_folder, offline_mappers[gaze_mapper['3d']])

        return Exporter._merge_2d_3d_gaze(gaze_2d, gaze_3d)

    @staticmethod
    def _get_encoding(data_vars, dtype='int32'):
        """"""
        comp = {
            'zlib': True,
            'dtype': dtype,
            'scale_factor': 0.0001,
            '_FillValue': np.iinfo(dtype).min
        }

        encoding = {v: comp for v in data_vars}

        return encoding

    @staticmethod
    def _create_export_folder(filename):
        """"""
        folder = os.path.dirname(filename)
        os.makedirs(folder, exist_ok=True)

    def load_odometry_dataset(self):
        """"""
        t, c, p, q, v, w = self._load_odometry(self.folder)

        t = pd.to_datetime(t - self.info['start_time_synced_s']
                           + self.info['start_time_system_s'], unit='s')
        coords = {
            'time': t.values,
            'cartesian_axis': ['x', 'y', 'z'],
            'quaternion_axis': ['w', 'x', 'y', 'z'],
        }

        data_vars = {
            'tracker_confidence': ('time', c),
            'linear_velocity': (['time', 'cartesian_axis'], v),
            'angular_velocity': (['time', 'cartesian_axis'], w),
            'linear_position': (['time', 'cartesian_axis'], p),
            'angular_position': (['time', 'quaternion_axis'], q),
        }

        return xr.Dataset(data_vars, coords)

    def load_gaze_dataset(self):
        """"""
        if self.gaze_mapper == 'recording':
            t, c, n, p = self._load_gaze(self.folder)
        elif isinstance(self.gaze_mapper, dict) \
                and set(self.gaze_mapper.keys()) == {'2d', '3d'}:
            t, c, n, p = self._load_merged_gaze(self.folder, self.gaze_mapper)
        else:
            raise ValueError(
                f'Invalid gaze mapper selector: {self.gaze_mapper}')

        t = pd.to_datetime(t - self.info['start_time_synced_s']
                           + self.info['start_time_system_s'], unit='s')
        coords = {
            'time': t.values,
            'cartesian_axis': ['x', 'y', 'z'],
            'pixel_axis': ['x', 'y'],
        }

        data_vars = {
            'gaze_norm_pos': (['time', 'pixel_axis'], n),
        }

        # gaze point only available from 3d mapper
        if p is not None:
            data_vars['gaze_point'] = (['time', 'cartesian_axis'], p)

        # two confidence values from merged 2d/3d gaze
        if isinstance(c, tuple):
            assert len(c) == 2
            data_vars['gaze_confidence_2d'] = ('time', c[0])
            data_vars['gaze_confidence_3d'] = ('time', c[1])
        else:
            data_vars['gaze_confidence'] = ('time', c)

        return xr.Dataset(data_vars, coords)

    def write_odometry_dataset(self, filename=None):
        """"""
        ds = self.load_odometry_dataset()
        encoding = self._get_encoding(ds.data_vars)

        if filename is None:
            filename = os.path.join(self.folder, 'exports', 'odometry.nc')

        self._create_export_folder(filename)
        ds.to_netcdf(filename, encoding=encoding)

    def write_gaze_dataset(self, filename=None):
        """"""
        ds = self.load_gaze_dataset()
        encoding = self._get_encoding(ds.data_vars)

        if filename is None:
            filename = os.path.join(self.folder, 'exports', 'gaze.nc')

        self._create_export_folder(filename)
        ds.to_netcdf(filename, encoding=encoding)

    def load(self):
        """"""
        return self.load_gaze_dataset(), self.load_odometry_dataset()

    def export(self, filename=None):
        """"""
        self.write_gaze_dataset(filename=filename)
        self.write_odometry_dataset(filename=filename)
