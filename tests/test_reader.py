import os
import sys

import cv2
import numpy as np
import pandas as pd
import pytest
import xarray as xr
from numpy import testing as npt

from pupil_recording_interface import (
    GazeReader,
    load_dataset,
    write_netcdf,
    get_gaze_mappers,
    BaseReader,
    OdometryReader,
    VideoReader,
    OpticalFlowReader,
)
from pupil_recording_interface.errors import FileNotFoundError


class TestBaseReader(object):
    def test_constructor(self, folder):
        """"""
        exporter = BaseReader(folder)
        assert exporter.folder == folder

        with pytest.raises(FileNotFoundError):
            BaseReader("not_a_folder")

    def test_load_info(self, folder):
        """"""
        info = BaseReader._load_info(folder)
        assert info == info

        # legacy format
        info = BaseReader._load_info(folder, "info.csv")
        info["duration_s"] = 21.0
        assert info == info

        with pytest.raises(FileNotFoundError):
            BaseReader._load_info(folder, "not_a_file")

    def test_load_user_info(self, folder, info):
        """"""
        user_info = BaseReader._load_user_info(
            folder, info["start_time_system_s"]
        )

        t0 = pd.to_datetime(info["start_time_system_s"], unit="s")

        assert user_info == {
            "name": "TEST",
            "pre_calibration_start": t0 + pd.to_timedelta("1s"),
            "pre_calibration_end": t0 + pd.to_timedelta("2s"),
            "experiment_start": t0 + pd.to_timedelta("3s"),
            "experiment_end": t0 + pd.to_timedelta("4s"),
            "post_calibration_start": t0 + pd.to_timedelta("5s"),
            "post_calibration_end": t0 + pd.to_timedelta("6s"),
            "height": 1.80,
        }

    def test_timestamps_to_datetimeindex(self, folder, info):
        """"""
        timestamps = np.array([2295.0, 2296.0, 2297.0])

        idx = BaseReader._timestamps_to_datetimeindex(timestamps, info)

        assert idx.values[0].astype(float) / 1e9 == 1570725800.4130569

    def test_load_timestamps_as_datetimeindex(self, folder, info):
        """"""
        idx = BaseReader._load_timestamps_as_datetimeindex(
            folder, "gaze", info
        )
        assert idx.values[0].astype(float) / 1e9 == 1570725800.149778

        # with offset
        idx_with_offs = BaseReader._load_timestamps_as_datetimeindex(
            folder, "gaze", info, 1.0
        )
        assert np.all(idx_with_offs == idx + pd.to_timedelta("1s"))

        with pytest.raises(FileNotFoundError):
            BaseReader._load_timestamps_as_datetimeindex(
                folder, "not_a_topic", info
            )

    def test_load_pldata_as_dataframe(self, folder):
        """"""
        df = BaseReader._load_pldata_as_dataframe(folder, "odometry")

        assert set(df.columns) == {
            "topic",
            "timestamp",
            "confidence",
            "linear_velocity",
            "angular_velocity",
            "position",
            "orientation",
        }

        with pytest.raises(FileNotFoundError):
            BaseReader._load_pldata_as_dataframe(folder, "not_a_topic")

    def test_get_encoding(self):
        """"""
        encoding = BaseReader._get_encoding(["test_var"])

        assert encoding["test_var"] == {
            "zlib": True,
            "dtype": "int32",
            "scale_factor": 0.0001,
            "_FillValue": np.iinfo("int32").min,
        }

    def test_create_export_folder(self, export_folder):
        """"""
        BaseReader._create_export_folder(
            os.path.join(export_folder, "test.nc")
        )

        assert os.path.exists(export_folder)

    def test_write_netcdf(self, folder, export_folder):
        """"""
        GazeReader(folder).write_netcdf()

        ds = xr.open_dataset(os.path.join(export_folder, "gaze.nc"))

        assert set(ds.data_vars) == {
            "gaze_confidence_3d",
            "gaze_point",
            "gaze_norm_pos",
        }

        ds.close()


class TestFunctionalReader(object):
    def test_load_dataset(self, folder):
        """"""
        gaze, odometry = load_dataset(
            folder, gaze="recording", odometry="recording"
        )

        assert set(gaze.data_vars) == {
            "gaze_confidence_3d",
            "gaze_point",
            "gaze_norm_pos",
        }
        assert set(odometry.data_vars) == {
            "tracker_confidence",
            "linear_velocity",
            "angular_velocity",
            "linear_position",
            "angular_position",
        }

    def test_write_netcdf(self, folder):
        """"""
        write_netcdf(folder, gaze="recording", odometry="recording")

        assert os.path.exists(os.path.join(folder, "exports", "odometry.nc"))
        assert os.path.exists(os.path.join(folder, "exports", "gaze.nc"))

    def test_get_gaze_mappers(self, folder):
        """"""
        mappers = get_gaze_mappers(folder)

        assert mappers == {"recording", "2d Gaze Mapper ", "3d Gaze Mapper"}


class TestGazeReader(object):
    @pytest.fixture(autouse=True)
    def set_up(self):
        """"""
        self.n_gaze = 5160
        self.n_gaze_offline = 5134
        self.gaze_mappers = {"2d": "2d Gaze Mapper ", "3d": "3d Gaze Mapper"}

    def test_load_gaze(self, folder):
        """"""
        t, c, n, p = GazeReader._load_gaze(folder)

        assert t.shape == (self.n_gaze,)
        assert c.shape == (self.n_gaze,)
        assert n.shape == (self.n_gaze, 2)
        assert p.shape == (self.n_gaze, 3)

    def test_load_merged_gaze(self, folder):
        """"""
        t, c, n, p = GazeReader._load_merged_gaze(folder, self.gaze_mappers)

        assert t.shape == (self.n_gaze_offline,)
        assert c[0].shape == (self.n_gaze_offline,)
        assert c[1].shape == (self.n_gaze_offline,)
        assert n.shape == (self.n_gaze_offline, 2)
        assert p.shape == (self.n_gaze_offline, 3)

    def test_get_offline_gaze_mapper(self, folder):
        """"""
        mappers = GazeReader._get_offline_gaze_mappers(folder)

        assert set(mappers.keys()) == {"3d Gaze Mapper", "2d Gaze Mapper "}
        for v in mappers.values():
            assert os.path.exists(
                os.path.join(
                    folder, "offline_data", "gaze-mappings", v + ".pldata"
                )
            )

        with pytest.raises(FileNotFoundError):
            GazeReader._get_offline_gaze_mappers("not_a_folder")

    def test_load_dataset(self, folder):
        """"""
        # from recording
        ds = GazeReader(folder).load_dataset()

        assert dict(ds.sizes) == {
            "time": self.n_gaze,
            "cartesian_axis": 3,
            "pixel_axis": 2,
        }

        assert set(ds.data_vars) == {
            "gaze_confidence_3d",
            "gaze_point",
            "gaze_norm_pos",
        }

        # offline 2d mapper
        ds = GazeReader(folder, source=self.gaze_mappers["2d"]).load_dataset()

        assert dict(ds.sizes) == {"time": self.n_gaze_offline, "pixel_axis": 2}

        assert set(ds.data_vars) == {"gaze_confidence_2d", "gaze_norm_pos"}

        # merged 2d/3d gaze
        ds = GazeReader(folder, source=self.gaze_mappers).load_dataset()

        assert dict(ds.sizes) == {
            "time": self.n_gaze_offline,
            "cartesian_axis": 3,
            "pixel_axis": 2,
        }

        assert set(ds.data_vars) == {
            "gaze_confidence_2d",
            "gaze_confidence_3d",
            "gaze_point",
            "gaze_norm_pos",
        }

        # bad gaze argument
        with pytest.raises(ValueError):
            GazeReader(folder, source="not_gaze_mapper").load_dataset()

    def test_write_netcdf(self, folder, export_folder):
        """"""
        GazeReader(folder).write_netcdf()

        ds = xr.open_dataset(os.path.join(export_folder, "gaze.nc"))

        assert set(ds.data_vars) == {
            "gaze_confidence_3d",
            "gaze_point",
            "gaze_norm_pos",
        }

        ds.close()


class TestOdometryReader(object):
    @pytest.fixture(autouse=True)
    def set_up(self):
        """"""
        self.n_odometry = 4220

    def test_load_odometry(self, folder):
        """"""
        t, c, p, q, v, w = OdometryReader._load_odometry(folder)

        assert t.shape == (self.n_odometry,)
        assert c.shape == (self.n_odometry,)
        assert c.dtype == int
        assert p.shape == (self.n_odometry, 3)
        assert q.shape == (self.n_odometry, 4)
        assert v.shape == (self.n_odometry, 3)
        assert w.shape == (self.n_odometry, 3)

    def test_load_dataset(self, folder):
        """"""
        # from recording
        ds = OdometryReader(folder).load_dataset()

        assert dict(ds.sizes) == {
            "time": self.n_odometry,
            "cartesian_axis": 3,
            "quaternion_axis": 4,
        }

        assert set(ds.data_vars) == {
            "tracker_confidence",
            "linear_velocity",
            "angular_velocity",
            "linear_position",
            "angular_position",
        }

        # bad odometry argument
        with pytest.raises(ValueError):
            OdometryReader(folder, source="not_supported").load_dataset()


class TestVideoReader(object):
    @pytest.fixture(autouse=True)
    def set_up(self):
        """"""
        self.n_frames = 504
        self.n_valid_frames = 474
        self.frame_shape = (720, 1280, 3)
        self.roi_size = 128
        self.fps = 23.98741572903148

    def test_get_encoding(self):
        """"""
        encoding = VideoReader._get_encoding(["frames"])

        assert encoding["frames"] == {
            "zlib": True,
            "dtype": "uint8",
        }

    @pytest.mark.xfail(
        sys.version_info < (3, 0), reason="isinstance check fails"
    )
    def test_get_capture(self, folder):
        """"""
        capture = VideoReader._get_capture(folder, "world")

        assert isinstance(capture, cv2.VideoCapture)

        with pytest.raises(FileNotFoundError):
            VideoReader._get_capture(folder, "not_a_topic")

    def test_resolution(self, folder):
        """"""
        resolution = VideoReader(folder, "world").resolution
        assert resolution == self.frame_shape[-2::-1]
        assert isinstance(resolution[0], int)
        assert isinstance(resolution[1], int)

    def test_frame_count(self, folder):
        """"""
        frame_count = VideoReader(folder, "world").frame_count
        assert frame_count == self.n_frames
        assert isinstance(frame_count, int)

    def test_frame_shape(self, folder):
        """"""
        shape = VideoReader(folder).frame_shape
        assert shape == self.frame_shape

    def test_fps(self, folder):
        """"""
        fps = VideoReader(folder).fps
        assert fps == self.fps

    def test_get_valid_idx(self):
        """"""
        norm_pos = np.array(
            [[0.5, 0.5], [0.5, 0.5], [0.5, 0.9], [0.9, 0.5], [0.5, 0.5]]
        )

        idx = VideoReader._get_valid_idx(norm_pos, (512, 512), self.roi_size)

        np.testing.assert_equal(idx, (True, True, False, False, True))

    def test_get_bounds(self, folder):
        """"""
        interface = VideoReader(folder, roi_size=self.roi_size)

        # completely inside
        bounds = interface._get_bounds(256, 512, self.roi_size)
        npt.assert_equal(bounds, ((0, 128), (192, 320)))

        # partially inside
        bounds = interface._get_bounds(0, 512, self.roi_size)
        npt.assert_equal(bounds, ((64, 128), (0, 64)))
        bounds = interface._get_bounds(512, 512, self.roi_size)
        npt.assert_equal(bounds, ((0, 64), (448, 512)))

        # completely outside
        bounds = interface._get_bounds(1024, 512, self.roi_size)
        npt.assert_equal(bounds, ((0, 0), (512, 512)))
        bounds = interface._get_bounds(-512, 512, self.roi_size)
        npt.assert_equal(bounds, ((576, 128), (0, 0)))

    def test_get_roi(self, folder):
        """"""
        frame = np.random.rand(512, 512)
        interface = VideoReader(folder, roi_size=self.roi_size)

        # completely inside
        roi = interface.get_roi(frame, (0.5, 0.5))
        npt.assert_equal(roi, frame[192:320, 192:320])

        # partially inside
        roi = interface.get_roi(frame, (0.0, 0.0))
        npt.assert_equal(roi[:64, 64:128], frame[448:, :64])

        # completely outside
        roi = interface.get_roi(frame, (2.0, 2.0))
        npt.assert_equal(roi, np.nan * np.ones((128, 128)))

        # regression test for valid negative indexes
        interface.get_roi(frame, (0.0, 1.3))

        # color frame
        frame = np.random.rand(512, 512, 3)
        roi = interface.get_roi(frame, (0.5, 0.5))
        assert roi.shape == (self.roi_size, self.roi_size, 3)

    def test_convert_to_uint8(self):
        """"""
        frame = VideoReader.convert_to_uint8(
            np.nan * np.ones(self.frame_shape)
        )
        np.testing.assert_equal(
            frame, np.zeros(self.frame_shape, dtype="uint8")
        )

    def test_load_raw_frame(self, folder):
        """"""
        interface = VideoReader(folder)
        frame = interface.load_raw_frame(0)
        assert frame.shape == self.frame_shape

        # invalid index
        with pytest.raises(ValueError):
            interface.load_raw_frame(self.n_frames)

    def test_load_frame(self, folder):
        """"""
        interface = VideoReader(folder)
        frame = interface.load_frame(0)
        assert frame.shape == self.frame_shape

        # ROI around norm pos
        norm_pos = load_dataset(folder, gaze="recording").gaze_norm_pos
        interface = VideoReader(
            folder, norm_pos=norm_pos, roi_size=self.roi_size
        )
        frame = interface.load_frame(0)
        assert frame.shape == (
            self.roi_size,
            self.roi_size,
            self.frame_shape[2],
        )

        # with timestamp
        interface = VideoReader(folder)
        t, frame = interface.load_frame(0, return_timestamp=True)
        assert float(t.value) / 1e9 == 1570725800.2383718

    def test_read_frames(self, folder):
        """"""
        # TODO move this to process_frame test
        # full frame
        interface = VideoReader(folder)
        assert next(interface.read_frames()).shape == self.frame_shape

        # grayscale
        interface = VideoReader(folder, color_format="gray")
        assert next(interface.read_frames()).shape == self.frame_shape[:2]

        # sub-sampled frame
        interface = VideoReader(folder, subsampling=2.0)
        assert next(interface.read_frames()).shape == (
            self.frame_shape[0] / 2,
            self.frame_shape[1] / 2,
            self.frame_shape[2],
        )

        # ROI around gaze position
        norm_pos = load_dataset(folder, gaze="recording").gaze_norm_pos
        interface = VideoReader(
            folder, norm_pos=norm_pos, roi_size=self.roi_size
        )
        assert next(interface.read_frames()).shape == (
            self.roi_size,
            self.roi_size,
            self.frame_shape[2],
        )

    def test_load_dataset(self, folder):
        """"""
        interface = VideoReader(folder, subsampling=8.0, color_format="gray")

        ds = interface.load_dataset(
            start=interface.user_info["experiment_start"],
            end=interface.user_info["experiment_end"],
        )

        assert dict(ds.sizes) == {"time": 22, "frame_x": 160, "frame_y": 90}

        assert set(ds.data_vars) == {"frames"}
        assert ds.frames.dtype == "uint8"

        # ROI around norm_pos
        norm_pos = load_dataset(folder, gaze="recording").gaze_norm_pos
        interface = VideoReader(
            folder, norm_pos=norm_pos, roi_size=self.roi_size
        )

        ds = interface.load_dataset(dropna=True)

        assert dict(ds.sizes) == {
            "time": self.n_valid_frames,
            "frame_x": self.roi_size,
            "frame_y": self.roi_size,
            "color": 3,
        }

        assert set(ds.data_vars) == {"frames"}
        assert ds.frames.dtype == "uint8"


class TestOpticalFlowReader(object):
    @pytest.fixture(autouse=True)
    def set_up(self):
        """"""
        self.n_frames = 504
        self.n_valid_frames = 463
        self.frame_shape = (720, 1280, 2)
        self.roi_size = 128

    def test_get_valid_idx(self):
        """"""
        norm_pos = np.array(
            [[0.5, 0.5], [0.5, 0.5], [0.5, 0.9], [0.9, 0.5], [0.5, 0.5]]
        )

        idx = OpticalFlowReader._get_valid_idx(
            norm_pos, (512, 512), self.roi_size
        )

        np.testing.assert_equal(idx, (False, True, False, False, False))

    def test_calculate_optical_flow(self):
        """"""
        flow = OpticalFlowReader.calculate_optical_flow(
            np.random.rand(128, 128), np.random.rand(128, 128)
        )
        assert flow.shape == (128, 128, 2)
        assert not np.any(np.isnan(flow))

        # no last roi
        flow = OpticalFlowReader.calculate_optical_flow(
            np.random.rand(128, 128), None
        )
        npt.assert_equal(flow, np.nan * np.ones((128, 128, 2)))

    def test_load_optical_flow(self, folder):
        """"""
        interface = OpticalFlowReader(folder)

        flow = interface.load_optical_flow(1)
        assert flow.shape == self.frame_shape

        # first frame
        flow = interface.load_optical_flow(0)
        assert flow.shape == self.frame_shape
        assert np.all(np.isnan(flow))

        # with timestamp
        t, flow = interface.load_optical_flow(1, return_timestamp=True)
        assert float(t.value) / 1e9 == 1570725800.2718818

        # invalid index
        with pytest.raises(ValueError):
            interface.load_optical_flow(self.n_frames)

    def test_read_optical_flow(self, folder):
        """"""
        norm_pos = load_dataset(folder, gaze="recording").gaze_norm_pos
        interface = OpticalFlowReader(
            folder, norm_pos=norm_pos, roi_size=self.roi_size
        )

        assert next(interface.read_optical_flow()).shape == (
            self.roi_size,
            self.roi_size,
            2,
        )

    def test_load_dataset(self, folder):
        """"""
        import tqdm

        interface = OpticalFlowReader(folder, subsampling=8.0)

        ds = interface.load_dataset(
            start=interface.user_info["experiment_start"],
            end=interface.user_info["experiment_end"],
        )

        assert dict(ds.sizes) == {
            "time": 22,
            "roi_x": 160,
            "roi_y": 90,
            "pixel_axis": 2,
        }
        assert ds.indexes["time"][0] >= interface.user_info["experiment_start"]
        assert ds.indexes["time"][-1] < interface.user_info["experiment_end"]
        assert set(ds.data_vars) == {"optical_flow"}

        # ROI around norm_pos
        norm_pos = load_dataset(folder, gaze="recording").gaze_norm_pos
        interface = OpticalFlowReader(
            folder, norm_pos=norm_pos, roi_size=self.roi_size
        )

        ds = interface.load_dataset(dropna=True, iter_wrapper=tqdm.tqdm)

        assert dict(ds.sizes) == {
            "time": self.n_valid_frames,
            "roi_x": self.roi_size,
            "roi_y": self.roi_size,
            "pixel_axis": 2,
        }

        npt.assert_allclose(
            ds.roi_x,
            np.arange(-self.roi_size / 2 + 0.5, self.roi_size / 2 + 0.5),
        )
        npt.assert_allclose(
            ds.roi_y,
            np.arange(self.roi_size / 2 - 0.5, -self.roi_size / 2 - 0.5, -1),
        )

        # start/end with dropna
        ds = interface.load_dataset(
            dropna=True,
            start=interface.user_info["experiment_start"],
            end=interface.user_info["experiment_end"],
        )

        assert ds.sizes["time"] == 21
