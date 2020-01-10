import os

import cv2
import numpy as np
import pandas as pd
import xarray as xr

from pupil_recording_interface import BaseReader


def _iter_wrapper(it, **kwargs):
    """ Dummy iter wrapper. """
    return it


class VideoReader(BaseReader):
    """ Reader for video data. """

    def __init__(self, folder, source='world', color_format=None,
                 norm_pos=None, roi_size=None, interpolation_method='linear',
                 video_offset=0., subsampling=None):
        """ Constructor.

        Parameters
        ----------
        folder : str
            Path to the recording folder.

        source : str, default 'world'
            The source of the data. If 'recording', the recorded data will
            be used.

        color_format : str, optional
            If 'gray', convert video frames to grayscale.

        norm_pos : xarray DataArray, optional
            If specified, extract an ROI around the norm pos for each frame.
            The DataArray must contain a coordinate named 'time' with the
            timestamps which will be used to match the timestamps of the video
            frames. The parameter `roi_size` must also be specified.

        roi_size : int, optional
            The size of the ROI in pixels (see `norm_pos`).

        interpolation_method : str, default 'linear'
            Interpolation method for matching norm pos timestamps with video
            timestamps (See `norm_pos`).

        video_offset : float, default 0.
            The offset of the video frames wrt to their recorded timestamps.
            It might be necessary to adjust this in order to fix
            synchronization issues between norm pos timestamps and video
            timestamps (see `norm_pos`).

        subsampling : float, optional
            If specified, sub-sample each frame by this factor. Sub-sampling
            is applied before ROI extraction.
        """
        super(VideoReader, self).__init__(folder, source=source)
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
        self.frame_shape = self.load_frame(0).shape
        self.fps = self._get_fps(self.capture)

    @property
    def _nc_name(self):
        """ Name of exported netCDF file. """
        return self.source

    @property
    def video_info(self):
        """ Video metadata. """
        return {
            'resolution': self.resolution,
            'frame_count': self.frame_count,
            'fps': np.round(self.fps, 3)
        }

    @staticmethod
    def _load_intrinsics(folder):
        """ Load world camera intrinsics. """
        filepath = os.path.join(folder, 'world.intrinsics')
        if not os.path.exists(filepath):
            return None, None
        else:
            # TODO read intrinsics
            return None, None

    @staticmethod
    def _get_capture(folder, topic):
        """ Get a cv2.VideoCapture for the video file. """
        filepath = os.path.join(folder, topic + '.mp4')
        if not os.path.exists(filepath):
            raise FileNotFoundError(
                'File {}.mp4 not found in folder {}'.format(topic, folder))

        return cv2.VideoCapture(filepath)

    @staticmethod
    def _get_resolution(capture):
        """ Get the resolution of the video file. """
        return (int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
                int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)))

    @staticmethod
    def _get_frame_count(capture):
        """ Get the frame count of the video file. """
        return int(capture.get(cv2.CAP_PROP_FRAME_COUNT))

    @staticmethod
    def _get_fps(capture):
        """ Get the FPS of the video file. """
        return capture.get(cv2.CAP_PROP_FPS)

    @staticmethod
    def _get_encoding(data_vars, dtype='int32'):
        """ Get encoding for each data var in the netCDF export. """
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
    def _get_valid_idx(norm_pos, frame_shape, roi_size):
        """ Get idx of norm_pos where all ROI pixels are inside the frame. """
        # TODO split into module-level function and instance method
        norm_pos[:, 0] = norm_pos[:, 0] * frame_shape[1]
        norm_pos[:, 1] = (1 - norm_pos[:, 1]) * frame_shape[0]

        left_lower = norm_pos - roi_size // 2
        right_upper = norm_pos + roi_size // 2

        idx = np.all(left_lower > 0, axis=1) \
            & np.all(right_upper <= frame_shape, axis=1)

        return idx

    @staticmethod
    def _get_bounds(p, frame_size, roi_size):
        """ Get bounds of valid ranges for frame and ROI. """
        p0 = p - roi_size // 2
        p1 = p + roi_size // 2

        p0_frame = np.clip(p0, 0, frame_size)
        p1_frame = np.clip(p1, 0, frame_size)
        p0_roi = -p0 if p0 < 0 else 0
        p1_roi = frame_size - p0 if p1 >= frame_size else roi_size
        p1_roi = np.clip(p1_roi, 0, roi_size)

        return (p0_roi, p1_roi), (p0_frame, p1_frame)

    @staticmethod
    def convert_to_uint8(frame):
        """ Convert a video frame to uint8 dtype.

        Parameters
        ----------
        frame : numpy.ndarray
            The frame to convert.

        Returns
        -------
        numpy.ndarray
            The converted frame.
        """
        # TODO rename to convert_range or similar?
        frame *= 255.
        frame[np.isnan(frame)] = 0.
        return frame.astype('uint8')

    def convert_color(self, frame):
        """ Convert color format of a video frame.

        Parameters
        ----------
        frame : numpy.ndarray
            The frame to convert.

        Returns
        -------
        numpy.ndarray
            The converted frame.
        """
        if self.color_format == 'gray':
            return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            raise ValueError(
                'Unsupported color format: {}'.format(self.color_format))

    def get_roi(self, frame, norm_pos):
        """ Extract the ROI from a video frame.

        Parameters
        ----------
        frame : numpy.ndarray
            The input frame.

        norm_pos : iterable, len 2
            The norm pos of the ROI center.

        Returns
        -------
        numpy.ndarray
            The extracted ROI.
        """
        roi_shape = list(frame.shape)
        roi_shape[:2] = (self.roi_size, self.roi_size)
        roi = np.nan * np.ones(roi_shape)

        x, y = norm_pos

        if not np.isnan(x) and not np.isnan(y):
            (x0_roi, x1_roi), (x0_frame, x1_frame) = \
                VideoReader._get_bounds(
                    int(x * frame.shape[1]), frame.shape[1], self.roi_size)
            (y0_roi, y1_roi), (y0_frame, y1_frame) = \
                VideoReader._get_bounds(
                    int((1 - y) * frame.shape[0]), frame.shape[0],
                    self.roi_size)
            roi[y0_roi:y1_roi, x0_roi:x1_roi, ...] = \
                frame[y0_frame:y1_frame, x0_frame:x1_frame, ...]

        return roi

    def undistort_point(self, point):
        """ Un-distort a two-dimensional point.

        Parameters
        ----------
        point : iterable, len 2
            The distorted point.

        Returns
        -------
        tuple
            The undistorted point.
        """
        # TODO test
        frame_size = self.frame_shape[:2]
        u = point[0] * frame_size[1]
        v = (1 - point[1]) * frame_size[0]

        up, vp = np.squeeze(cv2.undistortPoints(
            np.array((u, v))[np.newaxis, np.newaxis, :],
            self.camera_matrix, self.distortion_coefs))

        x = (up + 1) / 2
        y = 1 - ((vp + 1) / 2)

        return x, y

    def undistort_frame(self, frame):
        """ Un-distort a video frame.

        Parameters
        ----------
        frame : numpy.ndarray
            The distorted frame.

        Returns
        -------
        numpy.ndarray
            The undistorted frame.
        """
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
        """ Sub-sample a video frame.

        Parameters
        ----------
        frame : numpy.ndarray
            The input frame.

        Returns
        -------
        numpy.ndarray
            The sub-sampled frame.
        """
        frame = cv2.resize(
            frame, None, fx=1. / self.subsampling,
            fy=1. / self.subsampling, interpolation=cv2.INTER_AREA)

        return frame

    def load_timestamps(self):
        """ Load the timestamps for the video file.

        Returns
        -------
        pandas.DatetimeIndex
            The timestamps for each frame.
        """
        return self._load_timestamps_as_datetimeindex(
            self.folder, self.source, self.info)

    def process_frame(self, frame, norm_pos=None):
        """ Process a video frame.

        Processing includes color conversion, un-distortion, sub-sampling
        and ROI extraction, provided that the corresponding parameters have
        been specified for this instance.

        Parameters
        ----------
        frame : numpy.ndarray
            The input frame.

        norm_pos : iterable, len 2, optional
            The norm pos of the ROI center. If not specified, no ROI
            extraction will be performed.

        Returns
        -------
        numpy.ndarray
            The processed frame.
        """
        if self.color_format is not None:
            frame = self.convert_color(frame)

        if self.distortion_coefs is not None:
            frame = self.undistort_frame(frame)

        if self.subsampling is not None:
            frame = self.subsample_frame(frame)

        if norm_pos is not None:
            frame = self.get_roi(frame, norm_pos)

        return frame.astype(float) / 255.

    def load_raw_frame(self, idx):
        """ Load a single un-processed video frame.

        Parameters
        ----------
        idx : int
            The index of the frame

        Returns
        -------
        numpy.ndarray
            The loaded frame.
        """
        if idx < 0 or idx >= self.frame_count:
            raise ValueError('Frame index out of range')

        self.capture.set(cv2.CAP_PROP_POS_FRAMES, idx)
        _, frame = self.capture.read()

        return frame

    def load_frame(self, idx, return_timestamp=False):
        """ Load a single processed video frame,

        Parameters
        ----------
        idx : int
            The index of the frame

        return_timestamp : bool, default False
            If True, also return the timestamp of the frame.

        Returns
        -------
        frame: numpy.ndarray
            The loaded frame.

        timestamp: Timestamp
            The timestamp of the frame.
        """
        frame = self.load_raw_frame(idx)

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
        """ Generator for processed frames.

        Parameters
        ----------
        start : int, optional
            If specified, start the generator at this frame index.

        end : int, optional
            If specified, stop the generator at this frame index.

        Yields
        -------
        numpy.ndarray
            The loaded frame.
        """
        # TODO accept timestamps for start and end
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

    def load_dataset(self, dropna=False, start=None, end=None):
        """ Load video data as an xarray Dataset

        Parameters
        ----------
        dropna : bool, default False
            If True, drop all frames containing NaN values. This can happen
            with ROI extraction when the ROI is (partially) outside of the
            frame.

        start : Timestamp, optional
            If specified, load the dataset starting at this video timestamp.

        end : Timestamp, optional
            If specified, load the dataset until this video timestamp.

        Returns
        -------
        xarray.Dataset:
            The video data as a dataset.
        """
        t = self.timestamps

        if start is not None:
            start = t.get_loc(start, method='nearest')

        if end is not None:
            end = t.get_loc(end, method='nearest')

        t = t[start:end]

        if dropna:
            t_gen, flow_gen = zip(
                *((t, f)
                  for t, f in zip(t, self.read_frames(start, end))
                  if not np.any(np.isnan(f))))
            t = pd.DatetimeIndex(t_gen)
            frames = np.array(flow_gen)
        else:
            frames = np.empty((t.size,) + self.frame_shape)
            for idx, f in enumerate(self.read_frames(start, end)):
                frames[idx] = f

        frames = self.convert_to_uint8(frames)

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


class OpticalFlowReader(VideoReader):
    """ Reader for extracting optical flow from video data. """

    def __init__(self, folder, source='world', **kwargs):
        """ Constructor.

        Parameters
        ----------
        folder : str
            Path to the recording folder.

        source : str, default 'world'
            The source of the data. If 'recording', the recorded data will
            be used.

        **kwargs : optional
            Additional parameters passed to the ``VideoReader`` constructor.

        See Also
        --------
        VideoReader
        """
        super(OpticalFlowReader, self).__init__(
            folder, source=source, color_format='gray', **kwargs)

        self.flow_shape = self.load_optical_flow(0).shape

    @property
    def _nc_name(self):
        """ Name of exported netCDF file. """
        return 'optical_flow'

    @staticmethod
    def _get_valid_idx(norm_pos, frame_shape, roi_size):
        """ Get idx of norm_pos where all ROI pixels are inside the frame. """
        idx = VideoReader._get_valid_idx(norm_pos, frame_shape, roi_size)
        return np.hstack((False, idx[1:] & idx[:-1]))

    @staticmethod
    def calculate_optical_flow(frame, last_frame):
        """ Calculate dense optical flow between two frames.

        Parameters
        ----------
        frame : numpy.ndarray
            The input frame.

        last_frame : numpy.ndarray
            The previous frame.

        Returns
        -------
        numpy.ndarray
            The dense optical flow between the frames.
        """
        # TODO fix scale for float images?
        if last_frame is not None:
            # TODO make configurable
            return -cv2.calcOpticalFlowFarneback(
                last_frame, frame, None, pyr_scale=0.5, levels=3, winsize=20,
                iterations=3, poly_n=7, poly_sigma=1.5, flags=0)
        else:
            return np.nan * np.ones(frame.shape + (2,))

    def load_optical_flow(self, idx, return_timestamp=False):
        """ Load a single optical flow frame.

        Parameters
        ----------
        idx : int
            The index of the frame

        return_timestamp : bool, default False
            If True, also return the timestamp of the frame.

        Returns
        -------
        numpy.ndarray
            The loaded optical flow frame.
        """
        if idx < 0 or idx >= self.frame_count:
            raise ValueError('Frame index out of range')

        if idx == 0:
            last_frame = None
        else:
            last_frame = self.load_frame(idx - 1)

        flow = self.calculate_optical_flow(self.load_frame(idx), last_frame)

        if return_timestamp:
            return self.timestamps[idx], flow
        else:
            return flow

    def read_optical_flow(self, start=None, end=None):
        """ Generator for optical flow frames.

        Parameters
        ----------
        start : int, optional
            If specified, start the generator at this frame index.

        end : int, optional
            If specified, stop the generator at this frame index.

        Yields
        -------
        numpy.ndarray
            The loaded optical flow frame.
        """
        last_frame = None
        for frame in self.read_frames(start, end):
            yield self.calculate_optical_flow(frame, last_frame)
            last_frame = frame

    def load_dataset(self, dropna=False, start=None, end=None,
                     iter_wrapper=_iter_wrapper):
        """ Load optical flow data as an xarray Dataset

        Parameters
        ----------
        dropna : bool, default False
            If True, drop all frames containing NaN values. This can happen
            with ROI extraction when the ROI is (partially) outside of the
            frame.

        start : Timestamp, optional
            If specified, load the dataset starting at this video timestamp.

        end : Timestamp, optional
            If specified, load the dataset until this video timestamp.

        iter_wrapper : callable, optional
            A wrapper around the optical flow generator. Works with ``tqdm``
            as a progress bar.

        Returns
        -------
        xarray.Dataset:
            The optical flow data as a dataset.
        """
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
                    self.read_optical_flow(start, end), total=t.size):
                if not np.any(np.isnan(f)):
                    flow[idx] = f
                    valid_idx[idx] = True
                    idx += 1
            flow = flow[:idx]
            t = t[valid_idx]
        else:
            flow = np.empty((t.size,) + self.flow_shape)
            for idx, f in iter_wrapper(enumerate(
                    self.read_optical_flow(start, end)), total=t.size):
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