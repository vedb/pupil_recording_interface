""""""
import sys

from .video import VideoRecorder
from .odometry import OdometryRecorder
from .multi_stream import MultiStreamRecorder
from .cli import CLI
from .config import (
    StreamConfig,
    VideoConfig,
    OdometryConfig,
    VideoRecorderConfig,
    OdometryRecorderConfig,
    VideoDisplayConfig,
    PupilDetectorConfig,
)

__all__ = [
    "VideoRecorder",
    "OdometryRecorder",
    "MultiStreamRecorder",
    "CLI",
    # Configs
    "StreamConfig",
    "VideoConfig",
    "OdometryConfig",
    "VideoRecorderConfig",
    "OdometryRecorderConfig",
    "VideoDisplayConfig",
    "PupilDetectorConfig",
]


def _run_cli():
    """ CLI entry point. """
    CLI().run(sys.argv)
