""""""
import sys

from .video import VideoRecorder
from .odometry import OdometryRecorder
from .multi_stream import MultiStreamRecorder
from .cli import CLI

__all__ = ["VideoRecorder", "OdometryRecorder", "MultiStreamRecorder", "CLI"]


def _run_cli():
    """ CLI entry point. """
    CLI().run(sys.argv)
