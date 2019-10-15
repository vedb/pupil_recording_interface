""""""
import os
import abc

import numpy as np
import pandas as pd

import json
from pupil_recording_interface.externals.file_methods import load_pldata_file


class BaseInterface(object):

    def __init__(self, folder, source='recording'):
        """"""
        if not os.path.exists(folder):
            raise FileNotFoundError(f'No such folder: {folder}')

        self.folder = folder
        self.source = source
        self.info = self._load_info(self.folder)

    @property
    def nc_name(self):
        return 'base'

    @staticmethod
    def _load_info(folder, filename='info.player.json'):
        """"""
        # TODO support csv
        if not os.path.exists(os.path.join(folder, filename)):
            raise FileNotFoundError(
                f'File {filename} not found in folder {folder}')

        with open(os.path.join(folder, filename)) as f:
            info = json.load(f)

        return info

    @staticmethod
    def _load_pldata_as_dataframe(folder, topic):
        """"""
        if not os.path.exists(os.path.join(folder, topic + '.pldata')):
            raise FileNotFoundError(
                f'File {topic}.pldata not found in folder {folder}')

        pldata = load_pldata_file(folder, topic)
        return pd.DataFrame([dict(d) for d in pldata.data])

    @staticmethod
    def _timestamps_to_datetimeindex(timestamps, info):
        """"""
        return pd.to_datetime(timestamps
                              - info['start_time_synced_s']
                              + info['start_time_system_s'],
                              unit='s')

    @staticmethod
    def _load_timestamps_as_datetimeindex(folder, topic, info):
        """"""
        filepath = os.path.join(folder, topic + '_timestamps.npy')
        if not os.path.exists(filepath):
            raise FileNotFoundError(
                f'File {topic}_timestamps.npy not found in folder {folder}')

        timestamps = np.load(filepath)
        return BaseInterface._timestamps_to_datetimeindex(timestamps, info)

    @staticmethod
    def _get_encoding(data_vars, dtype='int32'):
        """"""
        comp = {
            'zlib': True,
            'dtype': dtype,
            'scale_factor': 0.0001,
            '_FillValue': np.iinfo(dtype).min,
        }

        return {v: comp for v in data_vars}

    @staticmethod
    def _create_export_folder(filename):
        """"""
        folder = os.path.dirname(filename)
        os.makedirs(folder, exist_ok=True)

    @abc.abstractmethod
    def load_dataset(self):
        """"""

    def write_netcdf(self, filename=None):
        """"""
        ds = self.load_dataset()
        encoding = self._get_encoding(ds.data_vars)

        if filename is None:
            filename = os.path.join(
                self.folder, 'exports', self.nc_name + '.nc')

        self._create_export_folder(filename)
        ds.to_netcdf(filename, encoding=encoding)


class BaseRecorder(object):

    def __init__(self, folder):
        """"""
        if not os.path.exists(folder):
            raise FileNotFoundError(f'No such folder: {folder}')

        self.folder = folder
