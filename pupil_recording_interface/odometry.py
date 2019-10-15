""""""
import os
from collections import deque

import numpy as np
import xarray as xr

from uvc import get_time_monotonic as monotonic

from pupil_recording_interface.base import BaseInterface, BaseRecorder
from pupil_recording_interface.externals.file_methods import PLData_Writer


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


class OdometryRecorder(BaseRecorder):

    def __init__(self, folder, topic='odometry', verbose=False):
        """"""
        try:
            import pyrealsense2 as rs
        except ImportError:
            raise ImportError(
                'You need to install the pyrealsense2 library in order to '
                'use the odometry recorder')

        self.pipeline = rs.pipeline()
        self.config = rs.config()
        self.config.enable_stream(rs.stream.pose)

        self.filename = os.path.join(folder, topic + '.pldata')
        if os.path.exists(self.filename):
            raise IOError(f'{self.filename} exists, will not overwrite')

        self.writer = PLData_Writer(folder, topic)

        super(OdometryRecorder, self).__init__(folder)
        self.verbose = verbose

    @staticmethod
    def get_odometry(pipeline, t_last):
        """"""
        rs_frames = pipeline.wait_for_frames()

        t = monotonic()
        f = 1. / (t - t_last)
        t_last = t

        pose = rs_frames.get_pose_frame()

        c = pose.pose_data.tracker_confidence
        p = pose.pose_data.translation
        q = pose.pose_data.rotation
        v = pose.pose_data.velocity
        w = pose.pose_data.angular_velocity

        return t_last, f, c, \
            (p.x, p.y, p.z), (q.w, q.x, q.y, q.z), \
            (v.x, v.y, v.z), (w.x, w.y, w.z)

    @staticmethod
    def odometry_to_dict(odometry_data):
        """"""
        t, f, c, p, q, v, w = odometry_data
        return {
            'topic': 'odometry', 'timestamp': t, 'confidence': c,
             'position': p, 'orientation': q,
             'linear_velocity': v, 'angular_velocity': w}

    @staticmethod
    def moving_average(value, buffer):
        """"""
        buffer.append(value)
        return sum(buffer) / len(buffer)

    def run(self):
        """"""
        self.pipeline.start(self.config)
        buffer = deque(maxlen=200)

        if self.verbose:
            print(f'Started recording to {self.filename}')

        t = 0
        while True:
            try:
                odometry_data = self.get_odometry(self.pipeline, t)
                t = odometry_data[0]
                if self.verbose:
                    f = self.moving_average(odometry_data[1], buffer)
                    print(f'\rSampling rate: {f:.2f}', end='')
                self.writer.append(
                    self.odometry_to_dict(odometry_data))
            except (KeyboardInterrupt, RuntimeError):
                break

        if self.verbose:
            print('\nStopped recording')

        self.writer.close()
        self.pipeline.stop()
