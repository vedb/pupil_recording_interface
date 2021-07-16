import shutil
from pathlib import Path
from time import monotonic
from collections import deque

import pytest
import numpy as np

from pupil_recording_interface.decorators import device, stream, process
from pupil_recording_interface.device import BaseDevice
from pupil_recording_interface.device.video import VideoFileDevice
from pupil_recording_interface.stream import (
    BaseStream,
    VideoStream,
    MotionStream,
)
from pupil_recording_interface.packet import Packet
from pupil_recording_interface.pipeline import Pipeline
from pupil_recording_interface.process.display import VideoDisplay
from pupil_recording_interface.process.pupil_detector import PupilDetector
from pupil_recording_interface.process.recorder import VideoRecorder
from pupil_recording_interface.process.gaze_mapper import GazeMapper
from pupil_recording_interface.process.circle_detector import CircleDetector
from pupil_recording_interface.process.calibration import Calibration
from pupil_recording_interface.process.validation import Validation
from pupil_recording_interface.process.cam_params import (
    CamParamEstimator,
    CircleGridDetector,
)
from pupil_recording_interface.manager import StreamManager
from pupil_recording_interface.utils import get_test_recording
from pupil_recording_interface.externals.file_methods import (
    load_object,
    load_pldata_file,
)
from pupil_recording_interface.externals.methods import normalize


class MockMultiprocessingDeque(deque):
    def _getvalue(self):
        return len(self) > 0


@device("mock_device")
class MockDevice(BaseDevice):
    @property
    def is_started(self):
        return True


@device("mock_video_device")
class MockVideoDevice(MockDevice):

    resolution = (1280, 720)
    fps = 30


@stream("mock_stream")
class MockStream(BaseStream):
    def get_packet(self):
        return Packet(self.name, self.device.device_uid, monotonic())


@pytest.fixture()
def mock_mp_deque():
    """"""
    return MockMultiprocessingDeque


@pytest.fixture
def folder(request):
    """"""
    return request.getfixturevalue(request.param)


@pytest.fixture()
def folder_v1():
    """"""
    return get_test_recording("1.16")


@pytest.fixture()
def folder_v2():
    """"""
    return get_test_recording("2.0")


@pytest.fixture()
def export_folder_v1(folder_v1):
    """"""
    export_folder = Path(folder_v1) / "exports"
    export_folder.mkdir()
    yield export_folder
    shutil.rmtree(export_folder, ignore_errors=True)


@pytest.fixture()
def info():
    """"""
    return {
        "duration_s": 21.111775958999715,
        "meta_version": "2.0",
        "min_player_version": "1.16",
        "recording_name": "2019_10_10",
        "recording_software_name": "Pupil Capture",
        "recording_software_version": "1.16.95",
        "recording_uuid": "e5059604-26f1-42ed-8e35-354198b56021",
        "start_time_synced_s": 2294.807856069,
        "start_time_system_s": 1570725800.220913,
        "system_info": "User: test_user, Platform: Linux",
    }


@pytest.fixture()
def statuses():
    """"""
    return {
        "world": {
            "name": "world",
            "device_uid": "Pupil Cam1 ID2",
            "timestamp": 1.0,
            "source_timestamp": 1.0,
            "last_source_timestamp": 0.0,
            "fps": 30.0,
        },
        "eye0": {
            "name": "eye0",
            "device_uid": "Pupil Cam1 ID0",
            "timestamp": 1.0,
            "source_timestamp": 1.0,
            "last_source_timestamp": 0.0,
            "fps": 120.0,
            "pupil": {
                "ellipse": {
                    "center": (0.0, 0.0),
                    "axes": (0.0, 0.0),
                    "angle": -90.0,
                },
                "diameter": 0.0,
                "location": (0.0, 0.0),
                "confidence": 0.0,
            },
        },
    }


# -- PUPIL DATA -- #
@pytest.fixture()
def pupil(folder_v1):
    """"""
    pldata = load_pldata_file(folder_v1, "pupil")

    pupil = [dict(d) for d in pldata.data]

    return pupil


@pytest.fixture()
def gaze_2d(folder_v1):
    """"""
    pldata = load_pldata_file(
        Path(folder_v1) / "offline_data" / "gaze-mappings",
        "2d_Gaze_Mapper_-28b2161b-24dd-4265-b12f-7d09c380bf4f",
    )

    gaze = [dict(d) for d in pldata.data]
    for g in gaze:
        g["base_data"] = tuple(dict(pupil) for pupil in g["base_data"])

    return gaze


@pytest.fixture()
def calibration_2d(folder_v1):
    """"""
    return load_object(
        Path(folder_v1)
        / "calibrations"
        / "2d_Calibration-4fb6bf62-0ae8-42d2-a16c-913e68a5f3c3.plcal"
    )


@pytest.fixture()
def calibration_recorded(folder_v1):
    """"""
    return load_object(
        Path(folder_v1)
        / "calibrations"
        / "Recorded_Calibration-85f75cc5-e2b2-5a46-b083-0a2054bbc810.plcal"
    )


@pytest.fixture()
def reference_locations_raw(folder_v1):
    """"""
    locations = load_object(
        Path(folder_v1) / "offline_data" / "reference_locations.msgpack"
    )

    return locations["data"]


@pytest.fixture()
def reference_locations(reference_locations_raw):
    """"""
    resolution = (1280, 720)

    locations = [
        {
            "img_pos": location[0],
            "norm_pos": normalize(location[0], resolution),
            "timestamp": location[2],
        }
        for location in reference_locations_raw
    ]

    return locations


# -- PACKETS -- #
@pytest.fixture()
def packet():
    """"""
    return Packet(
        "world",
        "Pupil Cam1 ID2",
        0.0,
        frame=np.zeros((1280, 720), dtype=np.uint8),
        display_frame=np.zeros((1280, 720), dtype=np.uint8),
    )


@pytest.fixture()
def pupil_packet(packet, pupil):
    """"""
    packet.pupil = pupil[100]

    return packet


@pytest.fixture()
def gaze_packet(packet, gaze_2d):
    """"""
    packet.gaze = gaze_2d[100:102]

    return packet


@pytest.fixture()
def circle_marker_packet(packet):
    """"""
    packet.circle_markers = [
        {
            "ellipses": [
                (
                    (399.16404724121094, 215.4773941040039),
                    (7.052967071533203, 8.333015441894531),
                    43.05573272705078,
                ),
                (
                    (399.69960021972656, 215.33668518066406),
                    (53.05698776245117, 67.6202621459961),
                    8.497730255126953,
                ),
                (
                    (400.78492736816406, 215.5298080444336),
                    (109.97621154785156, 137.57115173339844),
                    8.513727188110352,
                ),
                (
                    (402.8581237792969, 215.88968658447266),
                    (170.45883178710938, 213.98965454101562),
                    8.824980735778809,
                ),
            ],
            "img_pos": (399.16404724121094, 215.4773941040039),
            "norm_pos": (0.31184691190719604, 0.7007258415222168),
            "marker_type": "Ref",
        }
    ]

    return packet


@pytest.fixture()
def circle_grid_packet(packet):
    """"""
    packet.circle_grid = {
        "grid_points": np.array(
            [
                [[100.0, 100.0]],
                [[100.0, 200.0]],
                [[200.0, 100.0]],
                [[200.0, 200.0]],
            ],
            dtype=np.float32,
        ),
        "resolution": (1280, 720),
        "stereo": False,
    }

    return packet


@pytest.fixture()
def patterns():
    """"""
    return {
        "world": [
            np.array(
                [
                    [[389.8157, 444.47968]],
                    [[377.68048, 376.75916]],
                    [[369.62338, 306.19482]],
                    [[363.8928, 235.31462]],
                    [[408.8126, 413.17044]],
                    [[399.81973, 340.9392]],
                    [[392.92044, 267.34897]],
                    [[387.56104, 194.50468]],
                    [[442.4331, 451.3918]],
                    [[432.70493, 377.94296]],
                    [[425.0677, 301.95154]],
                    [[418.32858, 225.87856]],
                    [[467.65466, 417.19376]],
                    [[459.4145, 339.37018]],
                    [[452.56833, 260.15448]],
                    [[446.59186, 182.17798]],
                    [[505.41058, 458.18686]],
                    [[496.49738, 379.3615]],
                    [[488.89267, 297.63828]],
                    [[482.52798, 215.87238]],
                    [[535.87213, 421.60162]],
                    [[528.4315, 337.94296]],
                    [[521.3924, 252.93925]],
                    [[514.4373, 169.07014]],
                    [[578.6055, 465.28088]],
                    [[570.66974, 381.06366]],
                    [[563.52765, 293.32672]],
                    [[556.13763, 205.6459]],
                    [[615.248, 426.16718]],
                    [[608.6058, 336.7845]],
                    [[601.2233, 245.69646]],
                    [[593.44226, 155.82664]],
                    [[662.1374, 472.38748]],
                    [[655.9392, 382.78024]],
                    [[649.0098, 289.19574]],
                    [[640.9132, 195.37755]],
                    [[705.04767, 430.6132]],
                    [[699.45825, 335.93768]],
                    [[691.42377, 238.95999]],
                    [[682.4091, 143.05402]],
                    [[756.0068, 478.74368]],
                    [[751.5222, 384.90884]],
                    [[744.77203, 286.0286]],
                    [[735.48975, 186.14366]],
                ],
                dtype=np.float32,
            ),
            np.array(
                [
                    [[389.95297, 444.4029]],
                    [[377.9055, 376.64807]],
                    [[369.90054, 306.11783]],
                    [[364.3736, 235.18631]],
                    [[408.97073, 413.1124]],
                    [[400.03796, 340.80692]],
                    [[393.28555, 267.23254]],
                    [[387.95908, 194.41692]],
                    [[442.6255, 451.29385]],
                    [[432.92902, 377.79358]],
                    [[425.3573, 301.8399]],
                    [[418.74948, 225.83989]],
                    [[467.86163, 417.1129]],
                    [[459.70535, 339.27405]],
                    [[452.90106, 260.1152]],
                    [[447.01584, 182.06192]],
                    [[505.56345, 458.1174]],
                    [[496.63672, 379.22668]],
                    [[489.2498, 297.54214]],
                    [[482.9211, 215.79077]],
                    [[536.05194, 421.5078]],
                    [[528.68225, 337.78345]],
                    [[521.7002, 252.80708]],
                    [[514.80066, 168.9728]],
                    [[578.7341, 465.11182]],
                    [[570.8615, 380.88885]],
                    [[563.7861, 293.18524]],
                    [[556.51013, 205.51712]],
                    [[615.44293, 426.00723]],
                    [[608.8262, 336.6239]],
                    [[601.53064, 245.58672]],
                    [[593.7761, 155.72636]],
                    [[662.296, 472.23636]],
                    [[656.1342, 382.62753]],
                    [[649.227, 289.05338]],
                    [[641.25073, 195.27911]],
                    [[705.1635, 430.49448]],
                    [[699.66614, 335.7125]],
                    [[691.70844, 238.79591]],
                    [[682.6858, 142.96063]],
                    [[756.1572, 478.54822]],
                    [[751.7437, 384.70352]],
                    [[744.95105, 285.8376]],
                    [[735.77686, 185.95274]],
                ],
                dtype=np.float32,
            ),
            np.array(
                [
                    [[99.68895, 412.46658]],
                    [[88.41287, 347.00443]],
                    [[82.56355, 278.9982]],
                    [[80.992035, 211.09326]],
                    [[112.05628, 381.7151]],
                    [[104.08008, 312.05588]],
                    [[100.36345, 241.37477]],
                    [[100.363106, 171.72185]],
                    [[138.89116, 418.37015]],
                    [[128.80927, 347.2124]],
                    [[123.05599, 273.95905]],
                    [[120.72978, 201.05002]],
                    [[156.4412, 384.82764]],
                    [[148.50598, 309.48215]],
                    [[144.63855, 233.31264]],
                    [[144.49171, 158.54079]],
                    [[187.61154, 424.33228]],
                    [[177.37135, 347.6646]],
                    [[171.32716, 268.71722]],
                    [[169.36827, 190.2049]],
                    [[209.67305, 388.33026]],
                    [[201.88329, 307.0855]],
                    [[197.69852, 225.14337]],
                    [[197.11052, 144.6498]],
                    [[246.75266, 430.55542]],
                    [[236.27446, 348.39288]],
                    [[230.15694, 263.41595]],
                    [[227.44583, 178.87994]],
                    [[274.80518, 392.07047]],
                    [[266.837, 304.95764]],
                    [[262.16946, 216.72375]],
                    [[261.1003, 130.26576]],
                    [[317.50308, 437.30585]],
                    [[307.60052, 349.40384]],
                    [[301.00677, 258.31]],
                    [[297.7688, 167.48463]],
                    [[352.35733, 396.10257]],
                    [[344.6383, 303.35477]],
                    [[338.8549, 208.8916]],
                    [[337.02664, 116.05517]],
                    [[401.79355, 443.78012]],
                    [[392.23816, 351.09344]],
                    [[384.90485, 254.13776]],
                    [[380.40558, 156.7368]],
                ],
                dtype=np.float32,
            ),
        ],
        "t265_left": [
            np.array(
                [
                    [[375.9253, 397.72076]],
                    [[372.13895, 373.94318]],
                    [[369.29984, 348.79523]],
                    [[366.72452, 323.0172]],
                    [[384.11545, 387.2647]],
                    [[381.3292, 361.84344]],
                    [[378.84143, 335.45148]],
                    [[376.2384, 308.68674]],
                    [[396.62836, 401.11673]],
                    [[394.01944, 375.55682]],
                    [[391.62976, 348.64584]],
                    [[389.02606, 321.19122]],
                    [[407.035, 389.9462]],
                    [[404.8618, 362.72153]],
                    [[402.66263, 334.6024]],
                    [[400.2459, 306.0466]],
                    [[420.59396, 404.86316]],
                    [[418.67676, 377.603]],
                    [[416.67938, 348.90756]],
                    [[414.56833, 319.5215]],
                    [[432.79807, 393.03403]],
                    [[431.36777, 364.07663]],
                    [[429.50125, 334.03873]],
                    [[427.1763, 303.5047]],
                    [[447.64096, 408.9198]],
                    [[446.44394, 380.04645]],
                    [[445.07684, 349.52942]],
                    [[443.13086, 318.21335]],
                    [[461.92294, 396.5662]],
                    [[461.1721, 365.8859]],
                    [[459.78265, 333.9502]],
                    [[457.74524, 301.29688]],
                    [[477.60266, 413.37762]],
                    [[477.4932, 382.962]],
                    [[476.75574, 350.6763]],
                    [[475.29016, 317.3219]],
                    [[493.90143, 400.49744]],
                    [[494.1316, 368.3135]],
                    [[493.2756, 334.5043]],
                    [[491.5977, 299.73505]],
                    [[510.5294, 418.1954]],
                    [[511.487, 386.4839]],
                    [[511.58655, 352.6599]],
                    [[510.5643, 317.24326]],
                ],
                dtype=np.float32,
            ),
            np.array(
                [
                    [[375.95398, 397.6729]],
                    [[372.20657, 373.86963]],
                    [[369.37137, 348.74463]],
                    [[366.8716, 322.93182]],
                    [[384.13358, 387.16818]],
                    [[381.4095, 361.77527]],
                    [[378.90918, 335.37744]],
                    [[376.36725, 308.65826]],
                    [[396.69092, 401.082]],
                    [[394.07648, 375.45428]],
                    [[391.7083, 348.5485]],
                    [[389.12573, 321.1853]],
                    [[407.09418, 389.8349]],
                    [[404.95306, 362.6426]],
                    [[402.73715, 334.54608]],
                    [[400.35577, 305.99585]],
                    [[420.61896, 404.77142]],
                    [[418.73987, 377.50177]],
                    [[416.75165, 348.82886]],
                    [[414.67184, 319.4752]],
                    [[432.86325, 392.95386]],
                    [[431.4212, 363.97244]],
                    [[429.57742, 333.9415]],
                    [[427.28378, 303.4017]],
                    [[447.66132, 408.84317]],
                    [[446.4867, 379.926]],
                    [[445.14487, 349.422]],
                    [[443.22104, 318.11792]],
                    [[461.95358, 396.4788]],
                    [[461.22885, 365.76953]],
                    [[459.85083, 333.86496]],
                    [[457.8299, 301.22778]],
                    [[477.64377, 413.28873]],
                    [[477.52475, 382.85242]],
                    [[476.82776, 350.59973]],
                    [[475.378, 317.21204]],
                    [[493.9267, 400.38086]],
                    [[494.16962, 368.19595]],
                    [[493.33612, 334.37772]],
                    [[491.658, 299.63513]],
                    [[510.57758, 418.07587]],
                    [[511.53976, 386.35782]],
                    [[511.67294, 352.55756]],
                    [[510.64267, 317.12393]],
                ],
                dtype=np.float32,
            ),
            np.array(
                [
                    [[235.28935, 392.9579]],
                    [[229.5076, 367.89865]],
                    [[225.36862, 341.28198]],
                    [[222.32277, 313.85336]],
                    [[241.76239, 381.28818]],
                    [[237.30826, 354.4243]],
                    [[233.80112, 326.47723]],
                    [[231.10794, 298.07288]],
                    [[254.87851, 394.987]],
                    [[250.08823, 368.1145]],
                    [[246.33456, 339.80463]],
                    [[243.15877, 310.7128]],
                    [[263.5517, 382.39108]],
                    [[259.50806, 353.8781]],
                    [[256.3428, 324.233]],
                    [[253.80328, 294.08087]],
                    [[277.79654, 397.005]],
                    [[273.5138, 368.63165]],
                    [[270.03555, 338.48727]],
                    [[267.39246, 307.64005]],
                    [[288.23627, 383.8242]],
                    [[284.75034, 353.5353]],
                    [[281.85223, 322.13864]],
                    [[279.49545, 290.07727]],
                    [[304.04385, 399.277]],
                    [[300.2765, 369.33243]],
                    [[297.3106, 337.503]],
                    [[294.78836, 304.7915]],
                    [[316.57837, 385.45404]],
                    [[313.66702, 353.59528]],
                    [[311.12985, 320.37518]],
                    [[309.1503, 286.3895]],
                    [[333.64774, 401.74826]],
                    [[330.72845, 370.26135]],
                    [[328.25668, 336.80463]],
                    [[326.21417, 302.2023]],
                    [[348.4531, 387.3409]],
                    [[346.2828, 354.05502]],
                    [[344.12527, 319.12793]],
                    [[342.5312, 283.17648]],
                    [[366.96594, 404.3632]],
                    [[364.8623, 371.72833]],
                    [[362.9939, 336.86884]],
                    [[361.31036, 300.40955]],
                ],
                dtype=np.float32,
            ),
        ],
        "t265_right": [
            np.array(
                [
                    [[335.886, 398.45233]],
                    [[331.3589, 375.16013]],
                    [[327.87805, 350.4333]],
                    [[325.08643, 325.37363]],
                    [[342.10864, 388.21893]],
                    [[338.62744, 363.21667]],
                    [[335.536, 337.31638]],
                    [[332.6903, 311.24542]],
                    [[353.54077, 401.81586]],
                    [[349.9922, 376.63583]],
                    [[346.90198, 350.16718]],
                    [[343.78857, 323.20007]],
                    [[361.7998, 390.79092]],
                    [[358.72412, 363.89594]],
                    [[355.90955, 336.08743]],
                    [[353.05933, 308.02478]],
                    [[374.36145, 405.51425]],
                    [[371.26672, 378.46704]],
                    [[368.40112, 349.9983]],
                    [[365.73157, 320.93262]],
                    [[384.37134, 393.7711]],
                    [[381.78394, 364.83914]],
                    [[379.14075, 335.01883]],
                    [[376.21985, 304.6764]],
                    [[398.5437, 409.66678]],
                    [[395.89966, 380.69604]],
                    [[393.47754, 350.16907]],
                    [[390.75476, 318.80954]],
                    [[410.69177, 397.3136]],
                    [[408.58875, 366.3343]],
                    [[406.14062, 334.1875]],
                    [[403.37085, 301.39255]],
                    [[426.16113, 414.34067]],
                    [[424.38025, 383.48102]],
                    [[422.28064, 350.68832]],
                    [[419.7395, 316.90396]],
                    [[440.65002, 401.23773]],
                    [[439.30762, 368.37183]],
                    [[436.9635, 333.86322]],
                    [[434.302, 298.3619]],
                    [[457.7694, 419.45886]],
                    [[456.78467, 386.83426]],
                    [[455.14612, 351.985]],
                    [[452.6776, 315.48508]],
                ],
                dtype=np.float32,
            ),
            np.array(
                [
                    [[335.9845, 398.39243]],
                    [[331.41724, 375.05792]],
                    [[328.03748, 350.41852]],
                    [[325.2135, 325.27625]],
                    [[342.13452, 388.1258]],
                    [[338.719, 363.0918]],
                    [[335.66675, 337.2949]],
                    [[332.85876, 311.17404]],
                    [[353.6106, 401.73404]],
                    [[350.07434, 376.55667]],
                    [[346.99, 350.0916]],
                    [[343.94153, 323.12537]],
                    [[361.87305, 390.68942]],
                    [[358.79553, 363.7547]],
                    [[356.02783, 336.0303]],
                    [[353.1892, 307.91678]],
                    [[374.39526, 405.4189]],
                    [[371.328, 378.39514]],
                    [[368.4934, 349.92395]],
                    [[365.84607, 320.86475]],
                    [[384.4192, 393.6942]],
                    [[381.87695, 364.80292]],
                    [[379.25537, 334.92014]],
                    [[376.35376, 304.5995]],
                    [[398.5868, 409.58426]],
                    [[395.9419, 380.64175]],
                    [[393.57947, 350.08762]],
                    [[390.8518, 318.75226]],
                    [[410.74426, 397.2436]],
                    [[408.66528, 366.22433]],
                    [[406.24182, 334.07043]],
                    [[403.49475, 301.33633]],
                    [[426.2157, 414.23996]],
                    [[424.45093, 383.36804]],
                    [[422.3811, 350.58313]],
                    [[419.84375, 316.81177]],
                    [[440.6902, 401.13287]],
                    [[439.36597, 368.2555]],
                    [[437.0725, 333.75858]],
                    [[434.43896, 298.2885]],
                    [[457.83472, 419.34195]],
                    [[456.84058, 386.71442]],
                    [[455.2329, 351.88965]],
                    [[452.78528, 315.41113]],
                ],
                dtype=np.float32,
            ),
            np.array(
                [
                    [[203.44238, 393.88504]],
                    [[197.48462, 370.24722]],
                    [[193.18774, 345.2065]],
                    [[190.00073, 319.4021]],
                    [[208.06909, 382.89398]],
                    [[203.29248, 357.56104]],
                    [[199.62683, 331.2221]],
                    [[196.77649, 304.6026]],
                    [[219.4624, 395.78662]],
                    [[214.30652, 370.4195]],
                    [[210.19519, 343.7526]],
                    [[206.83447, 316.45303]],
                    [[225.9541, 383.8919]],
                    [[221.4989, 356.95334]],
                    [[217.92578, 329.047]],
                    [[215.11768, 300.72992]],
                    [[238.44202, 397.76733]],
                    [[233.53113, 370.83716]],
                    [[229.54602, 342.43158]],
                    [[226.50806, 313.2668]],
                    [[246.32788, 385.2097]],
                    [[242.17676, 356.5699]],
                    [[238.74097, 326.82812]],
                    [[235.95642, 296.58218]],
                    [[260.38782, 399.9243]],
                    [[255.698, 371.3554]],
                    [[251.98804, 341.2185]],
                    [[248.86182, 310.24387]],
                    [[270.1084, 386.66852]],
                    [[266.20044, 356.34317]],
                    [[262.83875, 324.74252]],
                    [[260.23706, 292.49625]],
                    [[285.53296, 402.26068]],
                    [[281.29858, 372.13382]],
                    [[277.7379, 340.15613]],
                    [[274.78906, 307.12064]],
                    [[297.25928, 388.34183]],
                    [[293.7489, 356.44623]],
                    [[290.38306, 322.9819]],
                    [[287.93896, 288.4884]],
                    [[314.52832, 404.78583]],
                    [[310.6106, 373.27878]],
                    [[307.13196, 339.64972]],
                    [[304.21655, 304.50934]],
                ],
                dtype=np.float32,
            ),
        ],
    }


@pytest.fixture()
def intrinsics():
    """"""
    return {
        "world": (
            (1280, 720),
            "radial",
            np.array(
                [
                    [1.09102840e03, 0.00000000e00, 5.40758028e02],
                    [0.00000000e00, 9.06409752e02, 4.48742036e02],
                    [0.00000000e00, 0.00000000e00, 1.00000000e00],
                ]
            ),
            np.array(
                [
                    [
                        -0.59883649,
                        0.54028932,
                        -0.03402168,
                        0.03306559,
                        -0.3829259,
                    ]
                ]
            ),
        )
    }


@pytest.fixture()
def extrinsics():
    """"""
    return {
        ("t265_left", "t265_right"): (
            (848, 800),
            (848, 800),
            np.array(
                [
                    [0.99999411, 0.00115959, 0.0032307],
                    [-0.00120395, 0.9999046, 0.01375999],
                    [-0.00321443, -0.0137638, 0.99990011],
                ]
            ),
            np.array([[-2.87012494], [0.0349811], [-0.03503141]]),
        )
    }


@pytest.fixture()
def calibration_result():
    """"""
    return {
        "subject": "start_plugin",
        "name": "Binocular_Gaze_Mapper",
        "args": {
            "params": [
                [
                    22.06279309095615,
                    27.233805896338197,
                    -4.968271559107238,
                    -3.0065855962823704,
                    -13.47774849297383,
                    -21.039823201325518,
                    -79.63250746458891,
                    174.32881820383022,
                    2.927348015233868,
                    1.165874665331882,
                    4.186160094797165,
                    -3.060545021023703,
                    -3.5697134072793375,
                ],
                [
                    51.57494601395783,
                    50.96653289212003,
                    -12.911423077545884,
                    -0.9033969413550649,
                    -33.73793257878155,
                    -34.04548721522045,
                    -183.9156834459527,
                    413.4205868732686,
                    7.679344281249296,
                    -1.6095141228808707,
                    14.952456135552591,
                    -9.037791215096188,
                    -8.995370243320579,
                ],
                13,
            ],
            "params_eye0": [
                [
                    -5.573642210122941,
                    -15.660366268881239,
                    3.3892265084323627,
                    15.491778221191906,
                    24.61607970636751,
                    -37.56048142264788,
                    2.8102198453565217,
                ],
                [
                    -4.449380270968307,
                    -4.243154731676149,
                    4.098351002412766,
                    0.6817178913459605,
                    0.7913556940415702,
                    -3.397681472038215,
                    2.8006933001301615,
                ],
                7,
            ],
            "params_eye1": [
                [
                    -6.0625412029505625,
                    -1.308220620996945,
                    3.314804406714515,
                    -0.1758573135817958,
                    5.839207978162214,
                    -3.9934924304376267,
                    1.7932222025398197,
                ],
                [
                    -59.64240627663011,
                    -6.624310160582425,
                    40.491922926613995,
                    -4.079075716683576,
                    84.13402791986088,
                    -78.37694504349447,
                    7.209455805477312,
                ],
                7,
            ],
        },
    }


# -- CONFIGS -- #
@pytest.fixture()
def mock_stream_config():
    """"""
    return MockStream.Config("mock_device", "mock_device", name="mock_stream")


@pytest.fixture()
def video_stream_config():
    """"""
    return VideoStream.Config(
        "uvc", "test_cam", resolution=(1280, 720), fps=30
    )


@pytest.fixture()
def pipeline_config():
    """"""
    return VideoStream.Config(
        "uvc",
        "test_cam",
        resolution=(1280, 720),
        fps=30,
        pipeline=[VideoRecorder.Config()],
    )


@pytest.fixture()
def motion_stream_config():
    """"""
    return MotionStream.Config("t265", "t265", motion_type="odometry")


@pytest.fixture()
def config_list():
    """"""
    return [
        VideoStream.Config("uvc", "test_cam", resolution=(1280, 720), fps=30),
        VideoStream.Config("t265", "t265_serial"),
        MotionStream.Config("t265", "t265_serial", motion_type="odometry"),
    ]


@pytest.fixture()
def process_configs(tmpdir):
    """ Mapping from process type to working test config for each process. """
    process_kwargs = {
        "video_recorder": {"folder": tmpdir},
        "motion_recorder": {"folder": tmpdir},
        "pupil_detector": {"folder": tmpdir},
        "calibration": {"folder": tmpdir},
        "cam_param_estimator": {"streams": ["world"], "folder": tmpdir},
        "video_file_syncer": {"master_stream": "world"},
    }

    configs = {
        process_type: cls.Config(**process_kwargs.get(process_type, {}))
        for process_type, cls in process.registry.items()
    }

    return configs


# -- DEVICES -- #
@pytest.fixture()
def mock_device():
    """"""
    return MockDevice("mock_device")


@pytest.fixture()
def mock_video_device():
    """"""
    return MockVideoDevice("mock_video_device")


@pytest.fixture()
def video_file_device(folder_v1):
    """"""
    return VideoFileDevice(folder_v1, "world")


# -- STREAMS -- #
@pytest.fixture()
def mock_stream(mock_device):
    """"""
    return MockStream(mock_device, name="mock_stream")


@pytest.fixture()
def video_stream(pipeline):
    """"""
    return VideoStream(None, pipeline, "test_stream")


@pytest.fixture()
def world_video_stream(video_file_device):
    """"""
    return VideoStream(video_file_device)


# -- PROCESSES -- #
@pytest.fixture()
def video_display():
    """"""
    return VideoDisplay("test")


@pytest.fixture()
def pupil_detector(tmpdir):
    """"""
    return PupilDetector(folder=tmpdir, record=True)


@pytest.fixture()
def gaze_mapper(tmpdir, calibration_2d):
    """"""
    return GazeMapper(
        folder=tmpdir, calibration=calibration_2d["data"][8][1], record=True,
    )


@pytest.fixture()
def circle_detector():
    """"""
    return CircleDetector()


@pytest.fixture()
def calibration():
    """"""
    return Calibration((1280, 720))


@pytest.fixture()
def validation():
    """"""
    return Validation((1280, 720), eye_resolution=(192, 192))


@pytest.fixture()
def cam_param_estimator(tmpdir, circle_grid_packet):
    """"""
    estimator = CamParamEstimator(["world", "t265"], tmpdir)

    grid_points_right = circle_grid_packet.circle_grid["grid_points"].copy()
    grid_points_right[:, :, 0] += 848

    pattern = {
        "world": circle_grid_packet.circle_grid,
        "t265": {
            "grid_points": [
                circle_grid_packet.circle_grid["grid_points"],
                grid_points_right,
            ],
            "resolution": (1696, 800),
            "stereo": True,
        },
    }

    estimator._pattern_queue.put(pattern)
    estimator._pattern_queue.put(pattern)

    return estimator


@pytest.fixture()
def circle_grid_detector():
    """"""
    return CircleGridDetector()


# -- OTHER -- #
@pytest.fixture()
def pipeline(video_display):
    """"""
    return Pipeline([video_display])


@pytest.fixture()
def stream_manager(mock_stream_config, mock_mp_deque):
    """"""
    manager = StreamManager([mock_stream_config])
    manager._status_queues["mock_stream"] = mock_mp_deque()

    return manager
