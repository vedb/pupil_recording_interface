""""""
import time
import cv2

from pupil_recording_interface.recorder.multi_stream import MultiStreamRecorder
from pupil_recording_interface.recorder.video import ImageEncoder


class MultiCameraCalibration(MultiStreamRecorder):
    """ Calibration for multiple rigidly mounted cameras. """

    def __init__(self, folder, configs, policy='new_folder', n_images=8,
                 quiet=False):
        """ Constructor.

        Parameters
        ----------
        folder: str
            Path to the recording folder.

        configs: iterable of StreamConfig
            An iterable of stream configurations.

        policy: str, default 'new_folder'
            Policy for recording folder creation. If 'new_folder',
            new sub-folders will be created with incremental numbering. If
            'here', the data will be recorded to the specified folder but
            will throw an error when existing files would be overwritten. If
            'overwrite', the data will be recorded to the specified folder
            and existing files will possibly be overwritten.

        n_images: int, default 8
            Number of calibration images to acquire.

        quiet: bool, default False
            If True, do not print infos to stdout.
        """
        super(MultiCameraCalibration, self).__init__(
            folder, configs, policy=policy, quiet=quiet,
            encoder=ImageEncoder, show_video=True)

        self.n_images = n_images

    def flush_event_queue(
            self, event_queue, recording_events, n_acquired):
        """ Process new events in the event queue. """
        while not event_queue.empty():
            event = event_queue.get()
            if event == ord('c'):
                for r in recording_events.values():
                    r.set()
                n_acquired += 1
                if not self.quiet:
                    print('Saved calibration images [{}/{}]'.format(
                        n_acquired, self.n_images))

        return n_acquired

    def calibrate(self):
        """ Run the calibration. """
        if not self.quiet:
            print('Calibrating... ', end='')

        # TODO calibration code

        if not self.quiet:
            print('done!')

    def run(self):
        """ Main recording loop. """
        if not self.quiet:
            print('Saving calibration images to {}'.format(self.folder))

        # run hooks that need to be run in the main thread
        for recorder in self.recorders.values():
            recorder.run_pre_thread_hooks()

        # dispatch recording threads
        processes, event_queue, fps_queues, stop_event, recording_events = \
            self._init_processes(
                self.recorders, self._max_queue_size, set_recording_event=True)
        self._start_processes(processes)

        # acquire self.n_images calibration images
        n_acquired = 0
        while n_acquired < self.n_images:
            try:
                # TODO fps queues must be emptied in order to avoid
                #  freezing, maybe don't init queues at all
                for recorder_name, recorder in self.recorders.items():
                    while not fps_queues[recorder_name].empty():
                        recorder._fps_buffer.append(
                            fps_queues[recorder_name].get())

                # check for events queued by processes
                n_acquired = self.flush_event_queue(
                    event_queue, recording_events, n_acquired)

            except KeyboardInterrupt:
                break

        # stop recording threads
        self._stop_processes(processes, stop_event)

        if not self.quiet:
            print('Finished acquiring calibration images.')

        # run hooks that need to be run in the main thread
        for recorder in self.recorders.values():
            recorder.run_post_thread_hooks()

        self.calibrate()
