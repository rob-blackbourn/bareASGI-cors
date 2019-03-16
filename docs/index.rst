Cross Origin Resource Sharing With bareASGI
===========================================

CORS support for `bareASGI <https://bareasgi.readthedocs.io/en/latest>`_.

Installation
------------

The package can be installed with pip.

.. code-block:: bash

    pip install bareasgi-cors

This is a Python3.7 and later package with dependencies on:

* bareASGI

Usage
-----

The support is implemented as middleware.

.. code-block:: python

    from bareasgi import Application
    from bareasgi_cors import CORSMiddleware

    cors_middleware = CORSMiddleware()
    app = Application(middlewares=[cors_middleware])

Post Routes
===========

Before issuing a POST across origin an OPTION request will be made. This means that
every post route must also support OPTION.

Here is an example:

.. code-block:: python

    app.http_router.add({'POST', 'OPTIONS'}, '/info', set_info)



.. toctree::
    :maxdepth: 2
    :caption: Contents:

    api

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
