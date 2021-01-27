.. _examples:

Examples
========

Prerequisites
-------------

We recommend using pupil_recording_interface in a dedicated conda environment,
especially if you want to use the online functionality. For Linux users, we
provide an :download:`environment file<../_static/envs/environment-lnx64.yml>`
that you can download and set up with:

.. code-block:: console

    $ conda env create -f environment-lnx64.yml

For the notebook versions of the examples, it is sufficient to have Jupyter
notebook installed in your base environment alongside ``nb_conda``:

.. code-block:: console

    $ conda install -n base nb_conda

Now you can open any of the example notebooks, go to *Kernel > Change kernel*
and select *Python [conda env:pri-examples]*.
