""""""
import numpy as np
import xarray as xr

from pupil_recording_interface.base import BaseInterface


class OdometryInterface(BaseInterface):

    @property
    def nc_name(self):
        return 'odometry'

    @staticmethod
    def _load_odometry(folder, topic='odometry'):
        """"""
        df = BaseInterface._load_pldata_as_dataframe(folder, topic)

        t = df.timestamp
        c = df.confidence
        p = np.array(df.position.to_list())
        q = np.array(df.orientation.to_list())
        v = np.array(df.linear_velocity.to_list())
        w = np.array(df.angular_velocity.to_list())

        return t, c, p, q, v, w

    def load_dataset(self):
        """"""
        if self.source == 'recording':
            t, c, p, q, v, w = self._load_odometry(self.folder)
        else:
            raise ValueError(f'Invalid odometry source: {self.source}')

        t = self._timestamps_to_datetimeindex(t, self.info)

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
