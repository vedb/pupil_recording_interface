import os

from .test_base import InterfaceTester
import numpy.testing as npt

import numpy as np
import xarray as xr
import cv2

from pupil_recording_interface import \
    VideoInterface, OpticalFlowInterface, load_dataset


class TestVideoInterface(InterfaceTester):

    def setUp(self):
        """"""
        super(TestVideoInterface, self).setUp()
        self.n_frames = 504
        self.n_valid_frames = 474
        self.frame_shape = (720, 1280, 3)
        self.roi_size = 128
        self.fps = 23.98741572903148

    def test_get_encoding(self):
        """"""
        encoding = VideoInterface._get_encoding(['frames'])

        self.assertDictEqual(encoding['frames'], {
            'zlib': True,
            'dtype': 'uint8',
        })

    def test_get_capture(self):
        """"""
        capture = VideoInterface._get_capture(self.folder, 'world')

        assert isinstance(capture, cv2.VideoCapture)

        with self.assertRaises(FileNotFoundError):
            VideoInterface._get_capture(self.folder, 'not_a_topic')

    def test_resolution(self):
        """"""
        resolution = VideoInterface(self.folder, 'world').resolution
        assert resolution == self.frame_shape[-2::-1]

    def test_frame_count(self):
        """"""
        frame_count = VideoInterface(self.folder, 'world').frame_count
        assert frame_count == self.n_frames

    def test_frame_shape(self):
        """"""
        shape = VideoInterface(self.folder).frame_shape
        assert shape == self.frame_shape

    def test_fps(self):
        """"""
        fps = VideoInterface(self.folder).fps
        assert fps == self.fps

    def test_get_bounds(self):
        """"""
        # completely inside
        bounds = VideoInterface.get_bounds(256, 512, self.roi_size)
        npt.assert_equal(bounds, ((0, 128), (192, 320)))

        # partially inside
        bounds = VideoInterface.get_bounds(0, 512, self.roi_size)
        npt.assert_equal(bounds, ((64, 128), (0, 64)))
        bounds = VideoInterface.get_bounds(512, 512, self.roi_size)
        npt.assert_equal(bounds, ((0, 64), (448, 512)))

        # completely outside
        bounds = VideoInterface.get_bounds(1024, 512, self.roi_size)
        npt.assert_equal(bounds, ((0, 0), (512, 512)))
        bounds = VideoInterface.get_bounds(-512, 512, self.roi_size)
        npt.assert_equal(bounds, ((576, 128), (0, 0)))

    def test_get_roi(self):
        """"""
        frame = np.random.rand(512, 512)

        # completely inside
        roi = VideoInterface.get_roi(frame, (0.5, 0.5), self.roi_size)
        npt.assert_equal(roi, frame[192:320, 192:320])

        # partially inside
        roi = VideoInterface.get_roi(frame, (0., 0.), self.roi_size)
        npt.assert_equal(roi[:64, 64:128], frame[448:, :64])

        # completely outside
        roi = VideoInterface.get_roi(frame, (2., 2.), self.roi_size)
        npt.assert_equal(roi, np.nan * np.ones((128, 128)))

        # regression test for valid negative indexes
        VideoInterface.get_roi(frame, (0., 1.3), self.roi_size)

        # color frame
        frame = np.random.rand(512, 512, 3)
        roi = VideoInterface.get_roi(frame, (0.5, 0.5), self.roi_size)
        assert roi.shape == (self.roi_size, self.roi_size, 3)

    def test_frame_as_uint8(self):
        """"""
        frame = VideoInterface.frame_as_uint8(np.nan*np.ones(self.frame_shape))
        np.testing.assert_equal(
            frame, np.zeros(self.frame_shape, dtype='uint8'))

    def test_get_frame(self):
        """"""
        interface = VideoInterface(self.folder)

        frame = interface.get_frame(0)
        assert frame.shape == self.frame_shape

        # with timestamp
        t, frame = interface.get_frame(0, return_timestamp=True)
        assert float(t.value) / 1e9 == 1570725800.2383718

        # invalid index
        with self.assertRaises(ValueError):
            interface.get_frame(self.n_frames)

    def test_read_frames(self):
        """"""
        # TODO move this to process_frame test
        # full frame
        interface = VideoInterface(self.folder)
        assert next(interface.read_frames()).shape == self.frame_shape

        # grayscale
        interface = VideoInterface(self.folder, color_format='gray')
        assert next(interface.read_frames()).shape == self.frame_shape[:2]

        # sub-sampled frame
        interface = VideoInterface(self.folder, subsampling=2.)
        assert next(interface.read_frames()).shape == (
            self.frame_shape[0] / 2, self.frame_shape[1] / 2,
            self.frame_shape[2])

        # ROI around gaze position
        norm_pos = load_dataset(self.folder, gaze='recording').gaze_norm_pos
        interface = VideoInterface(
            self.folder, norm_pos=norm_pos, roi_size=self.roi_size)
        assert next(interface.read_frames()).shape == (
            self.roi_size, self.roi_size, self.frame_shape[2])

    def test_load_dataset(self):
        """"""
        interface = VideoInterface(
            self.folder, subsampling=8., color_format='gray')

        ds = interface.load_dataset()

        self.assertDictEqual(dict(ds.sizes), {
            'time': self.n_frames,
            'frame_x': 160,
            'frame_y': 90})

        assert set(ds.data_vars) == {'frames'}
        assert ds.frames.dtype == 'uint8'

        # ROI around norm_pos
        norm_pos = load_dataset(self.folder, gaze='recording').gaze_norm_pos
        interface = VideoInterface(
            self.folder, norm_pos=norm_pos, roi_size=self.roi_size)

        ds = interface.load_dataset(dropna=True)

        self.assertDictEqual(dict(ds.sizes), {
            'time': self.n_valid_frames,
            'frame_x': self.roi_size,
            'frame_y': self.roi_size,
            'color': 3})

        assert set(ds.data_vars) == {'frames'}
        assert ds.frames.dtype == 'uint8'


class TestOpticalFlowInterface(InterfaceTester):

    def setUp(self):
        """"""
        super(TestOpticalFlowInterface, self).setUp()
        self.n_frames = 504
        self.n_valid_frames = 463
        self.frame_shape = (720, 1280, 2)
        self.roi_size = 128

    def test_calculate_flow(self):
        """"""
        flow = OpticalFlowInterface.calculate_flow(
            np.random.rand(128, 128), np.random.rand(128, 128))
        self.assertEqual(flow.shape, (128, 128, 2))
        assert not np.any(np.isnan(flow))

        # no last roi
        flow = OpticalFlowInterface.calculate_flow(
            np.random.rand(128, 128), None)
        npt.assert_equal(flow, np.nan * np.ones((128, 128, 2)))

    def test_get_optical_flow(self):
        """"""
        interface = OpticalFlowInterface(self.folder)

        flow = interface.get_optical_flow(1)
        assert flow.shape == self.frame_shape

        # first frame
        flow = interface.get_optical_flow(0)
        assert flow.shape == self.frame_shape
        assert np.all(np.isnan(flow))

        # with timestamp
        t, flow = interface.get_optical_flow(1, return_timestamp=True)
        assert float(t.value) / 1e9 == 1570725800.2718818

        # invalid index
        with self.assertRaises(ValueError):
            interface.get_optical_flow(self.n_frames)

    def test_estimate_optical_flow(self):
        """"""
        norm_pos = load_dataset(self.folder, gaze='recording').gaze_norm_pos
        interface = OpticalFlowInterface(
            self.folder, norm_pos=norm_pos, roi_size=self.roi_size)

        assert next(interface.estimate_optical_flow()).shape == (
            self.roi_size, self.roi_size, 2)

    def test_load_dataset(self):
        """"""
        interface = OpticalFlowInterface(self.folder, subsampling=8.)

        ds = interface.load_dataset()

        self.assertDictEqual(dict(ds.sizes), {
            'time': self.n_frames,
            'roi_x': 160,
            'roi_y': 90,
            'pixel_axis': 2})

        assert set(ds.data_vars) == {'optical_flow'}

        # ROI around norm_pos
        norm_pos = load_dataset(self.folder, gaze='recording').gaze_norm_pos
        interface = OpticalFlowInterface(
            self.folder, norm_pos=norm_pos, roi_size=self.roi_size)

        ds = interface.load_dataset(dropna=True)

        self.assertDictEqual(dict(ds.sizes), {
            'time': self.n_valid_frames,
            'roi_x': self.roi_size,
            'roi_y': self.roi_size,
            'pixel_axis': 2})
