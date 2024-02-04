""""""
import abc
import csv
import hashlib
import json
import collections
from pathlib import Path
import logging

import numpy as np
import pandas as pd
import msgpack

from pupil_recording_interface.externals.file_methods import PLData_Writer

logger = logging.getLogger(__name__)


class Unpacker:
    MSGPACK_EXT_CODE = 13

    @classmethod
    def unpack(cls, payload):
        """"""
        return msgpack.unpackb(
            payload,
            raw=False,
            use_list=False,
            object_hook=cls.unpacking_object_hook,
            ext_hook=cls.unpacking_ext_hook,
        )

    @classmethod
    def unpacking_object_hook(cls, obj):
        if isinstance(obj, dict):
            return obj

    @classmethod
    def unpacking_ext_hook(cls, code, data):
        if code == cls.MSGPACK_EXT_CODE:
            return cls.unpack(data)
        return msgpack.ExtType(code, data)


class BaseReader:
    """ Base class for all readers. """

    def __init__(self, folder):
        """ Constructor.

        Parameters
        ----------
        folder : str or pathlib.Path
            Path to the recording folder.
        """
        folder = Path(folder).expanduser()
        if not folder.exists():
            raise FileNotFoundError(f"No such folder: {folder}")

        self.folder = folder

        if (self.folder / "info.csv").exists():
            self.info = self._load_info(self.folder, "info.csv")
        else:
            self.info = self._load_info(self.folder)

        try:
            self.user_info = self._load_user_info(
                self.folder, self.info["start_time_system_s"]
            )
        except FileNotFoundError:
            self.user_info = {}

    @property
    @abc.abstractmethod
    def export_name(self):
        """ Name of exported files. """

    @staticmethod
    def _load_legacy_info(file_handle):
        """ Load recording info from legacy file as dict. """
        reader = csv.reader(file_handle)
        info = {rows[0]: rows[1] for rows in reader}

        info = {
            "duration_s": sum(
                float(x) * 60 ** i
                for i, x in enumerate(
                    reversed(info["Duration Time"].split(":"))
                )
            ),
            "meta_version": "2.0",
            "min_player_version": info["Data Format Version"],
            "recording_name": info["Recording Name"],
            "recording_software_name": "Pupil Capture",
            "recording_software_version": info["Capture Software Version"],
            "recording_uuid": info["Recording UUID"],
            "start_time_synced_s": float(info["Start Time (Synced)"]),
            "start_time_system_s": float(info["Start Time (System)"]),
            "system_info": info["System Info"],
        }

        return info

    @staticmethod
    def _load_info(folder, filename="info.player.json"):
        """ Load recording info file as dict. """
        if not (folder / filename).exists():
            raise FileNotFoundError(
                f"File {filename} not found in folder {folder}"
            )

        with open(folder / filename) as f:
            if filename.endswith(".json"):
                info = json.load(f)
            elif filename.endswith(".csv"):
                info = BaseReader._load_legacy_info(f)
            else:
                raise ValueError("Unsupported info file type.")

        return info

    @staticmethod
    def _load_user_info(folder, start_time, filename="user_info.csv"):
        """ Load data from user_info.csv file as dict. """
        if not (folder / filename).exists():
            raise FileNotFoundError(
                f"File {filename} not found in folder {folder}"
            )

        with open(folder / filename) as f:
            reader = csv.reader(f)
            info = {
                rows[0]: rows[1]
                for rows in reader
                if len(rows) >= 2 and rows[0] != "key"
            }

        for k, v in info.items():
            if k.endswith(("start", "end")):
                info[k] = pd.to_timedelta(v) + pd.to_datetime(
                    start_time, unit="s"
                )
            elif k == "height":
                info[k] = float(v) / 100.0

        return info

    @classmethod
    def _load_pldata(cls, folder, topic):
        """ Load data from a .pldata file. """
        msgpack_file = folder / f"{topic}.pldata"
        if not msgpack_file.exists():
            raise FileNotFoundError(
                f"File {topic}.pldata not found in folder {folder}"
            )

        data = collections.deque()
        with open(msgpack_file, "rb") as fh:
            for topic, payload in msgpack.Unpacker(
                fh, raw=False, use_list=False
            ):
                try:
                    data.append(Unpacker.unpack(payload))
                except TypeError:
                    # can happen when recording is broken
                    logger.warning("Found corrupt data while unpacking.")
                    continue

        return list(data)

    @classmethod
    def _save_pldata(cls, folder, topic, data):
        """ Save data as a .pldata file. """
        with PLData_Writer(folder, topic) as writer:
            for datum in data:
                writer.append(datum)

    @classmethod
    def _load_pldata_as_dataframe(cls, folder, topic):
        """ Load data from a .pldata file into a pandas.DataFrame. """
        return pd.DataFrame(cls._load_pldata(folder, topic))

    @classmethod
    def _timestamps_to_datetimeindex(cls, timestamps, info):
        """ Convert timestamps from float to pandas.DatetimeIndex. """
        return pd.to_datetime(
            timestamps
            - info["start_time_synced_s"]
            + info["start_time_system_s"],
            unit="s",
        )

    @classmethod
    def _load_timestamps_from_pldata(cls, folder, topic, offset):
        """"""
        df = cls._load_pldata_as_dataframe(folder, topic)
        return pd.to_datetime(df.source_timestamp.values + offset, unit="s")

    @classmethod
    def _load_timestamps_as_datetimeindex(
        cls, folder, topic, info, offset=0.0, use_pldata=None
    ):
        """ Load timestamps as pandas.DatetimeIndex. """
        if use_pldata is not False:
            try:
                return cls._load_timestamps_from_pldata(folder, topic, offset)
            except (FileNotFoundError, AttributeError):
                if use_pldata:
                    raise

        filepath = folder / f"{topic}_timestamps.npy"
        if not filepath.exists():
            raise FileNotFoundError(
                f"File {topic}_timestamps.npy not found in folder {folder}"
            )

        timestamps = np.load(filepath)
        idx = cls._timestamps_to_datetimeindex(timestamps, info)

        return idx + pd.to_timedelta(offset, unit="s")

    @staticmethod
    def _get_encoding(data_vars, dtype="int32"):
        """ Get encoding for each data var in the netCDF export. """
        comp = {
            "zlib": True,
            "dtype": dtype,
            "scale_factor": 0.0001,
            "_FillValue": np.iinfo(dtype).min,
        }

        return {v: comp for v in data_vars}

    def load_pldata(self, topic):
        """ Load data from a .pldata file as a list of dicts.

        Parameters
        ----------
        topic : str
            The topic to load, e.g. "gaze".

        Returns
        -------
        data : list of dict
            The loaded data.
        """
        return self._load_pldata(self.folder, topic)

    def save_pldata(self, topic, data):
        """ Save data from a list of dicts as a .pldata file.

        Parameters
        ----------
        topic : str
            The topic to save, e.g. "gaze".

        data : list of dict
            The data to be saved.
        """
        self._save_pldata(self.folder, topic, data)

    @abc.abstractmethod
    def load_dataset(self):
        """ Load data as an xarray Dataset. """

    def write_netcdf(self, filename=None):
        """ Export data to netCDF.

        Parameters
        ----------
        filename : path-like, optional
            The name of the exported file. Defaults to
            ``<recording_folder>/exports/<no>/<datatype>.nc`` where
            ``<datatype>`` is `gaze`, `odometry` etc.
        """
        ds = self.load_dataset()
        encoding = self._get_encoding(ds.data_vars)

        if filename is None:
            folder = self.folder / "exports"
            counter = 0
            while (folder / f"{counter:03d}").exists():
                counter += 1
            folder = folder / f"{counter:03d}"
            filename = folder / f"{self.export_name}.nc"

        filename.parent.mkdir(parents=True, exist_ok=True)
        ds.to_netcdf(filename, encoding=encoding)


def _compute_hash(*args):
    """ Compute hash from an argument list. """
    m = hashlib.new("ripemd160")
    m.update(str(args).encode("utf-8"))

    return m.hexdigest()


def _load_dataset(folder, topic, source, method, cache):
    """ Load a single (cached) dataset. """
    import xarray as xr
    from .gaze import GazeReader
    from .motion import MotionReader
    from .pupil import PupilReader
    from .marker import MarkerReader

    if topic == "gaze":
        reader = GazeReader(folder, source=source)
    elif topic == "pupil":
        reader = PupilReader(folder, source=source, method=method)
    elif topic == "marker":
        reader = MarkerReader(folder)
    elif topic in ("odometry", "accel", "gyro"):
        reader = MotionReader(folder, stream=topic, source=source)
    else:
        raise ValueError(f"Unsupported topic {topic}")

    if cache:
        if method is None:
            filepath = folder / "cache" / f"{topic}-{_compute_hash(source)}.nc"
        else:
            filepath = (
                folder
                / "cache"
                / f"{topic}-{_compute_hash(source)}-{method}.nc"
            )
        if not filepath.exists():
            reader.write_netcdf(filename=filepath)
        return xr.open_dataset(filepath)
    else:
        return reader.load_dataset()
