""""""
import os

import numpy as np
import xarray as xr
from msgpack import Unpacker

from pupil_recording_interface import BaseReader
from pupil_recording_interface.errors import FileNotFoundError


class GazeReader(BaseReader):
    """ Reader for gaze data. """

    def __init__(self, folder, source="recording"):
        """ Constructor.

        Parameters
        ----------
        folder : str
            Path to the recording folder.

        source : str or dict, default 'recording'
            The source of the data. If 'recording', the recorded data will
            be used. Can also be the name of a gaze mapper or a dict in the
            format ``{'2d': '<2d_gaze_mapper>', '3d': '<3d_gaze_mapper>'}`` in
            which case the norm pos from the 2d mapper and the gaze point
            from the 3d mapper will be used.
        """
        super(GazeReader, self).__init__(folder, source=source)
        self.gaze_mappers = self._get_offline_gaze_mappers(self.folder)

    @property
    def _nc_name(self):
        """ Name of exported netCDF file. """
        return "gaze"

    @staticmethod
    def _load_gaze(folder, topic="gaze"):
        """ Load gaze data from a .pldata file. """
        df = BaseReader._load_pldata_as_dataframe(folder, topic)

        if df.size == 0:
            raise ValueError(
                "No gaze data in {}".format(
                    os.path.join(folder, topic + ".pldata")
                )
            )

        t = df.timestamp
        c = df.confidence
        n = np.array(df.norm_pos.to_list())

        if "gaze_point_3d" not in df.columns:
            p = None
        else:
            p = np.nan * np.ones(t.shape + (3,))
            idx_notnan = df.gaze_point_3d.apply(lambda x: isinstance(x, tuple))
            p[idx_notnan, :] = np.array(df.gaze_point_3d[idx_notnan].to_list())
            p /= 1000.0

        return t, c, n, p

    @staticmethod
    def _merge_2d_3d_gaze(gaze_2d, gaze_3d):
        """ Merge data from a 2d and a 3d gaze mapper. """
        t, idx_2d, idx_3d = np.intersect1d(
            gaze_2d[0], gaze_3d[0], return_indices=True
        )

        return (
            t,
            (gaze_2d[1][idx_2d], gaze_3d[1][idx_3d]),
            gaze_2d[2][idx_2d],
            gaze_3d[3][idx_3d],
        )

    @staticmethod
    def _get_offline_gaze_mappers(folder):
        """ Get the topic names of all offline gaze mappers. """
        filepath = os.path.join(folder, "offline_data", "gaze_mappers.msgpack")

        if not os.path.exists(filepath):
            raise FileNotFoundError("No offline gaze mappers found")

        with open(filepath, "rb") as f:
            gm_data = Unpacker(f, use_list=False).unpack()[b"data"]

        def get_topic(name, urn):
            return name.decode().replace(" ", "_") + "-" + urn.decode()

        return {g[1].decode(): get_topic(g[1], g[0]) for g in gm_data}

    @staticmethod
    def _load_merged_gaze(folder, gaze_mapper):
        """ Load and merge gaze from different mappers (2d and 3d). """
        offline_mappers = GazeReader._get_offline_gaze_mappers(folder)

        mapper_folder = os.path.join(folder, "offline_data", "gaze-mappings")
        gaze_2d = GazeReader._load_gaze(
            mapper_folder, offline_mappers[gaze_mapper["2d"]]
        )
        gaze_3d = GazeReader._load_gaze(
            mapper_folder, offline_mappers[gaze_mapper["3d"]]
        )

        return GazeReader._merge_2d_3d_gaze(gaze_2d, gaze_3d)

    def load_dataset(self):
        """ Load gaze data as an xarray Dataset.

        Returns
        -------
        xarray.Dataset
            The gaze data as a dataset.
        """
        if self.source == "recording":
            t, c, n, p = self._load_gaze(self.folder)
        elif isinstance(self.source, str) and self.source in self.gaze_mappers:
            t, c, n, p = self._load_gaze(
                os.path.join(self.folder, "offline_data", "gaze-mappings"),
                self.gaze_mappers[self.source],
            )
        elif isinstance(self.source, dict) and set(self.source.keys()) == {
            "2d",
            "3d",
        }:
            t, c, n, p = self._load_merged_gaze(self.folder, self.source)
        else:
            raise ValueError("Invalid gaze source: {}".format(self.source))

        t = self._timestamps_to_datetimeindex(t, self.info)

        coords = {
            "time": t.values,
            "pixel_axis": ["x", "y"],
        }

        data_vars = {
            "gaze_norm_pos": (["time", "pixel_axis"], n),
        }

        # gaze point only available from 3d mapper
        if p is not None:
            coords["cartesian_axis"] = ["x", "y", "z"]
            data_vars["gaze_point"] = (["time", "cartesian_axis"], p)

        # two confidence values from merged 2d/3d gaze
        if isinstance(c, tuple):
            assert len(c) == 2
            data_vars["gaze_confidence_2d"] = ("time", c[0])
            data_vars["gaze_confidence_3d"] = ("time", c[1])
        elif p is None:
            data_vars["gaze_confidence_2d"] = ("time", c)
        else:
            data_vars["gaze_confidence_3d"] = ("time", c)

        ds = xr.Dataset(data_vars, coords)

        # sort and remove duplicate samples
        ds.sortby("time")
        _, index = np.unique(ds["time"], return_index=True)
        ds = ds.isel(time=index)

        return ds
