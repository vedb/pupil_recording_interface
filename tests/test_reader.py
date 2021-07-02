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
    PupilReader,
    MotionReader,
    VideoReader,
    OpticalFlowReader,
)


@pytest.fixture()
def test_data_folder():
    """"""
    return Path(__file__).parent / "test_data"


@pytest.fixture()
def t265_folder(test_data_folder):
    """"""
    return test_data_folder / "t265_test_recording"


@pytest.fixture()
def t265_export_folder(t265_folder):
    """"""
    export_folder = t265_folder / "exports"
    yield export_folder
    shutil.rmtree(export_folder, ignore_errors=True)


class TestBaseReader:
    def test_constructor(self, folder_v1):
        """"""
        exporter = BaseReader(folder_v1)
        assert exporter.folder == folder_v1

        with pytest.raises(FileNotFoundError):
            BaseReader("not_a_folder")

    def test_load_info(self, folder_v1, info):
        """"""
        loaded_info = BaseReader._load_info(folder_v1)
        assert loaded_info == info

        # legacy format
        loaded_info = BaseReader._load_info(folder_v1, "info.csv")
        loaded_info["duration_s"] = 21.111775958999715
        assert loaded_info == info

        with pytest.raises(FileNotFoundError):
            BaseReader._load_info(folder_v1, "not_a_file")

    def test_load_user_info(self, folder_v1, info):
        """"""
        user_info = BaseReader._load_user_info(
            folder_v1, info["start_time_system_s"]
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

    def test_timestamps_to_datetimeindex(self, folder_v1, info):
        """"""
        timestamps = np.array([2295.0, 2296.0, 2297.0])

        idx = BaseReader._timestamps_to_datetimeindex(timestamps, info)

        assert idx.values[0].astype(float) / 1e9 == 1570725800.4130569

    def test_load_timestamps_as_datetimeindex(self, folder_v1, info):
        """"""
        idx = BaseReader._load_timestamps_as_datetimeindex(
            folder_v1, "gaze", info
        )
        assert idx.values[0].astype(float) / 1e9 == 1570725800.149778

        # with offset
        idx_with_offs = BaseReader._load_timestamps_as_datetimeindex(
            folder_v1, "gaze", info, 1.0
        )
        assert np.all(idx_with_offs == idx + pd.to_timedelta("1s"))

        # source timestamps from pldata
        idx_world_source = BaseReader._load_timestamps_as_datetimeindex(
            folder_v1, "world", info
        )
        assert isinstance(idx_world_source, pd.DatetimeIndex)
        assert len(idx_world_source) == 504

        # source timestamps from pldata
        idx_world_monotonic = BaseReader._load_timestamps_as_datetimeindex(
            folder_v1, "world", info, use_pldata=False
        )
        assert isinstance(idx_world_monotonic, pd.DatetimeIndex)
        np.testing.assert_almost_equal(
            idx_world_monotonic.values.astype(float),
            idx_world_source.values.astype(float),
        )

        with pytest.raises(FileNotFoundError):
            BaseReader._load_timestamps_as_datetimeindex(
                folder_v1, "not_a_topic", info
            )

    def test_load_pldata(self, folder_v1):
        """"""
        data = BaseReader._load_pldata(folder_v1, "odometry")

        assert len(data) == 4220
        assert set(data[0].keys()) == {
            "topic",
            "timestamp",
            "confidence",
            "linear_velocity",
            "angular_velocity",
            "position",
            "orientation",
        }

    def test_save_pldata(self, folder_v1, export_folder_v1):
        """"""
        data = BaseReader._load_pldata(folder_v1, "odometry")
        BaseReader._save_pldata(export_folder_v1, "odometry", data)

        assert (export_folder_v1 / "odometry.pldata").exists()

    def test_load_pldata_as_dataframe(self, folder_v1):
        """"""
        df = BaseReader._load_pldata_as_dataframe(folder_v1, "odometry")

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
            BaseReader._load_pldata_as_dataframe(folder_v1, "not_a_topic")

    def test_get_encoding(self):
        """"""
        encoding = BaseReader._get_encoding(["test_var"])

        assert encoding["test_var"] == {
            "zlib": True,
            "dtype": "int32",
            "scale_factor": 0.0001,
            "_FillValue": np.iinfo("int32").min,
        }

    def test_write_netcdf(self, folder_v1, export_folder_v1):
        """"""
        pytest.importorskip("netCDF4")

        GazeReader(folder_v1).write_netcdf()

        ds = xr.open_dataset(export_folder_v1 / "000" / "gaze.nc")

        assert set(ds.data_vars) == {
            "eye",
            "eye0_center",
            "eye0_normal",
            "eye1_center",
            "eye1_normal",
            "gaze_confidence_3d",
            "gaze_norm_pos",
            "gaze_point",
        }

        ds.close()


class TestFunctionalReader:
    @pytest.mark.parametrize(
        "folder", ["folder_v1", "folder_v2"], indirect=True
    )
    def test_load_dataset(self, folder, t265_folder):
        """"""
        gaze, odometry = load_dataset(
            folder, gaze="recording", odometry="recording"
        )

        assert set(gaze.data_vars) == {
            "eye",
            "gaze_confidence_3d",
            "gaze_point",
            "eye0_center",
            "eye1_center",
            "eye0_normal",
            "eye1_normal",
            "gaze_norm_pos",
        }
        assert set(odometry.data_vars) == {
            "confidence",
            "linear_velocity",
            "angular_velocity",
            "position",
            "orientation",
        }

        # t265 recording
        odometry, accel, gyro = load_dataset(
            t265_folder,
            odometry="recording",
            accel="recording",
            gyro="recording",
        )
        assert set(odometry.data_vars) == {
            "confidence",
            "linear_acceleration",
            "angular_acceleration",
            "linear_velocity",
            "angular_velocity",
            "position",
            "orientation",
        }
        assert set(accel.data_vars) == {"linear_acceleration"}
        assert set(gyro.data_vars) == {"angular_velocity"}

    @pytest.mark.parametrize(
        "folder", ["folder_v1", "folder_v2"], indirect=True
    )
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
        self, folder_v1, t265_folder, export_folder_v1, t265_export_folder
    ):
        """"""
        pytest.importorskip("netCDF4")

        # packaged recording
        write_netcdf(folder_v1, gaze="recording", odometry="recording")
        assert (export_folder_v1 / "000" / "odometry.nc").exists()
        assert (export_folder_v1 / "000" / "gaze.nc").exists()

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

    @pytest.mark.parametrize(
        "folder", ["folder_v1", "folder_v2"], indirect=True
    )
    def test_get_gaze_mappers(self, folder):
        """"""
        mappers = get_gaze_mappers(str(folder))

        assert mappers == {"recording", "2d Gaze Mapper ", "3d Gaze Mapper"}


class TestGazeReader:
    @pytest.fixture(autouse=True)
    def set_up(self):
        """"""
        self.n_gaze = 5160
        self.n_gaze_offline = {"1.16": 5134, "2.0": 5125}
        self.n_gaze_merged = {"1.16": 5134, "2.0": 4987}
        self.gaze_mappers = {"2d": "2d Gaze Mapper ", "3d": "3d Gaze Mapper"}

    @pytest.mark.parametrize(
        "folder", ["folder_v1", "folder_v2"], indirect=True
    )
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

    def test_load_gaze(self, folder_v1, t265_folder):
        """"""
        data = GazeReader._load_gaze(folder_v1)

        assert data["timestamp"].shape == (self.n_gaze,)
        assert data["confidence"].shape == (self.n_gaze,)
        assert data["norm_pos"].shape == (self.n_gaze, 2)
        assert data["eye"].shape == (self.n_gaze,)
        assert data["gaze_point"].shape == (self.n_gaze, 3)
        assert data["eye0_center"].shape == (self.n_gaze, 3)
        assert data["eye1_center"].shape == (self.n_gaze, 3)
        assert data["eye0_normal"].shape == (self.n_gaze, 3)
        assert data["eye1_normal"].shape == (self.n_gaze, 3)

        assert set(np.unique(data["eye"])) == {0, 1, 2}

        # no gaze
        with pytest.raises(FileNotFoundError):
            GazeReader._load_gaze(t265_folder)

    def test_load_binocular_only_gaze(self, test_data_folder):
        """ Regression test for 3D gaze without monocular data. """
        data = GazeReader._load_gaze(test_data_folder, "binocular_only_gaze")

        assert data["timestamp"].shape == (665,)

    @pytest.mark.parametrize(
        "folder", ["folder_v1", "folder_v2"], indirect=True
    )
    def test_load_merged_gaze(self, folder):
        """"""
        data = GazeReader._load_merged_gaze(folder, self.gaze_mappers)
        version = GazeReader(folder).info["min_player_version"]
        n = self.n_gaze_merged[version]

        assert data["timestamp"].shape == (n,)
        assert data["confidence_2d"].shape == (n,)
        assert data["confidence_3d"].shape == (n,)
        assert data["norm_pos"].shape == (n, 2)
        assert data["eye"].shape == (n,)
        assert data["gaze_point"].shape == (n, 3)
        assert data["eye0_center"].shape == (n, 3)
        assert data["eye1_center"].shape == (n, 3)
        assert data["eye0_normal"].shape == (n, 3)
        assert data["eye1_normal"].shape == (n, 3)

    @pytest.mark.parametrize(
        "folder", ["folder_v1", "folder_v2"], indirect=True
    )
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

    @pytest.mark.parametrize(
        "folder", ["folder_v1", "folder_v2"], indirect=True
    )
    def test_load_dataset(self, folder):
        """"""
        version = GazeReader(folder).info["min_player_version"]

        # from recording
        ds = GazeReader(folder).load_dataset()
        assert dict(ds.sizes) == {
            "time": self.n_gaze,
            "cartesian_axis": 3,
            "pixel_axis": 2,
        }
        assert set(ds.data_vars) == {
            "eye",
            "gaze_confidence_3d",
            "gaze_point",
            "eye0_center",
            "eye1_center",
            "eye0_normal",
            "eye1_normal",
            "gaze_norm_pos",
        }

        # offline 2d mapper
        ds = GazeReader(folder, source=self.gaze_mappers["2d"]).load_dataset()
        assert dict(ds.sizes) == {
            "time": self.n_gaze_offline[version],
            "pixel_axis": 2,
        }
        assert set(ds.data_vars) == {
            "eye",
            "gaze_confidence_2d",
            "gaze_norm_pos",
        }

        # merged 2d/3d gaze
        ds = GazeReader(folder, source=self.gaze_mappers).load_dataset()
        assert dict(ds.sizes) == {
            "time": self.n_gaze_merged[version],
            "cartesian_axis": 3,
            "pixel_axis": 2,
        }
        assert set(ds.data_vars) == {
            "eye",
            "gaze_confidence_2d",
            "gaze_confidence_3d",
            "gaze_point",
            "eye0_center",
            "eye1_center",
            "eye0_normal",
            "eye1_normal",
            "gaze_norm_pos",
        }

        # bad gaze argument
        with pytest.raises(ValueError):
            GazeReader(folder, source="not_gaze_mapper").load_dataset()

    def test_write_netcdf(self, folder_v1, export_folder_v1):
        """"""
        pytest.importorskip("netCDF4")

        GazeReader(folder_v1).write_netcdf()
        ds = xr.open_dataset(export_folder_v1 / "000" / "gaze.nc")
        assert set(ds.data_vars) == {
            "eye",
            "gaze_confidence_3d",
            "gaze_point",
            "eye0_center",
            "eye1_center",
            "eye0_normal",
            "eye1_normal",
            "gaze_norm_pos",
        }

        ds.close()


class TestPupilReader:
    @pytest.fixture(autouse=True)
    def set_up(self):
        """"""
        self.n_pupil_2d = 5164
        self.n_pupil_3d = 5170
        self.n_pupil_pye3d = 5164

    def test_load_pupil(self, folder_v1, folder_v2):
        """"""
        # v1 3d
        data = PupilReader._load_pupil(folder_v1, "3d")
        assert data["timestamp"].shape == (self.n_pupil_3d,)
        assert data["confidence"].shape == (self.n_pupil_3d,)
        assert data["norm_pos"].shape == (self.n_pupil_3d, 2)
        assert data["eye"].shape == (self.n_pupil_3d,)
        assert data["diameter"].shape == (self.n_pupil_3d,)
        assert data["model_birth_timestamp"].shape == (self.n_pupil_3d,)

        # v2 2d
        data = PupilReader._load_pupil(
            folder_v2 / "offline_data", "2d", "offline_pupil"
        )
        assert data["timestamp"].shape == (self.n_pupil_2d,)
        assert data["confidence"].shape == (self.n_pupil_2d,)
        assert data["norm_pos"].shape == (self.n_pupil_2d, 2)
        assert data["eye"].shape == (self.n_pupil_2d,)
        assert data["diameter"].shape == (self.n_pupil_2d,)

        # v2 pye3d
        data = PupilReader._load_pupil(
            folder_v2 / "offline_data", "pye3d", "offline_pupil"
        )
        assert data["timestamp"].shape == (self.n_pupil_pye3d,)
        assert data["confidence"].shape == (self.n_pupil_pye3d,)
        assert data["norm_pos"].shape == (self.n_pupil_pye3d, 2)
        assert data["eye"].shape == (self.n_pupil_pye3d,)
        assert data["diameter"].shape == (self.n_pupil_pye3d,)
        assert data["location"].shape == (self.n_pupil_pye3d, 2)

    def test_load_dataset(self, folder_v1, folder_v2):
        """"""
        # from recording
        ds = PupilReader(folder_v1, method="3d").load_dataset()
        assert dict(ds.sizes) == {
            "time": self.n_pupil_3d,
            "cartesian_axis": 3,
            "pixel_axis": 2,
        }
        assert set(ds.data_vars) == {
            "circle_center",
            "circle_normal",
            "circle_radius",
            "confidence",
            "diameter",
            "diameter_3d",
            "ellipse_angle",
            "ellipse_axes",
            "ellipse_center",
            "eye",
            "model_birth_timestamp",
            "model_confidence",
            "phi",
            "projected_sphere_angle",
            "projected_sphere_axes",
            "projected_sphere_center",
            "pupil_norm_pos",
            "sphere_center",
            "sphere_radius",
            "theta",
        }

        # offline 2d
        ds = PupilReader(
            folder_v2, source="offline", method="2d"
        ).load_dataset()
        assert dict(ds.sizes) == {
            "time": self.n_pupil_2d,
            "pixel_axis": 2,
        }
        assert set(ds.data_vars) == {
            "confidence",
            "diameter",
            "ellipse_angle",
            "ellipse_axes",
            "ellipse_center",
            "eye",
            "pupil_norm_pos",
        }

        # offline pye3d
        ds = PupilReader(folder_v2, source="offline").load_dataset()
        assert dict(ds.sizes) == {
            "time": self.n_pupil_pye3d,
            "cartesian_axis": 3,
            "pixel_axis": 2,
        }
        assert set(ds.data_vars) == {
            "circle_center",
            "circle_normal",
            "circle_radius",
            "confidence",
            "diameter",
            "diameter_3d",
            "ellipse_angle",
            "ellipse_axes",
            "ellipse_center",
            "eye",
            "location",
            "model_confidence",
            "phi",
            "projected_sphere_angle",
            "projected_sphere_axes",
            "projected_sphere_center",
            "pupil_norm_pos",
            "sphere_center",
            "sphere_radius",
            "theta",
        }

        # bad gaze argument
        with pytest.raises(ValueError):
            PupilReader(folder_v1, source="not_a_pupil_source").load_dataset()


class TestMotionReader:
    @pytest.fixture(autouse=True)
    def set_up(self):
        """"""
        self.n_odometry_legacy = 4220
        self.n_odometry = 5850
        self.n_accel = 1939
        self.n_gyro = 5991

    def test_load_data(self, folder_v1, t265_folder):
        """"""
        # legacy odometry
        data = MotionReader._load_data(folder_v1)
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

    def test_load_dataset(self, folder_v1, t265_folder):
        """"""
        # legacy odometry
        ds = MotionReader(folder_v1).load_dataset()
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
            MotionReader(folder_v1, source="not_supported").load_dataset()


class TestVideoReader:
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

    def test_get_capture(self, folder_v1):
        """"""
        capture = VideoReader._get_capture(folder_v1, "world")

        assert isinstance(capture, cv2.VideoCapture)

        with pytest.raises(FileNotFoundError):
            VideoReader._get_capture(folder_v1, "not_a_topic")

    def test_resolution(self, folder_v1):
        """"""
        resolution = VideoReader(folder_v1, "world").resolution
        assert resolution == self.frame_shape[-2::-1]
        assert isinstance(resolution[0], int)
        assert isinstance(resolution[1], int)

    def test_frame_count(self, folder_v1):
        """"""
        frame_count = VideoReader(folder_v1, "world").frame_count
        assert frame_count == self.n_frames
        assert isinstance(frame_count, int)

    def test_frame_shape(self, folder_v1):
        """"""
        shape = VideoReader(folder_v1).frame_shape
        assert shape == self.frame_shape

    def test_fps(self, folder_v1):
        """"""
        fps = VideoReader(folder_v1).fps
        assert fps == self.fps

    def test_current_frame_index(self, folder_v1):
        """"""
        reader = VideoReader(folder_v1)
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

    def test_get_bounds(self, folder_v1):
        """"""
        reader = VideoReader(folder_v1, roi_size=self.roi_size)

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

    def test_get_frame_index(self, folder_v1):
        """"""
        reader = VideoReader(folder_v1)
        assert reader._get_frame_index(None) == 0
        assert reader._get_frame_index(None, default=1) == 1
        assert reader._get_frame_index(1) == 1
        assert reader._get_frame_index(reader.timestamps[2]) == 2

    def test_get_roi(self, folder_v1):
        """"""
        frame = np.random.rand(512, 512)
        reader = VideoReader(folder_v1, roi_size=self.roi_size)

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

    def test_load_raw_frame(self, folder_v1):
        """"""
        reader = VideoReader(folder_v1)
        frame = reader.load_raw_frame()
        assert frame.shape == self.frame_shape

        reader = VideoReader(folder_v1)
        frame_by_idx = reader.load_raw_frame(0)
        npt.assert_equal(frame_by_idx, frame)

        # invalid index
        with pytest.raises(ValueError):
            reader.load_raw_frame(self.n_frames)

    def test_load_frame(self, folder_v1):
        """"""
        reader = VideoReader(folder_v1)
        frame = reader.load_frame()
        assert frame.shape == self.frame_shape

        frame_by_idx = reader.load_frame(0)
        npt.assert_equal(frame_by_idx, frame)

        # timestamp
        frame_by_ts = reader.load_frame(reader.timestamps[0])
        npt.assert_equal(frame_by_ts, frame)

        # ROI around norm pos
        norm_pos = load_dataset(folder_v1, gaze="recording").gaze_norm_pos
        reader = VideoReader(
            folder_v1, norm_pos=norm_pos, roi_size=self.roi_size
        )
        frame = reader.load_frame(0)
        assert frame.shape == (
            self.roi_size,
            self.roi_size,
            self.frame_shape[2],
        )

        # with timestamp
        reader = VideoReader(folder_v1)
        t, frame = reader.load_frame(0, return_timestamp=True)
        assert float(t.value) / 1e9 == 1570725800.2383718

    def test_read_frames(self, folder_v1):
        """"""
        # TODO move this to process_frame test
        # full frame
        reader = VideoReader(folder_v1)
        assert next(reader.read_frames()).shape == self.frame_shape

        # grayscale
        reader = VideoReader(folder_v1, color_format="gray")
        assert next(reader.read_frames()).shape == self.frame_shape[:2]

        # sub-sampled frame
        reader = VideoReader(folder_v1, subsampling=2.0)
        assert next(reader.read_frames()).shape == (
            self.frame_shape[0] / 2,
            self.frame_shape[1] / 2,
            self.frame_shape[2],
        )

        # ROI around gaze position
        norm_pos = load_dataset(folder_v1, gaze="recording").gaze_norm_pos
        reader = VideoReader(
            folder_v1, norm_pos=norm_pos, roi_size=self.roi_size
        )
        assert next(reader.read_frames()).shape == (
            self.roi_size,
            self.roi_size,
            self.frame_shape[2],
        )

        # raw
        assert next(reader.read_frames(raw=True)).dtype == np.uint8

        # with timestamp
        _, ts = next(reader.read_frames(return_timestamp=True))
        assert ts == pd.Timestamp("2019-10-10 16:43:20.238371849")

    def test_load_dataset(self, folder_v1):
        """"""
        reader = VideoReader(folder_v1, subsampling=8.0, color_format="gray")

        ds = reader.load_dataset(
            start=reader.user_info["experiment_start"],
            end=reader.user_info["experiment_end"],
        )

        assert dict(ds.sizes) == {"time": 22, "frame_x": 160, "frame_y": 90}
        assert set(ds.data_vars) == {"frames"}
        assert ds.frames.dtype == "uint8"

        # ROI around norm_pos
        norm_pos = load_dataset(folder_v1, gaze="recording").gaze_norm_pos
        reader = VideoReader(
            folder_v1, norm_pos=norm_pos, roi_size=self.roi_size
        )

        ds = reader.load_dataset(dropna=True)

        assert dict(ds.sizes) == {
            "time": self.n_valid_frames,
            "frame_x": self.roi_size,
            "frame_y": self.roi_size,
            "color": 3,
        }

        assert set(ds.data_vars) == {"frames"}
        assert ds.frames.dtype == "uint8"


class TestOpticalFlowReader:
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

    def test_load_optical_flow(self, folder_v1):
        """"""
        reader = OpticalFlowReader(folder_v1)

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

    def test_read_optical_flow(self, folder_v1):
        """"""
        norm_pos = load_dataset(folder_v1, gaze="recording").gaze_norm_pos
        reader = OpticalFlowReader(
            folder_v1, norm_pos=norm_pos, roi_size=self.roi_size
        )

        assert next(reader.read_optical_flow()).shape == (
            self.roi_size,
            self.roi_size,
            2,
        )

    def test_load_dataset(self, folder_v1):
        """"""
        tqdm = pytest.importorskip("tqdm")

        reader = OpticalFlowReader(folder_v1, subsampling=8.0)

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
        norm_pos = load_dataset(folder_v1, gaze="recording").gaze_norm_pos
        reader = OpticalFlowReader(
            folder_v1, norm_pos=norm_pos, roi_size=self.roi_size
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
