""""""
import os
import json

import numpy as np
import pandas as pd
import xarray as xr

from pupil_exporter.externals.file_methods import load_pldata_file, load_object


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
        if not os.path.exists(os.path.join(folder, filename)):
            raise FileNotFoundError(
                f'File {filename} not found in folder {folder}')

        with open(os.path.join(folder, filename)) as f:
            info = json.load(f)

        return info

    @staticmethod
    def _load_odometry(folder, topic='odometry'):
        """"""
        if not os.path.exists(os.path.join(folder, topic + '.pldata')):
            raise FileNotFoundError(
                f'File {topic}.pldata not found in folder {folder}')

        pldata = load_pldata_file(folder, topic)
        df = pd.DataFrame([dict(d) for d in pldata.data])
        t = df.timestamp
        c = df.confidence
        p = np.array(df.position.to_list())
        q = np.array(df.orientation.to_list())
        v = np.array(df.linear_velocity.to_list())
        w = np.array(df.angular_velocity.to_list())

        return t, c, p, q, v, w

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
            'confidence': ('time', c),
            'linear_velocity': (['time', 'cartesian_axis'], v),
            'angular_velocity': (['time', 'cartesian_axis'], w),
            'linear_position': (['time', 'cartesian_axis'], p),
            'angular_position': (['time', 'quaternion_axis'], q),
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
