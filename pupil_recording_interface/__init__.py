""""""
import os
from pathlib import Path

from .reader import BaseReader, _load_dataset
from .reader.motion import MotionReader
from .reader.gaze import GazeReader
from .reader.video import VideoReader, OpticalFlowReader

from .device.video import VideoDeviceUVC, VideoFileDevice
from .device.flir import VideoDeviceFLIR
from .device.realsense import RealSenseDeviceT265

from .stream import VideoStream, MotionStream
from .manager import StreamManager

from .pipeline import Pipeline

from .process.recorder import VideoRecorder, MotionRecorder
from .process.display import VideoDisplay
from .process.pupil_detector import PupilDetector
from .process.gaze_mapper import GazeMapper
from .process.circle_detector import CircleDetector
from .process.calibration import Calibration
from .process.cam_params import CircleGridDetector, CamParamEstimator

from .decorators import device, stream, process

from .session import Session

from ._version import __version__  # noqa

DATA_DIR = Path(__file__).parent / "data"
TEST_RECORDING = Path(DATA_DIR) / "test_recording"


__all__ = [
    # Functions
    "load_dataset",
    "load_info",
    "load_user_info",
    "write_netcdf",
    "get_gaze_mappers",
    # Readers
    "GazeReader",
    "MotionReader",
    "VideoReader",
    "OpticalFlowReader",
    # Devices
    "VideoDeviceUVC",
    "VideoFileDevice",
    "VideoDeviceFLIR",
    "RealSenseDeviceT265",
    # Streams
    "VideoStream",
    "MotionStream",
    "StreamManager",
    # Pipeline & processes
    "Pipeline",
    "VideoRecorder",
    "MotionRecorder",
    "VideoDisplay",
    "PupilDetector",
    "CircleDetector",
    "GazeMapper",
    "Calibration",
    "CircleGridDetector",
    "CamParamEstimator",
    # Decorators
    "device",
    "stream",
    "process",
    # other
    "Session",
]

# disable active threads when OpenCV is built with OpenMP support
os.environ["OMP_WAIT_POLICY"] = "PASSIVE"


def load_dataset(
    folder, gaze=None, odometry=None, accel=None, gyro=None, cache=False
):
    """ Load a recording as an xarray Dataset.

    Parameters
    ----------
    folder : str or pathlib.Path
        Path to the recording folder.

    gaze : str, optional
        The source of the gaze data. If 'recording', the recorded data will
        be used. Can also be the name of a gaze mapper or a dict in the
        format ``{'2d': '<2d_gaze_mapper>', '3d': '<3d_gaze_mapper>'}`` in
        which case the norm pos from the 2d mapper and the gaze point
        from the 3d mapper will be used.

    odometry : str, optional
        The source of the odometry data. Can be 'recording'.

    accel : str, optional
        The source of the accel data. Can be 'recording'.

    gyro : str, optional
        The source of the gyro data. Can be 'recording'.

    cache : bool, default False
        If True, cache datasets as netCDF files in the recording folder.

    Returns
    -------
    xarray.Dataset or tuple thereof
        The recording data as a dataset or tuple thereof if both `gaze` and
        `odometry` are specified.
    """
    folder = Path(folder)
    return_vals = tuple()

    if gaze:
        return_vals += (_load_dataset(folder, "gaze", gaze, cache),)

    if odometry:
        return_vals += (_load_dataset(folder, "odometry", odometry, cache),)

    if accel:
        return_vals += (_load_dataset(folder, "accel", accel, cache),)

    if gyro:
        return_vals += (_load_dataset(folder, "gyro", gyro, cache),)

    if len(return_vals) == 1:
        return_vals = return_vals[0]

    return return_vals


def get_gaze_mappers(folder):
    """ Get available gaze mappers for a recording.

    Parameters
    ----------
    folder : str or pathlib.Path
        Path to the recording folder.

    Returns
    -------
    set
        The set of available mappers.
    """
    folder = Path(folder)

    mappers = set(GazeReader._get_offline_gaze_mappers(folder).keys())
    if (folder / "gaze.pldata").exists():
        mappers = mappers.union({"recording"})

    return mappers


def write_netcdf(
    folder, output_folder=None, gaze=None, odometry=None, accel=None, gyro=None
):
    """ Export a recording in the netCDF format.

    Parameters
    ----------
    folder : str or pathlib.Path
        Path to the recording folder.

    output_folder : str, optional
        Path to the folder where the recording will be exported to. Defaults
        to ``<folder>/exports/<export_number>``.

    gaze : str, optional
        The source of the gaze data. If 'recording', the recorded data will
        be used. Can also be the name of a gaze mapper or a dict in the
        format ``{'2d': '<2d_gaze_mapper>', '3d': '<3d_gaze_mapper>'}`` in
        which case the norm pos from the 2d mapper and the gaze point
        from the 3d mapper will be used.

    odometry : str, optional
        The source of the odometry data. Can be 'recording'.

    accel : str, optional
        The source of the accel data. Can be 'recording'.

    gyro : str, optional
        The source of the gyro data. Can be 'recording'.
    """
    if output_folder is None:
        output_folder = Path(folder) / "exports"
        counter = 0
        while (output_folder / f"{counter:03d}").exists():
            counter += 1
        output_folder = output_folder / f"{counter:03d}"
    else:
        output_folder = Path(output_folder)

    if gaze is not None:
        GazeReader(folder, source=gaze).write_netcdf(
            filename=output_folder / "gaze.nc"
        )

    if odometry is not None:
        MotionReader(folder, "odometry", source=odometry).write_netcdf(
            filename=output_folder / "odometry.nc"
        )

    if accel is not None:
        MotionReader(folder, "accel", source=accel).write_netcdf(
            filename=output_folder / "accel.nc"
        )

    if gyro is not None:
        MotionReader(folder, "gyro", source=gyro).write_netcdf(
            filename=output_folder / "gyro.nc"
        )


def load_info(folder):
    """ Load recording info.

    Parameters
    ----------
    folder : str or pathlib.Path
        Path to the recording folder.

    Returns
    -------
    dict:
        The recording info.
    """
    return BaseReader(folder).info


def load_user_info(folder):
    """ Load user info.

    Parameters
    ----------
    folder : str or pathlib.Path
        Path to the recording folder.

    Returns
    -------
    dict:
        The user info.
    """
    return BaseReader(folder).user_info
