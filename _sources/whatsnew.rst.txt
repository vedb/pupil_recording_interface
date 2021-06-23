What's New
==========

v0.5.0 (June 23rd, 2021)
------------------------

Breaking changes
~~~~~~~~~~~~~~~~
* The test recording in the examples is not part of the package anymore but
  instead downloaded and cached through the ``pooch`` library.
  This means that ``TEST_RECORDING`` is not working anymore and is replaced
  by ``get_test_recording``.

Bug fixes & improvements
~~~~~~~~~~~~~~~~~~~~~~~~
* Updated the default test recording to contain post-hoc gaze mapped by
  Pupil Player v3.


v0.4.1 (February 22nd, 2021)
----------------------------

Bug fixes & improvements
~~~~~~~~~~~~~~~~~~~~~~~~
* Fixed ``exposure_mode="auto"`` not working in ``VideoDeviceUVC``.
* Fixed extrinsics not being saved by ``CamParamEstimator``.
* Added ``available_controls`` attribute to ``VideoDeviceUVC`` that returns
  legal values for UVC controls and ``controls`` can be set by assigning
  a mapping from control names to new values.


v0.4.0 (January 28th, 2021)
---------------------------

New features
~~~~~~~~~~~~

* Package is now available via conda from our own channel.
* Devices, streams and processes can now be used as context managers which
  starts and stops them automatically. This makes the ``Session`` context
  manager obsolete, which is being deprecated.
* New ``VideoFileSyncer`` process for syncing video streamed from files.

Bug fixes & improvements
~~~~~~~~~~~~~~~~~~~~~~~~
* Fixed ``VideoDeviceUVC.get_frame_and_timestamp`` not working in Jupyter
  notebook.
* Fixed bug in ``load_dataset`` for accelerometer and gyroscope streams.


v0.3.0 (December 8th, 2020)
---------------------------

New features
~~~~~~~~~~~~

* Key presses from ``VideoDisplay`` windows are broadcast and stored in the
  ``keypresses`` deque by the manager.
* ``CircleGridDetector`` now accepts a ``scale`` parameter to speed up
  detection at the expense of accuracy for high-resolution streams.
* ``CamParamEstimator`` now shows a persistent overlay of previously detected
  circle patterns for the stream it is attached to.
* Processes and pipelines have access to their parent stream via the
  ``context`` attribute, if applicable.
* Processes can add display hooks to the packet that are picked up by
  ``VideoDisplay``.
* New ``load_pldata`` and ``save_pldata`` top-level methods.

Bug fixes & improvements
~~~~~~~~~~~~~~~~~~~~~~~~

* Fixed several bugs in ``CamParamEstimator`` regarding extrinsics estimation.
* Additionally save ``info.player.json`` at the start of the recording.
* Support loading source timestamps from .pldata files for video streams.
* Don't reopen ``VideoDisplay`` windows closed by user.


v0.2.1 (October 23rd, 2020)
---------------------------

Bug fixes & improvements
~~~~~~~~~~~~~~~~~~~~~~~~

* Set default exposure mode of ``VideoDeviceUVC`` to ``"auto"``.
* Added ``max_width`` parameter to ``VideoDisplay``.
* Disabled showing plots in Validation class.
* Fixed loading of broken recordings (with missing timestamps or corrupt
  pldata files).
* Fixed bug when loading 3D gaze with only binocular data.
* Fixed support for configs with ``device_uid=None``.


v0.2.0 (October 6th, 2020)
--------------------------

New features
~~~~~~~~~~~~

* Loaded gaze now contains the eye data that produced the mapping (left, right,
  both eyes) as well as the 3D eye centers and gaze normals.
* The ``load_raw_frame``, ``load_frame``, ``read_frames`` and ``load_dataset``
  methods of ``VideoReader`` and ``OpticalFlowReader`` now accept both
  timestamps and indexes as parameters.
* Streams can be started even when the underlying devices aren't connected
  with ``allow_failure=True``.
* Added ``scale``, ``detection_method`` and ``marker_size`` parameters to
  ``CircleDetector`` to allow more fine-grained control over detection.
  ``detection_method="vedb"`` is a new detection method that is less stable
  but significantly faster than the default.
* Added a ``Validation`` process that extends ``Calibration``, adding plots
  showing the coverage of the world camera FOV by the calibration marker and
  of the eye camera FOV by the pupils.
* Added a new example ``validate.py`` that demonstrates usage of the new
  circle detection method and the validation.
* Added experimental support for a ``PyAV``-based video encoder
  (``VideoEncoderAV``).
* Added ``nan_format`` parameter to ``StreamManager.format_status``.

Bug fixes
~~~~~~~~~

* Fixed devices not being able to shut down when in restart loop.
* Fixed blank window opening when starting a ``VideoDisplay`` process with
  ``paused=True``.


v0.1.0 (June 3rd, 2020)
-----------------------

Mostly feature-complete release that supports streaming, recording and
processing of Pupil Core streams as well as reading of recordings.
