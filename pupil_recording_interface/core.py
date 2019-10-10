""""""
import os
import json

import numpy as np
import pandas as pd
import xarray as xr

from pupil_recording_interface.externals.file_methods import load_pldata_file, load_object


class Exporter(object):

    def __init__(self, folder):
        """"""
        if not os.path.exists(folder):
            raise FileNotFoundError(f'No such folder: {folder}')

        self.folder = folder
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
    def _load_gaze(folder, topic='gaze'):
        """"""
        df = Exporter._pldata_as_dataframe(folder, topic)

        t = df.timestamp
        c = df.confidence
        n = np.array(df.norm_pos.to_list())
        p = np.nan * np.ones(t.shape + (3,))
        idx_notnan = df.gaze_point_3d.apply(lambda x: isinstance(x, tuple))
        p[idx_notnan, :] = np.array(df.gaze_point_3d[idx_notnan].to_list())

        return t, c, n, p

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
        t, c, n, p = self._load_gaze(self.folder)

        t = pd.to_datetime(t - self.info['start_time_synced_s']
                           + self.info['start_time_system_s'], unit='s')
        coords = {
            'time': t.values,
            'cartesian_axis': ['x', 'y', 'z'],
            'pixel_axis': ['x', 'y'],
        }

        data_vars = {
            'gaze_confidence': ('time', c),
            'gaze_point': (['time', 'cartesian_axis'], p),
            'gaze_norm_pos': (['time', 'pixel_axis'], n),
        }

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
