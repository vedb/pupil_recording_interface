""""""
import os
import abc
import csv
import json

import numpy as np
import pandas as pd

from pupil_recording_interface.externals.file_methods import load_pldata_file

FileNotFoundError = OSError


class BaseInterface(object):

    def __init__(self, folder, source='recording'):
        """"""
        if not os.path.exists(folder):
            raise FileNotFoundError('No such folder: {}'.format(folder))

        self.folder = folder
        self.source = source

        if os.path.exists(os.path.join(self.folder, 'info.csv')):
            self.info = self._load_info(self.folder, 'info.csv')
        else:
            self.info = self._load_info(self.folder)

        self.user_info = self._load_user_info(
            self.folder, self.info['start_time_system_s'])

    @property
    def nc_name(self):
        return 'base'

    @staticmethod
    def _load_legacy_info(file_handle):
        """"""
        reader = csv.reader(file_handle)
        info = {rows[0]: rows[1] for rows in reader}

        info = {
            "duration_s":
                sum(float(x) * 60 ** i for i, x in
                    enumerate(reversed(info['Duration Time'].split(":")))),
            "meta_version": "2.0",
            "min_player_version": info['Data Format Version'],
            "recording_name": info['Recording Name'],
            "recording_software_name": "Pupil Capture",
            "recording_software_version": info['Capture Software Version'],
            "recording_uuid": info['Recording UUID'],
            "start_time_synced_s": float(info['Start Time (Synced)']),
            "start_time_system_s": float(info['Start Time (System)']),
            "system_info": info['System Info']
        }

        return info

    @staticmethod
    def _load_info(folder, filename='info.player.json'):
        """"""
        if not os.path.exists(os.path.join(folder, filename)):
            raise FileNotFoundError(
                'File {} not found in folder {}'.format(filename, folder))

        with open(os.path.join(folder, filename)) as f:
            if filename.endswith('.json'):
                info = json.load(f)
            elif filename.endswith('.csv'):
                info = BaseInterface._load_legacy_info(f)
            else:
                raise ValueError('Unsupported info file type.')

        return info

    @staticmethod
    def _load_user_info(folder, start_time, filename='user_info.csv'):
        """"""
        if not os.path.exists(os.path.join(folder, filename)):
            raise FileNotFoundError(
                'File {} not found in folder {}'.format(filename, folder))

        with open(os.path.join(folder, filename)) as f:
            reader = csv.reader(f)
            info = {rows[0]: rows[1] for rows in reader if rows[0] != 'key'}

        for k, v in info.items():
            if k.endswith(('start', 'end')):
                info[k] = \
                    pd.to_timedelta(v) + pd.to_datetime(start_time, unit='s')

        return info

    @staticmethod
    def _load_pldata_as_dataframe(folder, topic):
        """"""
        if not os.path.exists(os.path.join(folder, topic + '.pldata')):
            raise FileNotFoundError(
                'File {}.pldata not found in folder {}'.format(topic, folder))

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
    def _load_timestamps_as_datetimeindex(folder, topic, info, offset=0.):
        """"""
        filepath = os.path.join(folder, topic + '_timestamps.npy')
        if not os.path.exists(filepath):
            raise FileNotFoundError(
                'File {}_timestamps.npy not found in folder {}'.format(
                    topic, folder))

        timestamps = np.load(filepath)
        idx = BaseInterface._timestamps_to_datetimeindex(timestamps, info)
        return idx + pd.to_timedelta(offset, unit='s')

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
        try:
            os.makedirs(folder)
        except OSError:
            pass

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
            raise FileNotFoundError('No such folder: {}'.format(folder))

        self.folder = folder
