""""""
import argparse

from pupil_recording_interface import (
    OdometryRecorder,
    OdometryReader,
    GazeReader,
    VideoReader,
)


class CLI(object):
    def run(self, argv):
        """"""
        parser = argparse.ArgumentParser("pri")
        parser.add_argument("command", help="Command to execute.")

        # parse_args defaults to [1:] for args, but you need to
        # exclude the rest of the args too, or validation will fail
        args = parser.parse_args(argv[1:2])
        if not hasattr(self, args.command):
            parser.error("Unrecognized command: {}".format(args.command))

        # use dispatch pattern to invoke method with same name
        try:
            getattr(self, args.command)(argv)
        except Exception as e:
            parser.error(str(e))

    @staticmethod
    def record(argv):
        """"""
        parser = argparse.ArgumentParser("pri record")
        parser.add_argument("topic", help="Topic to record.")
        parser.add_argument("folder", help="Path to the recording folder.")
        parser.add_argument(
            "-q",
            "--quiet",
            action="store_false",
            help="Set this flag to suppress output",
        )

        args = parser.parse_args(argv[2:])

        if args.topic == "odometry":
            OdometryRecorder(args.folder, verbose=args.quiet).run()
        else:
            raise ValueError("Unsupported topic: {}".format(args.topic))

    @staticmethod
    def export(argv):
        """"""
        parser = argparse.ArgumentParser("pri export")
        parser.add_argument("topic", help="Topic to export.")
        parser.add_argument("folder", help="Path to the recording folder.")
        parser.add_argument(
            "-s", "--source", help="Data source.", default="recording"
        )
        parser.add_argument(
            "-f", "--format", help="Export format.", default="nc"
        )
        parser.add_argument(
            "-o", "--output_file", help="Output file.", default=None
        )

        args = parser.parse_args(argv[2:])

        if args.topic == "gaze":
            interface = GazeReader(args.folder, source=args.source)
        elif args.topic == "video":
            interface = VideoReader(args.folder, source=args.source)
        elif args.topic == "odometry":
            interface = OdometryReader(args.folder, source=args.source)
        else:
            raise ValueError("Unsupported topic: {}".format(args.topic))

        if args.format in ("nc", "netcdf"):
            interface.write_netcdf(filename=args.output_file)
        else:
            raise ValueError("Unsupported format: {}".format(args.format))
