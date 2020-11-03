What's New
==========

v0.3.0 (November 3rd, 2020)
---------------------------

New features
~~~~~~~~~~~~

* Key presses from ``VideoDisplay`` windows are broadcast and stored in the
  ``keypresses`` deque by the mananger.
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
