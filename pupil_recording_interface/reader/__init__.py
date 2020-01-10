""""""
import abc
import csv
import json
import os

import numpy as np
import pandas as pd

from pupil_recording_interface.externals.file_methods import load_pldata_file
from pupil_recording_interface.errors import FileNotFoundError


class BaseReader(object):
    """ Base class for all readers. """

    def __init__(self, folder, source='recording'):
        """ Constructor.

        Parameters
        ----------
        folder : str
            Path to the recording folder.

        source : str, default 'recording'
            The source of the data. If 'recording', the recorded data will
            be used.
        """
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
    def _nc_name(self):
        """ Name of exported netCDF file. """
        return 'base'

    @staticmethod
    def _load_legacy_info(file_handle):
        """ Load recording info from legacy file as dict. """
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
        """ Load recording info file as dict. """
        if not os.path.exists(os.path.join(folder, filename)):
            raise FileNotFoundError(
                'File {} not found in folder {}'.format(filename, folder))

        with open(os.path.join(folder, filename)) as f:
            if filename.endswith('.json'):
                info = json.load(f)
            elif filename.endswith('.csv'):
                info = BaseReader._load_legacy_info(f)
            else:
                raise ValueError('Unsupported info file type.')

        return info

    @staticmethod
    def _load_user_info(folder, start_time, filename='user_info.csv'):
        """ Load data from user_info.csv file as dict. """
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
            elif k == 'height':
                info[k] = float(v) / 100.

        return info

    @staticmethod
    def _load_pldata_as_dataframe(folder, topic):
        """ Load data from a .pldata file into a pandas.DataFrame. """
        if not os.path.exists(os.path.join(folder, topic + '.pldata')):
            raise FileNotFoundError(
                'File {}.pldata not found in folder {}'.format(topic, folder))

        pldata = load_pldata_file(folder, topic)
        return pd.DataFrame([dict(d) for d in pldata.data])

    @staticmethod
    def _timestamps_to_datetimeindex(timestamps, info):
        """ Convert timestamps from float to pandas.DatetimeIndex. """
        return pd.to_datetime(timestamps
                              - info['start_time_synced_s']
                              + info['start_time_system_s'],
                              unit='s')

    @staticmethod
    def _load_timestamps_as_datetimeindex(folder, topic, info, offset=0.):
        """ Load timestamps as pandas.DatetimeIndex. """
        filepath = os.path.join(folder, topic + '_timestamps.npy')
        if not os.path.exists(filepath):
            raise FileNotFoundError(
                'File {}_timestamps.npy not found in folder {}'.format(
                    topic, folder))

        timestamps = np.load(filepath)
        idx = BaseReader._timestamps_to_datetimeindex(timestamps, info)
        return idx + pd.to_timedelta(offset, unit='s')

    @staticmethod
    def _get_encoding(data_vars, dtype='int32'):
        """ Get encoding for each data var in the netCDF export. """
        comp = {
            'zlib': True,
            'dtype': dtype,
            'scale_factor': 0.0001,
            '_FillValue': np.iinfo(dtype).min,
        }

        return {v: comp for v in data_vars}

    @staticmethod
    def _create_export_folder(filename):
        """ Create the export folder. """
        folder = os.path.dirname(filename)
        try:
            os.makedirs(folder)
        except OSError:
            pass

    @abc.abstractmethod
    def load_dataset(self):
        """ Load data as an xarray Dataset. """

    def write_netcdf(self, filename=None):
        """ Export data to netCDF.

        Parameters
        ----------
        filename : str, optional
            The name of the exported file. Defaults to
            `<recording_folder>/exports/<datatype>.nc` where `<datatype>` is
            `gaze`, `odometry` etc.
        """
        ds = self.load_dataset()
        encoding = self._get_encoding(ds.data_vars)

        if filename is None:
            filename = os.path.join(
                self.folder, 'exports', self._nc_name + '.nc')

        self._create_export_folder(filename)
        ds.to_netcdf(filename, encoding=encoding)
