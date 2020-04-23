import sys
import logging

import pupil_recording_interface as pri

calibration = {
    "params": (
        [
            -6.738264929857991,
            -4.2264581241890795,
            -5.5486309603733375,
            -3.2473320145810405,
            3.417235729846169,
            1.6015962595253193,
            10.348693009878701,
            -7.02733718171055,
            2.746040723426688,
            2.0297296825967663,
            8.80246647565474,
            -10.514537970421742,
            3.9300346599006772,
        ],
        [
            -7.949873359930862,
            -1.4242012442600114,
            11.094366725601603,
            8.063939210935196,
            1.828848523266707,
            -3.6891906511793593,
            13.78126334009248,
            -7.5191045459156385,
            -6.9505765561270145,
            -1.9829802720977412,
            -24.262175548531673,
            29.30846303630031,
            -0.2548744280007682,
        ],
        13,
    ),
    "params_eye0": (
        [
            0.2545660609977034,
            -1.692065643972036,
            0.7452694471609611,
            0.859410993254345,
            2.093522362589102,
            -1.4107165569726803,
            0.24442877728262147,
        ],
        [
            -1.6765382160065343,
            -3.4395112031020734,
            -0.27568454158500266,
            -1.0274006876870496,
            7.934803916404416,
            -6.119355482736768,
            2.2171886736110924,
        ],
        7,
    ),
    "params_eye1": (
        [
            -4.332300656161594,
            -1.8499127974740603,
            1.4700801800803973,
            0.5085799461646145,
            6.268217388705645,
            -8.06564396999261,
            1.8020472897303643,
        ],
        [
            8.449652694552814,
            9.626827571553935,
            -5.089628970478512,
            -3.509442219684155,
            -18.03533941720579,
            23.146000490697567,
            -3.256645030799435,
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
