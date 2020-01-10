""""""
from __future__ import print_function

import os
import warnings
from collections import deque

from pupil_recording_interface.externals.file_methods import PLData_Writer
from pupil_recording_interface.recorder import BaseRecorder


class OdometryRecorder(BaseRecorder):
    """ Recorder for odometry data from the T265 tracking camera. """

    def __init__(self, folder, topic='odometry', verbose=True):
        """ Constructor.

        Parameters
        ----------
        folder : str
            Path to the recording folder.

        topic : str, default 'odometry'
            Name of the topic of the recorded data. Is also used as the file
            name.

        verbose : bool, default True
            If True, display the current sampling rate during recording.
        """
        try:
            import pyrealsense2 as rs
        except ImportError:
            raise ImportError(
                'You need to install the pyrealsense2 library in order to '
                'use the odometry recorder.')

        try:
            import uvc
            self.monotonic = uvc.get_time_monotonic
        except ImportError:
            warnings.warn(
                'pyuvc library not found. Timestamps might not be perfectly '
                'synchronized with gaze and video.')
            from monotonic import monotonic
            self.monotonic = monotonic

        # realsense pipeline
        self.pipeline = rs.pipeline()
        self.config = rs.config()
        self.config.enable_stream(rs.stream.pose)

        # pldata writer
        self.filename = os.path.join(folder, topic + '.pldata')
        if os.path.exists(self.filename):
            raise IOError('{} exists, will not overwrite'.format(
                self.filename))
        self.writer = PLData_Writer(folder, topic)

        super(OdometryRecorder, self).__init__(folder)
        self.verbose = verbose

    @staticmethod
    def _get_odometry(rs_frame, t_last, monotonic):
        """ Get odometry data from realsense pose frame. """
        t = monotonic()
        f = 1. / (t - t_last)

        pose = rs_frame.get_pose_frame()

        c = pose.pose_data.tracker_confidence
        p = pose.pose_data.translation
        q = pose.pose_data.rotation
        v = pose.pose_data.velocity
        w = pose.pose_data.angular_velocity

        return t, f, c, \
            (p.x, p.y, p.z), (q.w, q.x, q.y, q.z), \
            (v.x, v.y, v.z), (w.x, w.y, w.z)

    @staticmethod
    def _odometry_to_dict(odometry_data):
        """ Convert odometry data to dict. """
        t, f, c, p, q, v, w = odometry_data
        return {
            'topic': 'odometry', 'timestamp': t, 'confidence': c,
            'position': p, 'orientation': q,
            'linear_velocity': v, 'angular_velocity': w}

    @staticmethod
    def _moving_average(value, buffer):
        """ Buffer values and compute moving average. """
        buffer.append(value)
        return sum(buffer) / len(buffer)

    def run(self):
        """ Start the recording. """
        self.pipeline.start(self.config)
        buffer = deque(maxlen=200)

        if self.verbose:
            print('Started recording to {}'.format(self.filename))

        t = 0.
        while True:
            try:
                rs_frame = self.pipeline.wait_for_frames()
                odometry_data = self._get_odometry(rs_frame, t, self.monotonic)
                t = odometry_data[0]
                if self.verbose:
                    f = self._moving_average(odometry_data[1], buffer)
                    print('\rSampling rate: {:.2f}'.format(f), end='')
                self.writer.append(self._odometry_to_dict(odometry_data))
            except (KeyboardInterrupt, RuntimeError):
                break

        if self.verbose:
            print('\nStopped recording')

        self.writer.close()
        self.pipeline.stop()
