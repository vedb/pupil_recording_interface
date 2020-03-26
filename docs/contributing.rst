Contributing
============

Environment setup
-----------------

#. Install miniconda: https://docs.conda.io/en/latest/miniconda.html

#. Clone the repository:

.. code-block:: console

    $ git clone https://github.com/vedb/pupil_recording_interface
    $ cd pupil_recording_interface

#. Create the conda environment:

.. code-block:: console

    $ conda env create

#. Activate the environment:

.. code-block:: console

    $ conda activate pupil-recording-interface

#. Install the package:

.. code-block:: console

    $ pip install -e --no-deps .


Reformatting
------------

Reformat with black:

.. code-block:: console

    $ black --target-version=py35 -l 79


Testing
-------

Lint with flake8:

.. code-block:: console

    $ flake8 pupil_recording_interface

Test with pytest

.. code-block:: console

    $ py.test


Documentation
-------------

Build docs with sphinx:

.. code-block:: console

    $ make -C docs/ html

Run doctests:

.. code-block:: console

    $ make -C docs/ doctest
