import sys
import shutil
from pathlib import Path

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
    MotionReader,
    VideoReader,
    OpticalFlowReader,
)


@pytest.fixture()
def t265_folder():
    """"""
    return Path(__file__).parent / "test_data" / "t265_test_recording"


@pytest.fixture()
def t265_export_folder(t265_folder):
    """"""
    export_folder = t265_folder / "exports"
    yield export_folder
    shutil.rmtree(export_folder, ignore_errors=True)


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

    def test_write_netcdf(self, folder, export_folder):
        """"""
        pytest.importorskip("netcdf4")

        GazeReader(folder).write_netcdf()

        ds = xr.open_dataset(export_folder / "gaze.nc")

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
            "confidence",
            "linear_velocity",
            "angular_velocity",
            "position",
            "orientation",
        }

    def test_load_dataset_cached(self, folder):
        """"""
        pytest.importorskip("netCDF4")

        load_dataset(folder, gaze="recording", cache=True)
        assert (
            folder
            / "cache"
            / "gaze-18a8baba7367c3ed0086a0c345f3c67bc2ca8b39.nc"
        ).exists()

        gaze = load_dataset(folder, gaze="recording", cache=False)
        gaze_nc = load_dataset(folder, gaze="recording", cache=True)
        assert gaze_nc == gaze

        shutil.rmtree(folder / "cache")

    def test_write_netcdf(
        self, folder, t265_folder, export_folder, t265_export_folder
    ):
        """"""
        pytest.importorskip("netCDF4")

        # packaged recording
        write_netcdf(folder, gaze="recording", odometry="recording")
        assert (export_folder / "000" / "odometry.nc").exists()
        assert (export_folder / "000" / "gaze.nc").exists()

        # test data recording
        write_netcdf(
            t265_folder,
            odometry="recording",
            accel="recording",
            gyro="recording",
        )
        assert (t265_export_folder / "000" / "odometry.nc").exists()
        assert (t265_export_folder / "000" / "accel.nc").exists()
        assert (t265_export_folder / "000" / "gyro.nc").exists()

    def test_get_gaze_mappers(self, folder):
        """"""
        mappers = get_gaze_mappers(str(folder))

        assert mappers == {"recording", "2d Gaze Mapper ", "3d Gaze Mapper"}


class TestGazeReader(object):
    @pytest.fixture(autouse=True)
    def set_up(self):
        """"""
        self.n_gaze = 5160
        self.n_gaze_offline = 5134
        self.gaze_mappers = {"2d": "2d Gaze Mapper ", "3d": "3d Gaze Mapper"}

    def test_constructor(self, folder, t265_folder):
        """"""
        reader = GazeReader(folder)
        assert set(reader.gaze_mappers.keys()) == {
            "3d Gaze Mapper",
            "2d Gaze Mapper ",
        }

        # no offline mappers
        reader = GazeReader(t265_folder)
        assert reader.gaze_mappers == {}

    def test_load_gaze(self, folder, t265_folder):
        """"""
        t, c, n, p = GazeReader._load_gaze(folder)

        assert t.shape == (self.n_gaze,)
        assert c.shape == (self.n_gaze,)
        assert n.shape == (self.n_gaze, 2)
        assert p.shape == (self.n_gaze, 3)

        # no gaze
        with pytest.raises(FileNotFoundError):
            GazeReader._load_gaze(t265_folder)

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
            assert (
                folder / "offline_data" / "gaze-mappings" / f"{v}.pldata"
            ).exists()

        with pytest.raises(FileNotFoundError):
            GazeReader._get_offline_gaze_mappers(folder / "not_a_folder")

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
        pytest.importorskip("netcdf4")

        GazeReader(folder).write_netcdf()

        ds = xr.open_dataset(export_folder / "gaze.nc")

        assert set(ds.data_vars) == {
            "gaze_confidence_3d",
            "gaze_point",
            "gaze_norm_pos",
        }

        ds.close()


class TestMotionReader(object):
    @pytest.fixture(autouse=True)
    def set_up(self):
        """"""
        self.n_odometry_legacy = 4220
        self.n_odometry = 5850
        self.n_accel = 1939
        self.n_gyro = 5991

    def test_load_data(self, folder, t265_folder):
        """"""
        # legacy odometry
        data = MotionReader._load_data(folder)
        assert data["timestamp"].shape == (self.n_odometry_legacy,)
        assert data["confidence"].shape == (self.n_odometry_legacy,)
        assert data["confidence"].dtype == int
        assert data["position"].shape == (self.n_odometry_legacy, 3)
        assert data["orientation"].shape == (self.n_odometry_legacy, 4)
        assert data["linear_velocity"].shape == (self.n_odometry_legacy, 3)
        assert data["angular_velocity"].shape == (self.n_odometry_legacy, 3)

        # odometry
        data = MotionReader._load_data(t265_folder)
        assert data["timestamp"].shape == (self.n_odometry,)
        assert data["confidence"].shape == (self.n_odometry,)
        assert data["position"].shape == (self.n_odometry, 3)
        assert data["orientation"].shape == (self.n_odometry, 4)
        assert data["linear_velocity"].shape == (self.n_odometry, 3)
        assert data["angular_velocity"].shape == (self.n_odometry, 3)
        assert data["linear_acceleration"].shape == (self.n_odometry, 3)
        assert data["angular_acceleration"].shape == (self.n_odometry, 3)

        # accel
        data = MotionReader._load_data(t265_folder, "accel")
        assert data["timestamp"].shape == (self.n_accel,)
        assert data["linear_acceleration"].shape == (self.n_accel, 3)

        # gyro
        data = MotionReader._load_data(t265_folder, "gyro")
        assert data["timestamp"].shape == (self.n_gyro,)
        assert data["angular_velocity"].shape == (self.n_gyro, 3)

    def test_load_dataset(self, folder, t265_folder):
        """"""
        # legacy odometry
        ds = MotionReader(folder).load_dataset()
        assert dict(ds.sizes) == {
            "time": self.n_odometry_legacy,
            "cartesian_axis": 3,
            "quaternion_axis": 4,
        }
        assert set(ds.data_vars) == {
            "confidence",
            "linear_velocity",
            "angular_velocity",
            "position",
            "orientation",
        }

        # odometry
        ds = MotionReader(t265_folder).load_dataset()
        assert dict(ds.sizes) == {
            "time": self.n_odometry,
            "cartesian_axis": 3,
            "quaternion_axis": 4,
        }
        assert set(ds.data_vars) == {
            "confidence",
            "linear_acceleration",
            "angular_acceleration",
            "linear_velocity",
            "angular_velocity",
            "position",
            "orientation",
        }

        # accel
        ds = MotionReader(t265_folder, "accel").load_dataset()
        assert dict(ds.sizes) == {"time": self.n_accel, "cartesian_axis": 3}
        assert set(ds.data_vars) == {"linear_acceleration"}

        # gyro
        ds = MotionReader(t265_folder, "gyro").load_dataset()
        assert dict(ds.sizes) == {"time": self.n_gyro, "cartesian_axis": 3}
        assert set(ds.data_vars) == {"angular_velocity"}

        # bad source argument
        with pytest.raises(ValueError):
            MotionReader(folder, source="not_supported").load_dataset()


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

    def test_current_frame_index(self, folder):
        """"""
        reader = VideoReader(folder)
        assert reader.current_frame_index == 0

        reader.load_raw_frame()
        assert reader.current_frame_index == 1

    def test_get_valid_idx(self):
        """"""
        norm_pos = np.array(
            [[0.5, 0.5], [0.5, 0.5], [0.5, 0.9], [0.9, 0.5], [0.5, 0.5]]
        )

        idx = VideoReader._get_valid_idx(norm_pos, (512, 512), self.roi_size)

        np.testing.assert_equal(idx, (True, True, False, False, True))

    def test_get_bounds(self, folder):
        """"""
        reader = VideoReader(folder, roi_size=self.roi_size)

        # completely inside
        bounds = reader._get_bounds(256, 512, self.roi_size)
        npt.assert_equal(bounds, ((0, 128), (192, 320)))

        # partially inside
        bounds = reader._get_bounds(0, 512, self.roi_size)
        npt.assert_equal(bounds, ((64, 128), (0, 64)))
        bounds = reader._get_bounds(512, 512, self.roi_size)
        npt.assert_equal(bounds, ((0, 64), (448, 512)))

        # completely outside
        bounds = reader._get_bounds(1024, 512, self.roi_size)
        npt.assert_equal(bounds, ((0, 0), (512, 512)))
        bounds = reader._get_bounds(-512, 512, self.roi_size)
        npt.assert_equal(bounds, ((576, 128), (0, 0)))

    def test_get_frame_index(self, folder):
        """"""
        reader = VideoReader(folder)
        assert reader._get_frame_index(None) == 0
        assert reader._get_frame_index(None, default=1) == 1
        assert reader._get_frame_index(1) == 1
        assert reader._get_frame_index(reader.timestamps[2]) == 2

    def test_get_roi(self, folder):
        """"""
        frame = np.random.rand(512, 512)
        reader = VideoReader(folder, roi_size=self.roi_size)

        # completely inside
        roi = reader.get_roi(frame, (0.5, 0.5))
        npt.assert_equal(roi, frame[192:320, 192:320])

        # partially inside
        roi = reader.get_roi(frame, (0.0, 0.0))
        npt.assert_equal(roi[:64, 64:128], frame[448:, :64])

        # completely outside
        roi = reader.get_roi(frame, (2.0, 2.0))
        npt.assert_equal(roi, np.nan * np.ones((128, 128)))

        # regression test for valid negative indexes
        reader.get_roi(frame, (0.0, 1.3))

        # color frame
        frame = np.random.rand(512, 512, 3)
        roi = reader.get_roi(frame, (0.5, 0.5))
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
        reader = VideoReader(folder)
        frame = reader.load_raw_frame()
        assert frame.shape == self.frame_shape

        reader = VideoReader(folder)
        frame_by_idx = reader.load_raw_frame(0)
        npt.assert_equal(frame_by_idx, frame)

        # invalid index
        with pytest.raises(ValueError):
            reader.load_raw_frame(self.n_frames)

    def test_load_frame(self, folder):
        """"""
        reader = VideoReader(folder)
        frame = reader.load_frame()
        assert frame.shape == self.frame_shape

        frame_by_idx = reader.load_frame(0)
        npt.assert_equal(frame_by_idx, frame)

        # timestamp
        frame_by_ts = reader.load_frame(reader.timestamps[0])
        npt.assert_equal(frame_by_ts, frame)

        # ROI around norm pos
        norm_pos = load_dataset(folder, gaze="recording").gaze_norm_pos
        reader = VideoReader(folder, norm_pos=norm_pos, roi_size=self.roi_size)
        frame = reader.load_frame(0)
        assert frame.shape == (
            self.roi_size,
            self.roi_size,
            self.frame_shape[2],
        )

        # with timestamp
        reader = VideoReader(folder)
        t, frame = reader.load_frame(0, return_timestamp=True)
        assert float(t.value) / 1e9 == 1570725800.2383718

    def test_read_frames(self, folder):
        """"""
        # TODO move this to process_frame test
        # full frame
        reader = VideoReader(folder)
        assert next(reader.read_frames()).shape == self.frame_shape

        # grayscale
        reader = VideoReader(folder, color_format="gray")
        assert next(reader.read_frames()).shape == self.frame_shape[:2]

        # sub-sampled frame
        reader = VideoReader(folder, subsampling=2.0)
        assert next(reader.read_frames()).shape == (
            self.frame_shape[0] / 2,
            self.frame_shape[1] / 2,
            self.frame_shape[2],
        )

        # ROI around gaze position
        norm_pos = load_dataset(folder, gaze="recording").gaze_norm_pos
        reader = VideoReader(folder, norm_pos=norm_pos, roi_size=self.roi_size)
        assert next(reader.read_frames()).shape == (
            self.roi_size,
            self.roi_size,
            self.frame_shape[2],
        )

    def test_load_dataset(self, folder):
        """"""
        reader = VideoReader(folder, subsampling=8.0, color_format="gray")

        ds = reader.load_dataset(
            start=reader.user_info["experiment_start"],
            end=reader.user_info["experiment_end"],
        )

        assert dict(ds.sizes) == {"time": 22, "frame_x": 160, "frame_y": 90}

        assert set(ds.data_vars) == {"frames"}
        assert ds.frames.dtype == "uint8"

        # ROI around norm_pos
        norm_pos = load_dataset(folder, gaze="recording").gaze_norm_pos
        reader = VideoReader(folder, norm_pos=norm_pos, roi_size=self.roi_size)

        ds = reader.load_dataset(dropna=True)

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
        reader = OpticalFlowReader(folder)

        flow = reader.load_optical_flow(1)
        assert flow.shape == self.frame_shape

        # first frame
        flow = reader.load_optical_flow(0)
        assert flow.shape == self.frame_shape
        assert np.all(np.isnan(flow))

        # with timestamp
        t, flow = reader.load_optical_flow(1, return_timestamp=True)
        assert float(t.value) / 1e9 == 1570725800.2718818

        # invalid index
        with pytest.raises(ValueError):
            reader.load_optical_flow(self.n_frames)

    def test_read_optical_flow(self, folder):
        """"""
        norm_pos = load_dataset(folder, gaze="recording").gaze_norm_pos
        reader = OpticalFlowReader(
            folder, norm_pos=norm_pos, roi_size=self.roi_size
        )

        assert next(reader.read_optical_flow()).shape == (
            self.roi_size,
            self.roi_size,
            2,
        )

    def test_load_dataset(self, folder):
        """"""
        tqdm = pytest.importorskip("tqdm")

        reader = OpticalFlowReader(folder, subsampling=8.0)

        ds = reader.load_dataset(
            start=reader.user_info["experiment_start"],
            end=reader.user_info["experiment_end"],
        )

        assert dict(ds.sizes) == {
            "time": 22,
            "roi_x": 160,
            "roi_y": 90,
            "pixel_axis": 2,
        }
        assert ds.indexes["time"][0] >= reader.user_info["experiment_start"]
        assert ds.indexes["time"][-1] < reader.user_info["experiment_end"]
        assert set(ds.data_vars) == {"optical_flow"}

        # ROI around norm_pos
        norm_pos = load_dataset(folder, gaze="recording").gaze_norm_pos
        reader = OpticalFlowReader(
            folder, norm_pos=norm_pos, roi_size=self.roi_size
        )

        ds = reader.load_dataset(dropna=True, iter_wrapper=tqdm.tqdm)

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
        ds = reader.load_dataset(
            dropna=True,
            start=reader.user_info["experiment_start"],
            end=reader.user_info["experiment_end"],
        )

        assert ds.sizes["time"] == 21
