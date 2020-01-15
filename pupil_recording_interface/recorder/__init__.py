""""""
import abc
import os

import numpy as np


class BaseRecorder(object):
    """ Base class for all recorders. """

    def __init__(self, folder, policy='new_folder'):
        """ Constructor.

        Parameters
        ----------
        folder : str
            Path to the recording folder.
        """
        self.folder = self._init_folder(folder, policy)

    @classmethod
    def _init_folder(cls, folder, policy):
        """"""
        folder = os.path.abspath(os.path.expanduser(folder))

        if policy == 'new_folder':
            counter = 0
            while os.path.exists(
                    os.path.join(folder, '{:03d}'.format(counter))):
                counter += 1
            folder = os.path.join(folder, '{:03d}'.format(counter))

        elif policy != 'overwrite':
            raise ValueError(
                'Unsupported file creation policy: {}'.format(policy))

        os.makedirs(folder, exist_ok=True)

        return folder


class BaseStreamRecorder(object):
    """ Base class for all stream recorders. """

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def init_capture(self):
        """ Initialize the underlying capture. """

    @abc.abstractmethod
    def run_pre_recording_hooks(self):
        """ Hooks to run before the main recording loop. """

    @abc.abstractmethod
    def get_data_and_timestamp(self):
        """ Get the last data packet and timestamp from the stream. """

    @abc.abstractmethod
    def write(self, data):
        """ Write data to disk. """

    @abc.abstractmethod
    def stop(self):
        """ Stop the recorder. """

    @abc.abstractmethod
    def run_post_recording_hooks(self):
        """ Hooks to run after the main recording loop. """

    def _process_timestamp(self, timestamp, fps_queue=None):
        """ Process a new timestamp. """
        self._timestamps.append(timestamp)

        if timestamp != self._last_timestamp:
            fps = 1. / (timestamp - self._last_timestamp)
        else:
            fps = np.nan

        if fps_queue is not None:
            fps_queue.put(fps)
        else:
            self._fps_buffer.append(fps)

        self._last_timestamp = timestamp

    def run(self, stop_event=None, fps_queue=None):
        """ Main recording loop.

        Parameters
        ----------
        stop_event: multiprocessing.Event, optional
            An event that stops recording in a multi-threaded setting.

        fps_queue: multiprocessing.Queue, optional
            A queue for the current fps in a multi-threaded setting.
        """
        # TODO for some devices, capture has to be initialized here for
        #  multi-threaded operation, check if we can circumvent this
        if self.capture is None:
            self.capture = self.init_capture()

        self.run_pre_recording_hooks()

        while True:
            try:
                if stop_event is not None and stop_event.is_set():
                    break

                data, timestamp = self.get_data_and_timestamp()

                # write data to disk
                self.write(data)

                # save timestamp and fps
                self._process_timestamp(timestamp, fps_queue)

            except KeyboardInterrupt:
                self.stop()
                break

        self.run_post_recording_hooks()
