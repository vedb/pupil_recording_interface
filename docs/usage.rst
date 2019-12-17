Usage
=====

Export gaze data to netCDF:

.. code-block:: python

    import pupil_recording_interface as pri

    pri.write_netcdf('/path/to/recording', gaze='recording')

This will create a ``gaze.nc`` file in the ``/path/to/recording/exports``
folder.

Load gaze and odometry data as xarray datasets:

.. code-block:: python

    import pupil_recording_interface as pri

    gaze, odometry = pri.load_dataset(
        '/path/to/recording', gaze='recording', odometry='recording')

For more details, please refer to the :ref:`api-reference` section.
