.. -*- mode: rst -*-

|Build|_

.. |Build| image:: https://github.com/vedb/pupil_recording_interface/workflows/build/badge.svg
.. _Build: https://github.com/vedb/pupil_recording_interface/actions


pupil_recording_interface
=========================

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

    pip install git+https://github.com/vedb/pupil_recording_interface.git

If you are using the conda package manager, install these dependencies first:

.. code-block:: console

    conda install xarray scipy msgpack-python opencv

Afterwards, install the package via ``pip`` as detailed above.
