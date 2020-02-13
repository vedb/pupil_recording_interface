""""""
import numpy as np
import xarray as xr

from pupil_recording_interface import BaseReader


class OdometryReader(BaseReader):
    """ Reader for odometry data. """

    @property
    def _nc_name(self):
        """ Name of exported netCDF file. """
        return "odometry"

    @staticmethod
    def _load_odometry(folder, topic="odometry"):
        """ Load odometry data from a .pldata file. """
        df = BaseReader._load_pldata_as_dataframe(folder, topic)

        t = df.timestamp
        c = df.confidence
        p = np.array(df.position.to_list())
        q = np.array(df.orientation.to_list())
        v = np.array(df.linear_velocity.to_list())
        w = np.array(df.angular_velocity.to_list())

        return t, c, p, q, v, w

    def load_dataset(self):
        """ Load odometry data as an xarray Dataset.

        Returns
        -------
        xarray.Dataset
            The odometry data as a dataset.
        """
        if self.source == "recording":
            t, c, p, q, v, w = self._load_odometry(self.folder)
        else:
            raise ValueError("Invalid odometry source: {}".format(self.source))

        t = self._timestamps_to_datetimeindex(t, self.info)

        coords = {
            "time": t.values,
            "cartesian_axis": ["x", "y", "z"],
            "quaternion_axis": ["w", "x", "y", "z"],
        }

        data_vars = {
            "tracker_confidence": ("time", c),
            "linear_velocity": (["time", "cartesian_axis"], v),
            "angular_velocity": (["time", "cartesian_axis"], w),
            "linear_position": (["time", "cartesian_axis"], p),
            "angular_position": (["time", "quaternion_axis"], q),
        }

        return xr.Dataset(data_vars, coords)
