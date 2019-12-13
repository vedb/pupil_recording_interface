""""""
from __future__ import division

import os

import numpy as np
import pandas as pd
import xarray as xr
import cv2

from pupil_recording_interface.base import BaseInterface
from pupil_recording_interface.errors import FileNotFoundError


def iter_wrapper(it, **kwargs):
    return it


class VideoInterface(BaseInterface):

    def __init__(self, folder, source='world', color_format=None,
                 norm_pos=None, roi_size=None, subsampling=None,
                 interpolation_method='linear', video_offset=0.):
        """"""
        super(VideoInterface, self).__init__(folder, source=source)
        self.color_format = color_format
        self.roi_size = roi_size
        self.subsampling = subsampling

        self.timestamps = self._load_timestamps_as_datetimeindex(
            self.folder, self.source, self.info, video_offset)

        # resample norm pos to video timestamps
        if norm_pos is not None:
            if self.roi_size is None:
                raise ValueError(
                    'roi_size must be specified when norm_pos is specified')
            self.norm_pos = norm_pos.interp(
                {'time': self.timestamps}, method=interpolation_method)
        else:
            self.norm_pos = None

        self.camera_matrix, self.distortion_coefs = self._load_intrinsics(
            self.folder)

        self.capture = self._get_capture(self.folder, source)
        self.resolution = self._get_resolution(self.capture)
        self.frame_count = self._get_frame_count(self.capture)
        self.frame_shape = self.get_frame(0).shape
        self.fps = self._get_fps(self.capture)

    @property
    def nc_name(self):
        return self.source

    @staticmethod
    def _load_intrinsics(folder):
        """"""
        filepath = os.path.join(folder, 'world.intrinsics')
        if not os.path.exists(filepath):
            return None, None
        else:
            # TODO read intrinsics
            return None, None

    @staticmethod
    def _get_capture(folder, topic):
        """"""
        filepath = os.path.join(folder, topic + '.mp4')
        if not os.path.exists(filepath):
            raise FileNotFoundError(
                'File {}.mp4 not found in folder {}'.format(topic, folder))

        return cv2.VideoCapture(filepath)

    @staticmethod
    def _get_resolution(capture):
        """"""
        return (int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
                int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)))

    @staticmethod
    def _get_frame_count(capture):
        """"""
        return int(capture.get(cv2.CAP_PROP_FRAME_COUNT))

    @staticmethod
    def _get_fps(capture):
        """"""
        return capture.get(cv2.CAP_PROP_FPS)

    @staticmethod
    def _get_encoding(data_vars, dtype='int32'):
        """"""
        comp = {
            'zlib': True,
            'dtype': dtype,
            'scale_factor': 0.0001,
            '_FillValue': np.iinfo(dtype).min
        }

        comp_f = {
            'zlib': True,
            'dtype': 'uint8',
        }

        return {v: (comp if v != 'frames' else comp_f) for v in data_vars}

    @staticmethod
    def convert_color(frame, color_format):
        """"""
        if color_format == 'gray':
            return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            raise ValueError(
                'Unsupported color format: {}'.format(color_format))

    def undistort_point(self, point, frame_size):
        """"""
        # TODO test
        u = point[0] * frame_size[1]
        v = (1 - point[1]) * frame_size[0]

        up, vp = np.squeeze(cv2.undistortPoints(
            np.array((u, v))[np.newaxis, np.newaxis, :],
            self.camera_matrix, self.distortion_coefs))

        x = (up + 1) / 2
        y = 1 - ((vp + 1) / 2)

        return x, y

    def undistort_frame(self, frame):
        """"""
        # TODO test
        h, w = frame.shape[:2]
        new_camera_matrix, (rx, ry, rw, rh) = cv2.getOptimalNewCameraMatrix(
            self.camera_matrix, self.distortion_coefs, (w, h), 0, (w, h))
        frame = cv2.undistort(
            frame, self.camera_matrix, self.distortion_coefs,
            newCameraMatrix=new_camera_matrix)

        frame_roi = np.nan * np.ones((h, w))
        frame_roi[ry:ry + rh, rx:rx + rw] = frame[ry:ry + rh, rx:rx + rw]

        return frame_roi

    def subsample_frame(self, frame):
        """"""
        frame = cv2.resize(
            frame, None, fx=1. / self.subsampling,
            fy=1. / self.subsampling, interpolation=cv2.INTER_AREA)

        return frame

    @staticmethod
    def get_valid_idx(norm_pos, frame_shape, roi_size):
        """"""
        norm_pos[:, 0] = norm_pos[:, 0] * frame_shape[1]
        norm_pos[:, 1] = (1 - norm_pos[:, 1]) * frame_shape[0]

        left_lower = norm_pos - roi_size // 2
        right_upper = norm_pos + roi_size // 2

        idx = np.all(left_lower > 0, axis=1) \
            & np.all(right_upper <= frame_shape, axis=1)

        return idx

    @staticmethod
    def get_bounds(p, frame_size, roi_size):
        """"""
        p0 = p - roi_size // 2
        p1 = p + roi_size // 2

        p0_frame = np.clip(p0, 0, frame_size)
        p1_frame = np.clip(p1, 0, frame_size)
        p0_roi = -p0 if p0 < 0 else 0
        p1_roi = frame_size - p0 if p1 >= frame_size else roi_size
        p1_roi = np.clip(p1_roi, 0, roi_size)

        return (p0_roi, p1_roi), (p0_frame, p1_frame)

    @staticmethod
    def get_roi(frame, norm_pos, roi_size):
        """"""
        roi_shape = list(frame.shape)
        roi_shape[:2] = (roi_size, roi_size)
        roi = np.nan * np.ones(roi_shape)

        x, y = norm_pos

        if not np.isnan(x) and not np.isnan(y):
            (x0_roi, x1_roi), (x0_frame, x1_frame) = \
                VideoInterface.get_bounds(
                    int(x * frame.shape[1]), frame.shape[1], roi_size)
            (y0_roi, y1_roi), (y0_frame, y1_frame) = \
                VideoInterface.get_bounds(
                    int((1 - y) * frame.shape[0]), frame.shape[0], roi_size)
            roi[y0_roi:y1_roi, x0_roi:x1_roi, ...] = \
                frame[y0_frame:y1_frame, x0_frame:x1_frame, ...]

        return roi

    @staticmethod
    def frame_as_uint8(frame):
        """"""
        frame[np.isnan(frame)] = 0.
        return frame.astype('uint8')

    def load_timestamps(self):
        """"""
        return self._load_timestamps_as_datetimeindex(
            self.folder, self.source, self.info)

    def process_frame(self, frame, norm_pos=None):
        """"""
        if self.color_format is not None:
            frame = self.convert_color(frame, self.color_format)

        if self.distortion_coefs is not None:
            frame = self.undistort_frame(frame)

        if self.subsampling is not None:
            frame = self.subsample_frame(frame)

        if norm_pos is not None:
            frame = self.get_roi(frame, norm_pos, self.roi_size)

        return frame.astype(float)

    def get_raw_frame(self, idx):
        """"""
        if idx < 0 or idx >= self.frame_count:
            raise ValueError('Frame index out of range')

        self.capture.set(cv2.CAP_PROP_POS_FRAMES, idx)
        _, frame = self.capture.read()

        return frame

    def get_frame(self, idx, return_timestamp=False):
        """"""
        frame = self.get_raw_frame(idx)

        if self.norm_pos is not None:
            norm_pos = self.norm_pos.values[idx]
        else:
            norm_pos = None

        if return_timestamp:
            return (self.timestamps[idx],
                    self.process_frame(frame, norm_pos=norm_pos))
        else:
            return self.process_frame(frame, norm_pos=norm_pos)

    def read_frames(self, start=None, end=None):
        """"""
        start = start or 0
        end = end or self.frame_count

        self.capture.set(cv2.CAP_PROP_POS_FRAMES, start)

        for idx in range(end - start):
            _, frame = self.capture.read()
            if self.norm_pos is not None:
                yield self.process_frame(
                    frame, self.norm_pos.values[idx - start])
            else:
                yield self.process_frame(frame)

    def load_dataset(self, dropna=False):
        """"""
        t = self.timestamps

        if dropna:
            t_gen, flow_gen = zip(
                *((t, f)
                  for t, f in zip(t, self.read_frames())
                  if not np.any(np.isnan(f))))
            t = pd.DatetimeIndex(t_gen)
            frames = np.array(flow_gen)
        else:
            frames = np.empty((t.size,) + self.frame_shape)
            for idx, f in enumerate(self.read_frames()):
                frames[idx] = f

        frames = self.frame_as_uint8(frames)

        dims = ['time', 'frame_y', 'frame_x']

        coords = {
            'time': t.values,
            'frame_x': np.arange(frames.shape[2]),
            'frame_y': np.arange(frames.shape[1]),
        }

        if frames.ndim == 4:
            coords['color'] = ['B', 'G', 'R']
            dims += ['color']

        data_vars = {
            'frames': (dims, frames)
        }

        return xr.Dataset(data_vars, coords)


class OpticalFlowInterface(VideoInterface):

    def __init__(self, folder, source='world', **kwargs):
        """"""
        super(OpticalFlowInterface, self).__init__(
            folder, source=source, color_format='gray', **kwargs)

        self.flow_shape = self.get_optical_flow(0).shape

    @property
    def nc_name(self):
        return 'optical_flow'

    @staticmethod
    def get_valid_idx(norm_pos, frame_shape, roi_size):
        """"""
        idx = VideoInterface.get_valid_idx(norm_pos, frame_shape, roi_size)
        return np.hstack((False, idx[1:] & idx[:-1]))

    @staticmethod
    def calculate_flow(frame, last_frame):
        """"""
        if last_frame is not None:
            # TODO make configurable
            return -cv2.calcOpticalFlowFarneback(
                last_frame, frame, None, pyr_scale=0.5, levels=3, winsize=20,
                iterations=3, poly_n=7, poly_sigma=1.5, flags=0)
        else:
            return np.nan * np.ones(frame.shape + (2,))

    def get_optical_flow(self, idx, return_timestamp=False):
        """"""
        if idx < 0 or idx >= self.frame_count:
            raise ValueError('Frame index out of range')

        if idx == 0:
            last_frame = None
        else:
            last_frame = self.get_frame(idx - 1)

        flow = self.calculate_flow(self.get_frame(idx), last_frame)

        if return_timestamp:
            return self.timestamps[idx], flow
        else:
            return flow

    def estimate_optical_flow(self, start=None, end=None):
        """"""
        last_frame = None
        for frame in self.read_frames(start, end):
            yield self.calculate_flow(frame, last_frame)
            last_frame = frame

    def load_dataset(self, dropna=False, start=None, end=None,
                     iter_wrapper=iter_wrapper):
        """"""
        t = self.timestamps
        ss = self.subsampling or 1.

        if start is not None:
            start = t.get_loc(start, method='nearest')

        if end is not None:
            end = t.get_loc(end, method='nearest')

        t = t[start:end]

        if dropna:
            # TODO fix get_valid_idx to get actual number of samples
            flow = np.empty((t.size,) + self.flow_shape)
            valid_idx = np.zeros(t.size, dtype=bool)
            idx = 0
            for f in iter_wrapper(
                    self.estimate_optical_flow(start, end), total=t.size):
                if not np.any(np.isnan(f)):
                    flow[idx] = f
                    valid_idx[idx] = True
                    idx += 1
            flow = flow[:idx]
            t = t[valid_idx]
        else:
            flow = np.empty((t.size,) + self.flow_shape)
            for idx, f in iter_wrapper(enumerate(
                    self.estimate_optical_flow(start, end)), total=t.size):
                flow[idx] = f

        # ROI coordinate system is centered and y-axis points upwards
        coords = {
            'time': t.values,
            'pixel_axis': ['x', 'y'],
            'roi_x': np.arange(
                -flow.shape[2] / 2 + 0.5, flow.shape[2] / 2 + 0.5) * ss,
            'roi_y': -np.arange(
                -flow.shape[1] / 2 + 0.5, flow.shape[1] / 2 + 0.5) * ss
        }

        data_vars = {
            'optical_flow':
                (['time', 'roi_y', 'roi_x', 'pixel_axis'], flow)
        }

        return xr.Dataset(data_vars, coords)
