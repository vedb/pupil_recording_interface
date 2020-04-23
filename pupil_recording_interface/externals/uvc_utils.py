"""
(*)~---------------------------------------------------------------------------
Pupil - eye tracking platform
Copyright (C) 2012-2020 Pupil Labs

Distributed under the terms of the GNU
Lesser General Public License (LGPL v3.0).
See COPYING and COPYING.LESSER for license details.
---------------------------------------------------------------------------~(*)
"""
import numpy as np
import cv2


class Exposure_Time(object):
    def __init__(self, max_ET, frame_rate, mode="manual"):
        self.mode = mode
        self.ET_thres = 1, min(10000 / frame_rate, max_ET)
        self.last_ET = self.ET_thres[1]

        self.targetY_thres = 90, 150

        self.AE_Win = np.array(
            [
                [3, 1, 1, 1, 1, 1, 1, 3],
                [3, 1, 1, 1, 1, 1, 1, 3],
                [2, 1, 1, 1, 1, 1, 1, 2],
                [2, 1, 1, 1, 1, 1, 1, 2],
                [2, 1, 1, 1, 1, 1, 1, 2],
                [2, 1, 1, 1, 1, 1, 1, 2],
                [3, 1, 1, 1, 1, 1, 1, 3],
                [3, 1, 1, 1, 1, 1, 1, 3],
            ]
        )
        self.smooth = 1 / 3
        self.check_freq = 0.1 / 3
        self.last_check_timestamp = None

    def calculate_based_on_frame(self, frame):
        if self.last_check_timestamp is None:
            self.last_check_timestamp = frame.timestamp

        if frame.timestamp - self.last_check_timestamp > self.check_freq:
            if self.mode == "manual":
                self.last_ET = self.ET_thres[1]
                return self.ET_thres[1]
            elif self.mode == "auto":
                image_block = cv2.resize(frame.gray, dsize=self.AE_Win.shape)
                YTotal = max(
                    np.multiply(self.AE_Win, image_block).sum()
                    / self.AE_Win.sum(),
                    1,
                )

                if YTotal < self.targetY_thres[0]:
                    targetET = self.last_ET * self.targetY_thres[0] / YTotal
                elif YTotal > self.targetY_thres[1]:
                    targetET = self.last_ET * self.targetY_thres[1] / YTotal
                else:
                    targetET = self.last_ET

                next_ET = np.clip(
                    self.last_ET + (targetET - self.last_ET) * self.smooth,
                    self.ET_thres[0],
                    self.ET_thres[1],
                )
                self.last_ET = next_ET
                return next_ET


class Check_Frame_Stripes(object):
    def __init__(
        self,
        check_freq_init=0.1,
        check_freq_upperbound=5,
        check_freq_lowerbound=0.00001,
        factor=0.8,
    ):
        self.check_freq_init = check_freq_init
        self.check_freq = self.check_freq_init
        self.check_freq_upperbound = check_freq_upperbound
        self.check_freq_lowerbound = check_freq_lowerbound
        self.factor = factor
        self.factor_mul = 1.1

        self.last_check_timestamp = None
        self.len_row_index = 8
        self.len_col_index = 8
        self.row_index = None
        self.col_index = None

    def require_restart(self, frame):
        if self.last_check_timestamp is None:
            self.last_check_timestamp = frame.timestamp

        if frame.timestamp - self.last_check_timestamp > self.check_freq:
            self.last_check_timestamp = frame.timestamp
            res = self.check_slice(frame.gray)

            if res is True:
                self.check_freq = (
                    min(self.check_freq_init, self.check_freq) * self.factor
                )
                if self.check_freq < self.check_freq_lowerbound:
                    return True
            elif res is False:
                if self.check_freq < self.check_freq_upperbound:
                    self.check_freq = min(
                        self.check_freq * self.factor_mul,
                        self.check_freq_upperbound,
                    )

        return False

    def check_slice(self, frame_gray):
        num_local_optimum = [0, 0]
        if self.row_index is None:
            self.row_index = np.linspace(
                8,
                frame_gray.shape[0] - 8,
                num=self.len_row_index,
                dtype=np.int,
            )
            self.col_index = np.linspace(
                8,
                frame_gray.shape[1] - 8,
                num=self.len_col_index,
                dtype=np.int,
            )
        for n in [0, 1]:
            if n == 0:
                arrs = np.array(frame_gray[self.row_index, :], dtype=np.int)
            else:
                arrs = np.array(frame_gray[:, self.col_index], dtype=np.int)
                arrs = np.transpose(arrs)

            local_max_union = set()
            local_min_union = set()
            for arr in arrs:
                local_max = set(
                    np.where(
                        np.r_[False, True, arr[2:] > arr[:-2] + 30]
                        & np.r_[arr[:-2] > arr[2:] + 30, True, False]
                        is True
                    )[0]
                )
                local_min = set(
                    np.where(
                        np.r_[False, True, arr[2:] + 30 < arr[:-2]]
                        & np.r_[arr[:-2] + 30 < arr[2:], True, False]
                        is True
                    )[0]
                )
                num_local_optimum[n] += len(
                    local_max_union.intersection(local_max)
                ) + len(local_min_union.intersection(local_min))
                if sum(num_local_optimum) >= 3:
                    return True
                local_max_union = local_max_union.union(local_max)
                local_min_union = local_min_union.union(local_min)

        if sum(num_local_optimum) == 0:
            return False
        else:
            return None


def pre_configure_capture(uvc_capture):
    """"""

    # UVC setting quirks:
    controls_dict = dict([(c.display_name, c) for c in uvc_capture.controls])

    try:
        controls_dict["Auto Focus"].value = 0
    except KeyError:
        pass

    if "Pupil Cam1" in uvc_capture.name:
        if "ID0" in uvc_capture.name or "ID1" in uvc_capture.name:
            uvc_capture.bandwidth_factor = 1.3
            try:
                controls_dict["Auto Exposure Priority"].value = 0
            except KeyError:
                pass
            try:
                controls_dict["Auto Exposure Mode"].value = 1
            except KeyError:
                pass
            try:
                controls_dict["Saturation"].value = 0
            except KeyError:
                pass
            try:
                controls_dict["Absolute Exposure Time"].value = 63
            except KeyError:
                pass
            try:
                controls_dict["Backlight Compensation"].value = 2
            except KeyError:
                pass
            try:
                controls_dict["Gamma"].value = 100
            except KeyError:
                pass
        else:
            uvc_capture.bandwidth_factor = 2.0
            try:
                controls_dict["Auto Exposure Priority"].value = 1
            except KeyError:
                pass

    elif "Pupil Cam2" in uvc_capture.name or "Pupil Cam3" in uvc_capture.name:
        try:
            controls_dict["Auto Exposure Priority"].value = 0
        except KeyError:
            pass
        try:
            controls_dict["Auto Exposure Mode"].value = 1
        except KeyError:
            pass
        try:
            controls_dict["Saturation"].value = 0
        except KeyError:
            pass
        try:
            controls_dict["Gamma"].value = 200
        except KeyError:
            pass

    else:
        uvc_capture.bandwidth_factor = 2.0
        try:
            controls_dict["Auto Focus"].value = 0
        except KeyError:
            pass

    return uvc_capture


def maybe_init_exposure_handler(uvc_capture, exposure_mode, frame_rate):
    """"""
    if "Pupil Cam2" in uvc_capture.name or "Pupil Cam3" in uvc_capture.name:
        if exposure_mode == "auto":
            # special settings apply to both, Pupil Cam2 and Cam3
            special_settings = {200: 28, 180: 31}
            return Exposure_Time(
                max_ET=special_settings.get(frame_rate, 32),
                frame_rate=frame_rate,
                mode=exposure_mode,
            )
