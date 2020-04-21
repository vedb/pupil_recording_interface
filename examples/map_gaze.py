import sys
import logging

import pupil_recording_interface as pri

calibration = {
    "params": (
        [
            -3.35928987346593,
            -1.1351383146598142,
            7.310356444411848,
            2.3389624689520137,
            1.3113593590371355,
            -0.5504925310404138,
            4.3069512959267335,
            -0.9988818152557206,
            -5.0902731406085255,
            -0.002750427387054888,
            -11.913667258028237,
            10.092069157588433,
            0.2080563725891711,
        ],
        [
            4.48087234430592,
            4.289194588553814,
            10.819043222013162,
            4.716892688492897,
            -2.8935293316310586,
            -3.2974121550865902,
            -7.164875148012609,
            6.668757528029424,
            -6.480144272184081,
            -0.2587913571678879,
            -14.6910780411297,
            11.303527790078121,
            -4.1484171911043735,
        ],
        13,
    ),
    "params_eye0": (
        [
            -6.820045825838425,
            -6.550791754871567,
            4.1695394177690295,
            2.696179482451249,
            12.07406236220669,
            -9.099101340812267,
            2.954521501399384,
        ],
        [
            26.381639978780594,
            15.010877066093451,
            -13.40834511950758,
            -5.726140445953507,
            -38.903473060829036,
            28.812469577728127,
            -7.221855520759918,
        ],
        7,
    ),
    "params_eye1": (
        [
            5.253611025330999,
            2.480280716538997,
            -4.903028618701357,
            -0.6979309979838311,
            -10.390443329051537,
            11.476187075482532,
            -0.32886364311635286,
        ],
        [
            7.1130549229305835,
            4.252168617268895,
            -4.379543368150065,
            0.025930758747446603,
            -8.524437903708622,
            6.070923918531467,
            -2.8201184323091137,
        ],
        7,
    ),
}


if __name__ == "__main__":

    # recording folder
    folder = "~/recordings/test"

    # stream configurations
    configs = [
        pri.VideoStream.Config(
            device_type="uvc",
            device_uid="Pupil Cam1 ID2",
            name="world",
            resolution=(1280, 720),
            fps=60,
            pipeline=[
                pri.GazeMapper.Config(record=True, calibration=calibration),
                pri.VideoDisplay.Config(overlay_gaze=True),
            ],
        ),
        pri.VideoStream.Config(
            device_type="uvc",
            device_uid="Pupil Cam1 ID0",
            name="eye0",
            resolution=(320, 240),
            fps=120,
            color_format="gray",
            pipeline=[
                pri.PupilDetector.Config(record=True),
                pri.VideoDisplay.Config(flip=True, overlay_pupil=True),
            ],
        ),
        pri.VideoStream.Config(
            device_type="uvc",
            device_uid="Pupil Cam1 ID1",
            name="eye1",
            resolution=(320, 240),
            fps=120,
            color_format="gray",
            pipeline=[
                pri.PupilDetector.Config(record=True),
                pri.VideoDisplay.Config(overlay_pupil=True),
            ],
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
                status = manager.format_status("pupil.confidence", max_cols=72)
                print("\r" + status, end="")

    print("\nStopped")
