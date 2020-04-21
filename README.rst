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

    $ pip install git+https://github.com/vedb/pupil_recording_interface.git

If you are using the conda package manager, install these dependencies first:

.. code-block:: console

    $ conda install xarray scipy msgpack-python opencv

Afterwards, install the package via ``pip`` as detailed above.
