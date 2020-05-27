import sys
import logging

import pupil_recording_interface as pri


# Generation of your pupil device (1, 2 or 3)
pupil_gen = 1


if __name__ == "__main__":

    # stream configurations
    configs = [
        pri.VideoStream.Config(
            device_type="uvc",
            device_uid=f"Pupil Cam{pupil_gen} ID2",
            name="world",
            resolution=(1280, 720),
            fps=30,
            pipeline=[pri.VideoDisplay.Config()],
        ),
        pri.VideoStream.Config(
            device_type="uvc",
            device_uid=f"Pupil Cam{pupil_gen} ID0",
            name="eye0",
            resolution=(320, 240) if pupil_gen == 1 else (192, 192),
            fps=120,
            color_format="gray",
            pipeline=[pri.VideoDisplay.Config(flip=True)],
        ),
        pri.VideoStream.Config(
            device_type="uvc",
            device_uid=f"Pupil Cam{pupil_gen} ID1",
            name="eye1",
            resolution=(320, 240) if pupil_gen == 1 else (192, 192),
            fps=120,
            color_format="gray",
            pipeline=[pri.VideoDisplay.Config()],
        ),
    ]

    # set up logger
    logging.basicConfig(
        stream=sys.stdout, level=logging.INFO, format="%(message)s"
    )

    # run manager
    with pri.StreamManager(configs) as manager:
        while not manager.stopped:
            if manager.all_streams_running:
                status = manager.format_status(
                    "fps", format="{:.2f} Hz", max_cols=72, sleep=0.1
                )
                print("\r" + status, end="")

    print("\nStopped")
