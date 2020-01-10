""""""
import os

from pupil_recording_interface.errors import FileNotFoundError


class BaseRecorder(object):
    """ Base class for all recorders. """

    def __init__(self, folder):
        """ Constructor.

        Parameters
        ----------
        folder : str
            Path to the recording folder.
        """
        if not os.path.exists(folder):
            raise FileNotFoundError('No such folder: {}'.format(folder))

        self.folder = folder

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
