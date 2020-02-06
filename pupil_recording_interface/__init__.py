""""""
import os
import sys

from .base import BaseInterface
from .odometry import OdometryInterface, OdometryRecorder
from .gaze import GazeInterface
from .video import VideoInterface, OpticalFlowInterface
from .cli import CLI
from . import control

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
TEST_RECORDING = os.path.join(DATA_DIR, 'test_recording')


__all__ = [
    'load_dataset',
    'load_info',
    'load_user_info',
    'write_netcdf',
    'get_gaze_mappers',
    'GazeInterface',
    'OdometryInterface',
    'VideoInterface',
    'OpticalFlowInterface',
    'OdometryRecorder'
]


def _run_cli():
    """ CLI entry point. """
    CLI().run(sys.argv)


def load_dataset(folder, gaze=None, odometry=None):
    """ Load a recording as an xarray Dataset.

    Parameters
    ----------
    folder : str
        Path to the recording folder.

    gaze : str, optional
        The source of the gaze data. If 'recording', the recorded data will
        be used. Can also be the name of a gaze mapper or a dict in the
        format ``{'2d': '<2d_gaze_mapper>', '3d': '<3d_gaze_mapper>'}`` in
        which case the norm pos from the 2d mapper and the gaze point
        from the 3d mapper will be used.

    odometry : str, optional
        The source of the odometry data. Can be 'recording'.

    Returns
    -------
    xarray.Dataset or tuple thereof
        The recording data as a dataset or tuple thereof if both `gaze` and
        `odometry` are specified.
    """
    return_vals = tuple()
    if gaze is not None:
        return_vals += (
            GazeInterface(folder, source=gaze).load_dataset(),)
    if odometry is not None:
        return_vals += (
            OdometryInterface(folder, source=odometry).load_dataset(),)

    if len(return_vals) == 1:
        return_vals = return_vals[0]

    return return_vals


def get_gaze_mappers(folder):
    """ Get available gaze mappers for a recording.

    Parameters
    ----------
    folder : str
        Path to the recording folder.

    Returns
    -------
    set
        The set of available mappers.
    """
    mappers = set(GazeInterface._get_offline_gaze_mappers(folder).keys())
    if os.path.exists(os.path.join(folder, 'gaze.pldata')):
        mappers = mappers.union({'recording'})

    return mappers


def write_netcdf(folder, output_folder=None, gaze=None, odometry=None):
    """ Export a recording in the netCDF format.

    Parameters
    ----------
    folder : str
        Path to the recording folder.

    output_folder : str, optional
        Path to the folder where the recording will be exported to. Defaults
        to ``<folder>/exports``.

    gaze : str, optional
        The source of the gaze data. If 'recording', the recorded data will
        be used. Can also be the name of a gaze mapper or a dict in the
        format ``{'2d': '<2d_gaze_mapper>', '3d': '<3d_gaze_mapper>'}`` in
        which case the norm pos from the 2d mapper and the gaze point
        from the 3d mapper will be used.

    odometry : str, optional
        The source of the odometry data. Can be 'recording'.
    """
    if gaze is not None:
        if output_folder is not None:
            filename = os.path.join(output_folder, 'gaze.nc')
        else:
            filename = None
        GazeInterface(
            folder, source=gaze).write_netcdf(filename=filename)
    if odometry is not None:
        if output_folder is not None:
            filename = os.path.join(output_folder, 'odometry.nc')
        else:
            filename = None
        OdometryInterface(
            folder, source=odometry).write_netcdf(filename=filename)


def load_info(folder):
    """ Load recording info.

    Parameters
    ----------
    folder : str
        Path to the recording folder.

    Returns
    -------
    dict:
        The recording info.
    """
    return BaseInterface(folder).info


def load_user_info(folder):
    """ Load user info.

    Parameters
    ----------
    folder : str
        Path to the recording folder.

    Returns
    -------
    dict:
        The user info.
    """
    return BaseInterface(folder).user_info
