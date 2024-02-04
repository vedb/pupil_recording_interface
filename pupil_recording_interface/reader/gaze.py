""""""
import numpy as np
import pandas as pd
import xarray as xr
from msgpack import Unpacker

from pupil_recording_interface.reader import BaseReader


class GazeReader(BaseReader):
    """ Reader for gaze data. """

    def __init__(self, folder, source="recording"):
        """ Constructor.

        Parameters
        ----------
        folder : str or pathlib.Path
            Path to the recording folder.

        source : str or dict, default 'recording'
            The source of the data. If 'recording', the recorded data will
            be used. Can also be the name of a gaze mapper or a dict in the
            format ``{'2d': '<2d_gaze_mapper>', '3d': '<3d_gaze_mapper>'}`` in
            which case the norm pos from the 2d mapper and the gaze point
            from the 3d mapper will be used.
        """
        super().__init__(folder)

        self.source = source
        try:
            self.gaze_mappers = self._get_offline_gaze_mappers(self.folder)
        except FileNotFoundError:
            self.gaze_mappers = {}

    @property
    def export_name(self):
        """ Name of exported files. """
        return "gaze"

    @staticmethod
    def _extract_gaze_data(df):
        """ Extract gaze data from DataFrame"""
        data = {
            "timestamp": df.timestamp,
            "confidence": df.confidence,
            "norm_pos": np.array(df.norm_pos.to_list()),
            "eye": np.zeros(df.timestamp.shape, dtype=int),
        }

        data["eye"][df.topic.str.endswith(".1.")] = 1
        data["eye"][df.topic.str.endswith(".01.")] = 2

        if "gaze_point_3d" in df.columns:
            # get 3d gaze point
            p = np.nan * np.ones(df.timestamp.shape + (3,))
            valid_idx = df.gaze_point_3d.apply(lambda x: isinstance(x, tuple))
            p[valid_idx, :] = np.array(df.gaze_point_3d[valid_idx].to_list())
            data["gaze_point"] = p / 1000.0

            # get indexes of binocular and monocular eye centers/normals
            if "eye_centers_3d" in df.columns:
                bin_idx = df.eye_centers_3d.apply(
                    lambda x: isinstance(x, dict)
                )
            else:
                bin_idx = np.zeros(df.shape[0], dtype=bool)
            if "eye_center_3d" in df.columns:
                mon_idx = df.eye_center_3d.apply(
                    lambda x: isinstance(x, tuple)
                )
                mon0_idx = mon_idx & (data["eye"] == 0)
                mon1_idx = mon_idx & (data["eye"] == 1)
            else:
                mon0_idx = np.zeros(df.shape[0], dtype=bool)
                mon1_idx = np.zeros(df.shape[0], dtype=bool)
            assert not (bin_idx & mon0_idx).any()
            assert not (bin_idx & mon1_idx).any()

            # merge monocular and binocular eye centers
            df_c = pd.DataFrame(df.eye_centers_3d[bin_idx].to_list())
            c0 = np.nan * np.ones(df.timestamp.shape + (3,))
            c0[bin_idx, :] = np.array(df_c.iloc[:, 0].to_list())
            if "eye_center_3d" in df.columns:
                c0[mon0_idx, :] = np.array(
                    df.eye_center_3d[mon0_idx].to_list()
                )
            data["eye0_center"] = c0 / 1000.0
            c1 = np.nan * np.ones(df.timestamp.shape + (3,))
            c1[bin_idx, :] = np.array(df_c.iloc[:, 1].to_list())
            if "eye_center_3d" in df.columns:
                c1[mon1_idx, :] = np.array(
                    df.eye_center_3d[mon1_idx].to_list()
                )
            data["eye1_center"] = c1 / 1000.0

            # merge monocular and binocular gaze normals
            df_n = pd.DataFrame(df.gaze_normals_3d[bin_idx].to_list())
            n0 = np.nan * np.ones(df.timestamp.shape + (3,))
            n0[bin_idx, :] = np.array(df_n.iloc[:, 0].to_list())
            if "eye_normal_3d" in df.columns:
                n0[mon0_idx, :] = np.array(
                    df.gaze_normal_3d[mon0_idx].to_list()
                )
            data["eye0_normal"] = n0
            n1 = np.nan * np.ones(df.timestamp.shape + (3,))
            n1[bin_idx, :] = np.array(df_n.iloc[:, 1].to_list())
            if "eye_normal_3d" in df.columns:
                n1[mon1_idx, :] = np.array(
                    df.gaze_normal_3d[mon1_idx].to_list()
                )
            data["eye1_normal"] = n1

        return data

    @staticmethod
    def _load_gaze(folder, topic="gaze"):
        """ Load gaze data from a .pldata file. """
        df = BaseReader._load_pldata_as_dataframe(folder, topic)

        if df.size == 0:
            raise ValueError(f"No gaze data in {folder / (topic + '.pldata')}")

        return GazeReader._extract_gaze_data(df)

    @staticmethod
    def _merge_2d_3d_gaze(gaze_2d, gaze_3d):
        """ Merge data from a 2d and a 3d gaze mapper. """
        t, idx_2d, idx_3d = np.intersect1d(
            gaze_2d["timestamp"], gaze_3d["timestamp"], return_indices=True
        )

        data = {
            "timestamp": t,
            "confidence_2d": gaze_2d["confidence"][idx_2d],
            "confidence_3d": gaze_3d["confidence"][idx_3d],
            "norm_pos": gaze_2d["norm_pos"][idx_2d],
        }

        for key in set(gaze_3d) - {"timestamp", "confidence", "norm_pos"}:
            data[key] = gaze_3d[key][idx_3d]

        return data

    @staticmethod
    def _get_offline_gaze_mappers(folder):
        """ Get the topic names of all offline gaze mappers. """
        filepath = folder / "offline_data" / "gaze_mappers.msgpack"

        if not filepath.exists():
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

        mapper_folder = folder / "offline_data" / "gaze-mappings"
        gaze_2d = GazeReader._load_gaze(
            mapper_folder, offline_mappers[gaze_mapper["2d"]]
        )
        gaze_3d = GazeReader._load_gaze(
            mapper_folder, offline_mappers[gaze_mapper["3d"]]
        )

        return GazeReader._merge_2d_3d_gaze(gaze_2d, gaze_3d)

    @staticmethod
    def _create_dataset(data, info):
        """ Create dataset from gaze data. """
        t = GazeReader._timestamps_to_datetimeindex(data["timestamp"], info)

        coords = {
            "time": t.values,
            "pixel_axis": ["x", "y"],
        }

        data_vars = {
            "eye": ("time", data["eye"]),
            "gaze_norm_pos": (["time", "pixel_axis"], data["norm_pos"]),
        }

        # gaze point, centers and normals only available from 3d mapper
        if "gaze_point" in data:
            coords["cartesian_axis"] = ["x", "y", "z"]
            data_vars.update(
                {
                    key: (["time", "cartesian_axis"], data[key])
                    for key in (
                        "gaze_point",
                        "eye0_center",
                        "eye1_center",
                        "eye0_normal",
                        "eye1_normal",
                    )
                }
            )

        # two confidence values from merged 2d/3d gaze
        if "confidence_2d" in data:
            data_vars["gaze_confidence_2d"] = ("time", data["confidence_2d"])
        if "confidence_3d" in data:
            data_vars["gaze_confidence_3d"] = ("time", data["confidence_3d"])
        if "confidence" in data:
            if "gaze_point" not in data:
                data_vars["gaze_confidence_2d"] = ("time", data["confidence"])
            else:
                data_vars["gaze_confidence_3d"] = ("time", data["confidence"])

        ds = xr.Dataset(data_vars, coords)

        # sort and remove duplicate samples
        ds.sortby("time")
        _, index = np.unique(ds["time"], return_index=True)
        ds = ds.isel(time=index)

        return ds

    @staticmethod
    def _dataset_from_list(gaze_list, info):
        """ Create dataset from list of dicts. """
        df = pd.DataFrame(gaze_list)
        data = GazeReader._extract_gaze_data(df)
        ds = GazeReader._create_dataset(data, info)

        return ds

    def load_dataset(self):
        """ Load gaze data as an xarray Dataset.

        Returns
        -------
        xarray.Dataset
            The gaze data as a dataset.
        """
        if self.source == "recording":
            data = self._load_gaze(self.folder)
        elif isinstance(self.source, str) and self.source in self.gaze_mappers:
            data = self._load_gaze(
                self.folder / "offline_data" / "gaze-mappings",
                self.gaze_mappers[self.source],
            )
        elif isinstance(self.source, dict) and set(self.source.keys()) == {
            "2d",
            "3d",
        }:
            data = self._load_merged_gaze(self.folder, self.source)
        else:
            raise ValueError(f"Invalid gaze source: {self.source}")

        ds = self._create_dataset(data, self.info)

        return ds
