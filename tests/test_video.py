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
        self.frame_shape = (720, 1280, 3)
        self.roi_size = 128

    def test_get_capture(self):
        """"""
        capture = VideoInterface._get_capture(self.folder, 'world')

        assert isinstance(capture, cv2.VideoCapture)

        with self.assertRaises(FileNotFoundError):
            VideoInterface._get_capture(self.folder, 'not_a_topic')

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

    def test_read_frames(self):
        """"""
        # full frame
        interface = VideoInterface(self.folder)
        for frame in interface.read_frames():
            assert frame.shape == self.frame_shape

        # grayscale
        interface = VideoInterface(self.folder, color_format='gray')
        for frame in interface.read_frames():
            assert frame.shape == self.frame_shape[:2]

        # sub-sampled frame
        interface = VideoInterface(self.folder, subsampling=2.)
        for frame in interface.read_frames():
            assert frame.shape == (
                self.frame_shape[0] / 2, self.frame_shape[1] / 2,
                self.frame_shape[2])

        # ROI around gaze position
        norm_pos = load_dataset(self.folder, gaze='recording').gaze_norm_pos
        interface = VideoInterface(
            self.folder, norm_pos=norm_pos, roi_size=self.roi_size)
        for frame in interface.read_frames():
            assert frame.shape == (
                self.roi_size, self.roi_size, self.frame_shape[2])


class TestOpticalFlowInterface(InterfaceTester):

    def setUp(self):
        """"""
        super(TestOpticalFlowInterface, self).setUp()
        self.n_valid_frames = 463
        self.frame_shape = (720, 1280, 3)
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

    def test_estimate_optical_flow(self):
        """"""
        norm_pos = load_dataset(self.folder, gaze='recording').gaze_norm_pos
        interface = OpticalFlowInterface(
            self.folder, norm_pos=norm_pos, roi_size=self.roi_size)

        for flow in interface.estimate_optical_flow():
            assert flow.shape == (
                self.roi_size, self.roi_size, 2)

    def test_load_dataset(self):
        """"""
        norm_pos = load_dataset(self.folder, gaze='recording').gaze_norm_pos
        interface = OpticalFlowInterface(
            self.folder, norm_pos=norm_pos, roi_size=self.roi_size)

        ds = interface.load_dataset(dropna=True)

        self.assertDictEqual(dict(ds.sizes), {
            'time': self.n_valid_frames,
            'roi_x': self.roi_size,
            'roi_y': self.roi_size,
            'pixel_axis': 2})

        assert set(ds.data_vars) == {'optical_flow'}
