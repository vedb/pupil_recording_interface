import sys
import logging

import pupil_recording_interface as pri


if __name__ == "__main__":

    # recording folder
    folder = "~/recordings/test"

    # stream configurations
    configs = [
        pri.VideoStream.Config(
            device_type="flir",
            device_uid=None,
            name="world",
            resolution=(2048, 1536),
            fps=55.0,
            color_format="bayer_rggb8",
            pipeline=[pri.VideoRecorder.Config(), pri.VideoDisplay.Config()],
        ),
    ]

    # set up logger
    logging.basicConfig(
        stream=sys.stdout, level=logging.DEBUG, format="%(message)s"
    )

    # run manager
    with pri.StreamManager(
        configs, folder=folder, policy="overwrite"
    ) as manager:
        while not manager.stopped:
            if manager.all_streams_running:
                status = manager.format_status("fps", max_cols=72, sleep=0.1)
                print("\r" + status, end="")

    print("\nStopped")
