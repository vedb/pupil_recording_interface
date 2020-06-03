""""""
import numpy as np
import pandas as pd
import xarray as xr

from pupil_recording_interface import BaseReader


class MotionReader(BaseReader):
    """ Reader for odometry data. """

    def __init__(self, folder, stream="odometry", source="recording"):
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
        super().__init__(folder)

        self.stream = stream
        self.source = source

    @property
    def export_name(self):
        """ Name of exported files. """
        return self.stream

    @staticmethod
    def _load_data(folder, topic="odometry"):
        """ Load odometry data from a .pldata file. """
        df = BaseReader._load_pldata_as_dataframe(folder, topic)

        data = {}
        if hasattr(df, "source_timestamp"):
            data["timestamp"] = df.source_timestamp
            data["timebase"] = "epoch"
        elif hasattr(df, "rs_timestamp"):
            data["timestamp"] = df.rs_timestamp
            data["timebase"] = "epoch"
        else:
            data["timestamp"] = df.timestamp
            data["timebase"] = "monotonic"

        for key in (
            "position",
            "orientation",
            "linear_velocity",
            "angular_velocity",
            "linear_acceleration",
            "angular_acceleration",
        ):
            if hasattr(df, key):
                data[key] = np.array(df[key].to_list())

        if hasattr(df, "confidence"):
            data["confidence"] = df.confidence
        elif hasattr(df, "tracker_confidence"):
            data["confidence"] = df.tracker_confidence

        return data

    def load_dataset(self):
        """ Load motion data as an xarray Dataset.

        Returns
        -------
        xarray.Dataset
            The motion data as a dataset.
        """
        if self.source == "recording":
            data = self._load_data(self.folder, self.stream)
        else:
            raise ValueError(f"Invalid {self.stream} source: {self.source}")

        if data["timebase"] == "monotonic":
            t = self._timestamps_to_datetimeindex(data["timestamp"], self.info)
        else:
            t = pd.to_datetime(data["timestamp"], unit="s")

        coords = {
            "time": t.values,
            "cartesian_axis": ["x", "y", "z"],
        }

        data_vars = {}

        for key in (
            "position",
            "linear_velocity",
            "angular_velocity",
            "linear_acceleration",
            "angular_acceleration",
        ):
            if key in data:
                data_vars[key] = (["time", "cartesian_axis"], data[key])

        if "confidence" in data:
            data_vars["confidence"] = ("time", data["confidence"])

        if "orientation" in data:
            coords["quaternion_axis"] = ["w", "x", "y", "z"]
            data_vars["orientation"] = (
                ["time", "quaternion_axis"],
                data["orientation"],
            )

        return xr.Dataset(data_vars, coords)
