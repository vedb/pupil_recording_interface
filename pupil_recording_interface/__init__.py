""""""
import warnings
from pathlib import Path

from .reader import BaseReader, _load_dataset
from .reader.motion import MotionReader
from .reader.gaze import GazeReader
from .reader.marker import MarkerReader
from .reader.pupil import PupilReader
from .reader.video import VideoReader, OpticalFlowReader

from .device.video import VideoDeviceUVC, VideoFileDevice
from .device.flir import VideoDeviceFLIR
from .device.realsense import RealSenseDeviceT265

from .stream import VideoStream, MotionStream
from .manager import StreamManager

from .pipeline import Pipeline

from .process.helpers import VideoFileSyncer
from .process.recorder import VideoRecorder, MotionRecorder
from .process.display import VideoDisplay
from .process.pupil_detector import PupilDetector
from .process.gaze_mapper import GazeMapper
from .process.circle_detector import CircleDetector
from .process.calibration import Calibration
from .process.cam_params import CircleGridDetector, CamParamEstimator

from .decorators import device, stream, process

from .session import Session

from .utils import get_test_recording, merge_pupils

from .externals.file_methods import load_object as _load_object
from .externals.file_methods import save_object as _save_object

from ._version import __version__  # noqa


__all__ = [
    # Functions
    "load_dataset",
    "load_info",
    "load_user_info",
    "load_pldata",
    "save_pldata",
    "write_netcdf",
    "get_gaze_mappers",
    "load_object",
    "save_object",
    # Readers
    "GazeReader",
    "PupilReader",
    "MarkerReader",
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
    "Validation",
    "CircleGridDetector",
    "CamParamEstimator",
    "VideoFileSyncer",
    # Decorators
    "device",
    "stream",
    "process",
    # other
    "Session",
    "get_test_recording",
    "merge_pupils",
]


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
        The recording data as a dataset or tuple thereof if multiple sources
        (`gaze`, `odometry`, ...) are specified.
    """
    warnings.warn(
        DeprecationWarning(
            "load_dataset is deprecated, use load_gaze, load_pupils, "
            "load_markers or load_motion instead"
        )
    )

    folder = Path(folder).expanduser()
    return_vals = tuple()

    if gaze:
        return_vals += (_load_dataset(folder, "gaze", gaze, None, cache),)

    if odometry:
        return_vals += (
            _load_dataset(folder, "odometry", odometry, None, cache),
        )

    if accel:
        return_vals += (_load_dataset(folder, "accel", accel, None, cache),)

    if gyro:
        return_vals += (_load_dataset(folder, "gyro", gyro, None, cache),)

    if len(return_vals) == 1:
        return_vals = return_vals[0]

    return return_vals


def load_gaze(folder, source="recording", cache=False):
    """ Load gaze data as an xarray.Dataset.

    Parameters
    ----------
    folder : str or pathlib.Path
        Path to the recording folder.

    source : str, default "recording"
        The source of the gaze data. If 'recording', the recorded data will
        be used. Can also be the name of a gaze mapper or a dict in the
        format ``{'2d': '<2d_gaze_mapper>', '3d': '<3d_gaze_mapper>'}`` in
        which case the norm pos from the 2d mapper and the gaze point
        from the 3d mapper will be used.

    cache : bool, default False
        If True, cache the dataset as a netCDF file in the recording folder.

    Returns
    -------
    xarray.Dataset
        The gaze data as a dataset.
    """
    return _load_dataset(folder, "gaze", source, None, cache)


def load_pupils(folder, source="recording", method="pye3d", cache=False):
    """ Load pupil data as an xarray.Dataset.

    Parameters
    ----------
    folder : str or pathlib.Path
        Path to the recording folder.

    source : str, default "recording"
        The source of the pupil data. Can be "recording" or "offline".

    cache : bool, default False
        If True, cache the dataset as a netCDF file in the recording folder.

    Returns
    -------
    xarray.Dataset
        The pupil data as a dataset.
    """
    return _load_dataset(folder, "pupil", source, method, cache)


def load_markers(folder, cache=False):
    """ Load calibration marker data as an xarray.Dataset.

    Parameters
    ----------
    folder : str or pathlib.Path
        Path to the recording folder.

    cache : bool, default False
        If True, cache the dataset as a netCDF file in the recording folder.

    Returns
    -------
    xarray.Dataset
        The pupil data as a dataset.
    """
    return _load_dataset(folder, "marker", "offline", None, cache)


def load_motion(folder, stream="odometry", cache=False):
    """ Load pupil data as an xarray.Dataset.

    Parameters
    ----------
    folder : str or pathlib.Path
        Path to the recording folder.

    stream : str, default "odometry"
        The motion stream to load.

    cache : bool, default False
        If True, cache the dataset as a netCDF file in the recording folder.

    Returns
    -------
    xarray.Dataset
        The pupil data as a dataset.
    """
    return _load_dataset(folder, stream, "recording", None, cache)


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
    folder = Path(folder).expanduser()
    if not folder.exists():
        raise FileNotFoundError(f"No such folder: {folder}")

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
        output_folder = Path(folder).expanduser() / "exports"
        counter = 0
        while (output_folder / f"{counter:03d}").exists():
            counter += 1
        output_folder = output_folder / f"{counter:03d}"
    else:
        output_folder = Path(output_folder).expanduser()

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


def load_pldata(folder, topic):
    """ Load data from a .pldata file as a list of dicts.

    Parameters
    ----------
    folder : str or pathlib.Path
        Path to the recording folder.

    topic : str
        The topic to load, e.g. "gaze".

    Returns
    -------
    data : list of dict
        The loaded data.
    """
    return BaseReader(folder).load_pldata(topic)


def save_pldata(folder, topic, data):
    """ Save data from a list of dicts as a .pldata file.

    Parameters
    ----------
    folder : str or pathlib.Path
        Path to the recording folder.

    topic : str
        The topic to load, e.g. "gaze".

    data : list of dict
        The data to be saved.
    """
    BaseReader(folder).save_pldata(topic, data)


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
    dict :
        The user info.
    """
    return BaseReader(folder).user_info


def load_object(filepath):
    """ Load a msgpack object (intrinsics, calibration, etc.).

    Parameters
    ----------
    filepath : str or pathlib.Path
        Path to the msgpack file.

    Returns
    -------
    obj :
        The loaded data
    """
    return _load_object(filepath)


def save_object(obj, filepath):
    """ Save data as a msgpack object (intrinsics, calibration, etc.).

    Parameters
    ----------
    obj :
        The object to save

    filepath : str or pathlib.Path
        Path to the msgpack file.
    """
    return _save_object(obj, filepath)
