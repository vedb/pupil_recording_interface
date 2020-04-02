""""""
import abc

import numpy as np

from pupil_recording_interface.device.realsense import RealSenseDeviceT265
from pupil_recording_interface.device.video import (
    VideoDeviceUVC,
    VideoDeviceFLIR,
)
from pupil_recording_interface.legacy.base import BaseStreamRecorder
from pupil_recording_interface.encoder import VideoEncoderFFMPEG


class VideoRecorder(BaseStreamRecorder):
    """ Recorder for a video stream. """

    __metaclass__ = abc.ABCMeta

    def __init__(
        self,
        folder,
        device,
        name=None,
        policy="new_folder",
        color_format="bgr24",
        codec="libx264",
        show_video=False,
        **encoder_kwargs,
    ):
        """ Constructor.

        Parameters
        ----------
        folder: str
            Path to the recording folder.

        device: BaseVideoDevice
            The device from which to record the video.

        name: str, optional
            The name of the legacy. If not specified, `device.uid` will be
            used.

        policy: str, default 'new_folder'
            Policy for recording folder creation. If 'new_folder',
            new sub-folders will be created with incremental numbering. If
            'here', the data will be recorded to the specified folder but
            will throw an error when existing files would be overwritten. If
            'overwrite', the data will be recorded to the specified folder
            and existing files will possibly overwritten.

        color_format: str, default 'bgr24'
            The target color format. Set to 'gray' for eye cameras.

        codec: str, default 'libx264'
            The desired video codec.

        show_video: bool, default False,
            If True, show the video stream in a window.

        encoder_kwargs:
            Addtional keyword arguments passed to the encoder.
        """
        super(VideoRecorder, self).__init__(
            folder, device, name=name, policy=policy
        )

        self.encoder = VideoEncoderFFMPEG(
            self.folder,
            self.name,
            self.device.resolution,
            self.device.fps,
            color_format,
            codec,
            self.overwrite,
            **encoder_kwargs,
        )

        self.color_format = color_format
        self.show_video = show_video

    @classmethod
    def _from_config(cls, config, folder, device=None, overwrite=False):
        """ Create a device from a StreamConfig. """
        # TODO codec and other parameters
        if device is None:
            if config.device_type == "uvc":
                device = VideoDeviceUVC(
                    config.device_uid, config.resolution, config.fps
                )
            elif config.device_type == "flir":
                device = VideoDeviceFLIR(
                    config.device_uid, config.resolution, config.fps
                )
            elif config.device_type == "t265":
                device = RealSenseDeviceT265(
                    config.device_uid,
                    config.resolution,
                    config.fps,
                    video=config.side,
                )
            else:
                raise ValueError(
                    "Unsupported device type: {}.".format(config.device_type)
                )

        policy = "overwrite" if overwrite else "here"

        return VideoRecorder(folder, device, name=config.name, policy=policy)

    def get_data_and_timestamp(self):
        """ Get the last data packet and timestamp from the stream. """
        # TODO handle uvc.StreamError and reinitialize capture
        # TODO get only jpeg buffer when not showing video
        if self.color_format == "gray":
            frame, timestamp = self.device._get_frame_and_timestamp("gray")
        else:
            frame, timestamp = self.device._get_frame_and_timestamp()

        # show video if requested
        if self.show_video:
            # TODO set show_video to false when window is closed
            self.device.show_frame(frame)

        return frame, timestamp

    def write(self, frame):
        """ Write data to disk. """
        self.encoder.write(frame)

    def stop(self):
        """ Stop the legacy. """
        # TODO additionally save timestamps continuously if paranoid=True
        super(VideoRecorder, self).stop()
        self.encoder.stop()
        np.save(self.encoder.timestamp_file, np.array(self._timestamps))
