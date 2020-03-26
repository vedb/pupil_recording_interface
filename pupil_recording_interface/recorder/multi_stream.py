""""""
from __future__ import print_function

import multiprocessing as mp
import time

from pupil_recording_interface.recorder import BaseRecorder, BaseStreamRecorder

# Added this to solve the difference between T265 repo and pri
# This is only called to print out the time sync values so that pupil
# player can load and sync the eye and world videos


class MultiStreamRecorder(BaseRecorder):
    """ Recorder for multiple streams. """

    def __init__(
        self,
        folder,
        configs,
        policy="new_folder",
        quiet=False,
        show_video=False,
        duration=30,
    ):
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

        quiet: bool, default False
            If True, do not print infos to stdout.

        show_video: bool, default False,
            If True, show the video streams in a window.
        """
        super(MultiStreamRecorder, self).__init__(folder, policy=policy)

        self.recorders = self._init_recorders(
            self.folder, configs, show_video, policy == "overwrite"
        )
        self.quiet = quiet

        self._stdout_delay = 3.0  # delay before showing fps on stdout
        self._max_queue_size = 20  # max size of process fps queue
        self.all_devices_initialized = True
        self.duration = duration
        self.start_time_monotonic = 0
        self.start_time = 0
        self.run_duration = 0
        print("Recording for %d seconds ..." % (self.duration))

    @classmethod
    def _init_recorders(cls, folder, configs, show_video, overwrite):
        """ Init recorder instances for all configs. """
        uids = {c.device_uid for c in configs}
        configs_by_uid = {
            uid: [c for c in configs if c.device_uid == uid] for uid in uids
        }

        devices_by_uid, recorders = {}, {}
        for uid, config_list in configs_by_uid.items():

            # init t265 device separately
            if config_list[0].device_type == "t265":
                from pupil_recording_interface.device.realsense import (
                    RealSenseDeviceT265,
                )

                devices_by_uid[uid] = RealSenseDeviceT265.from_config_list(
                    config_list
                )
            else:
                devices_by_uid[uid] = None

            for config in config_list:
                # if the device for the UID has already been created, use that
                recorder = BaseStreamRecorder.from_config(
                    config, folder, devices_by_uid[uid], overwrite
                )
                devices_by_uid[uid] = devices_by_uid[uid] or recorder.device
                recorder.show_video = show_video
                recorders[config.name] = recorder

        return recorders

    @classmethod
    def _init_processes(cls, recorders, max_queue_size):
        """ Create one process for each recorder instance. """
        stop_event = mp.Event()
        queues = {
            c_name: mp.Queue(maxsize=max_queue_size)
            for c_name in recorders.keys()
        }
        processes = {
            c_name: mp.Process(
                target=c.run_in_thread, args=(stop_event, queues[c_name])
            )
            for c_name, c in recorders.items()
        }

        return processes, queues, stop_event

    @classmethod
    def _start_processes(cls, processes):
        """ Start all recorder processes. """
        for process in processes.values():
            process.start()

    @classmethod
    def _stop_processes(cls, processes, stop_event):
        """ Stop all recorder processes. """
        stop_event.set()
        for process in processes.values():
            process.join()

    # TODO: Read actual software versions and system info
    def save_metadata(self):
        import json

        my_json_file = {
            "duration_s": self.run_duration,
            "meta_version": "2.1",
            "min_player_version": "1.16",
            "recording_name": self.folder,
            "recording_software_name": "Pupil Capture",
            "recording_software_version": "1.21.5",
            "recording_uuid": "63d404ee-5f05-45f0-854b-a403efbbfbe3",
            "start_time_synced_s": self.start_time_monotonic,  # 1879.586018413
            "start_time_system_s": self.start_time,  # 1582679643.3734152
            "system_info": "User: veddy, Platform: Linux, Machine: veddy02",
        }
        with open(
            self.folder + "/info.player.json", "w", encoding="utf-8"
        ) as f:
            json.dump(my_json_file, f, ensure_ascii=False, indent=4)

    def run(self):
        # TODO: Solve this issue correctly
        from uvc import get_time_monotonic

        now = time.time()
        now_m = get_time_monotonic()
        self.start_time = now
        self.start_time_monotonic = now_m
        print("run start time = ", now)
        print("run start time monotonic= ", now_m)

        """ Main recording loop. """
        if not self.quiet:
            print("Started recording to {}".format(self.folder))

        # run hooks that need to be run in the main thread
        for recorder in self.recorders.values():
            recorder.run_pre_thread_hooks()

        # dispatch recording threads
        processes, queues, stop_event = self._init_processes(
            self.recorders, self._max_queue_size
        )
        self._start_processes(processes)

        start_time = time.time()

        while time.time() - now < self.duration:
            try:
                # get fps from queues
                # TODO can the recorder instance do this by itself?
                for recorder_name, recorder in self.recorders.items():
                    while not queues[recorder_name].empty():
                        recorder._fps_buffer.append(
                            queues[recorder_name].get()
                        )

                # display fps after self._stdout_delay seconds
                if (
                    not self.quiet
                    and time.time() - start_time > self._stdout_delay
                ):
                    f_strs = ", ".join(
                        "{}: {:.2f} Hz".format(c_name, c.current_fps)
                        for c_name, c in self.recorders.items()
                    )
                    print("\rSampling rates: " + f_strs, end="")

            except KeyboardInterrupt:
                print("KeyboardInterrupt!!")
                break
        self.run_duration = time.time() - now
        print("\nDone Recording!", self.run_duration)

        # stop recording threads
        self._stop_processes(processes, stop_event)

        # run hooks that need to be run in the main thread
        for recorder in self.recorders.values():
            recorder.run_post_thread_hooks()

        if not self.quiet:
            self.save_metadata()
            print("\nStopped recording")
