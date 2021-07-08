.. -*- mode: rst -*-

|Build|_ |black|_

.. |Build| image:: https://github.com/vedb/pupil_recording_interface/workflows/build/badge.svg
.. _Build: https://github.com/vedb/pupil_recording_interface/actions

.. |black| image:: https://img.shields.io/badge/code%20style-black-000000.svg
.. _black: https://github.com/psf/black


pupil_recording_interface
=========================

.. TODO document recording/gaze estimation capabilities

This Python package provides a user-friendly way of working with recordings
from the Pupil Core eye tracking system. It includes interfaces for gaze and
video data as well as some additional features such as optical flow
calculation or recording of head tracking data.

Documentation
-------------

The documentation can be found at https://vedb.github.io/pupil_recording_interface

Installation
------------

pupil_recording_interface can be installed via ``pip``:

.. code-block:: console

    $ pip install opencv-python git+https://github.com/vedb/pupil_recording_interface.git

or via ``conda`` from our own channel:

.. code-block:: console

    $ conda install -c vedb -c conda-forge pupil_recording_interface

For features like streaming video from the Pupil Core cameras, recording data
or pupil detection, please refer to the `installation instructions`_ in the
documentation.

.. _installation instructions: https://vedb.github.io/pupil_recording_interface/installation.html
