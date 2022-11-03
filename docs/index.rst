
******************
fiberoptics-common
******************

**Date**: |today| **Version**: |version|

Getting started
===============

*fiberoptics-common* is a Python package implementing common functionality used across fiberoptics repositories.
The latest version can be installed directly from GitHub using *pip*.

.. code-block:: bash

    pip install git+https://github.com/equinor/fiberoptics-common.git

The package contains multiple submodules, each requiring a different set of dependencies. For instance, the ``fiberoptics.common.auth`` submodule depends on ``azure-identity``, which is installed using the *extras* syntax as shown in example 7 in the `pip documentation <https://pip.pypa.io/en/stable/cli/pip_install/#examples>`_. The name of the *extras* is the same as the submodule.

.. code-block:: bash

   pip install fiberoptics-common[auth]@git+https://github.com/equinor/fiberoptics-common.git

Dependencies for all submodules can be installed at once using ``all``.

``fiberoptics.common.misc`` is the only submodule that does not require any dependencies, and its contents is exposed under ``fiberoptics.common`` for convenience (and backwards compatibility).

API reference
=============

Here is a list of all submodules. Click on one of them to start browsing available functionality.

.. autosummary::
   :template: autosummary/main.rst
   :toctree: api
   :recursive:

   fiberoptics.common.auth
   fiberoptics.common.io
   fiberoptics.common.misc
   fiberoptics.common.plot
   fiberoptics.common.processing
   fiberoptics.common.scikit

