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

    $ conda activate pri

#. Install the package:

.. code-block:: console

    $ pip install -e --no-deps .


Reformatting / linting
----------------------

Reformat with black:

.. code-block:: console

    $ black .

Lint with flake8:

.. code-block:: console

    $ flake8 pupil_recording_interface

The above steps are also run by ``pre-commit``. Run this to automatically
reformat and lint before every commit:

.. code-block:: console

    $ pre-commit install


Testing
-------

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
