What's New
==========

master branch
-------------

* Loaded gaze now contains the eye data that produced the mapping (left, right,
  both eyes) as well as the 3D eye centers and gaze normals.
* The ``load_raw_frame``, ``load_frame``, ``read_frames`` and ``load_dataset``
  methods of ``VideoReader`` and ``OpticalFlowReader`` now accept both
  timestamps and indexes as parameters.


v0.1.0 (June 3rd, 2020)
-----------------------

Mostly feature-complete release that supports streaming, recording and
processing of Pupil Core streams as well as reading of recordings.
