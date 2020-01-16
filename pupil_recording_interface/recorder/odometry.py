""""""
import os

from pupil_recording_interface.externals.file_methods import PLData_Writer
from pupil_recording_interface.recorder import BaseStreamRecorder
from pupil_recording_interface.device.realsense import RealSenseDeviceT265


class OdometryRecorder(BaseStreamRecorder):
    """ Recorder for an odometry stream. """

    def __init__(self, *args, **kwargs):
        super(OdometryRecorder, self).__init__(*args, **kwargs)

        topic = 'odometry'
        self.filename = os.path.join(self.folder, topic + '.pldata')
        if not self.overwrite and os.path.exists(self.filename):
            raise IOError('{} exists, will not overwrite'.format(
                self.filename))
        self.writer = PLData_Writer(self.folder, topic)

    @classmethod
    def _from_config(cls, config, folder, device=None):
        """ Per-class implementation of from_config. """
        if device is None:
            # TODO fix having to start all streams
            device = RealSenseDeviceT265(
                config.device_uid, odometry=True, video='both', start=True)

        return OdometryRecorder(
            folder, device, name=config.name, policy='here')

    def start(self):
        """ Start the recorder. """
        if not self.device.is_started:
            self.device.start()

    def get_data_and_timestamp(self):
        """ Get the last data packet and timestamp from the stream. """
        return self.device._get_odometry_and_timestamp()

    def write(self, data):
        """ Write data to disk. """
        self.writer.append(data)

    def stop(self):
        """ Stop the recorder. """
        self.writer.close()
        self.device.stop()
