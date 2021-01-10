SSST - SunSpec Service Tool
===========================

Resources
---------

=================================  =================================  =============================

`Documentation <documentation_>`_  `Read the Docs <documentation_>`_  |documentation badge|
`Issues <issues_>`_                `GitHub <issues_>`_                |issues badge|

`Repository <repository_>`_        `GitHub <repository_>`_            |repository badge|
`Tests <tests_>`_                  `GitHub Actions <tests_>`_         |tests badge|
`Coverage <coverage_>`_            `Codecov <coverage_>`_             |coverage badge|

`Distribution <distribution_>`_    `PyPI <distribution_>`_            | |version badge|
                                                                      | |python versions badge|
                                                                      | |python interpreters badge|

=================================  =================================  =============================


Introduction
------------

This is an exploratory application using QTrio.


Installation
------------

This application is not yet published to PyPI nor built into directly runnable packages.
It is installable via either cloning and installing or directly via the Git repository.
When installing the Python package itself, it is recommended to work in a virtual environment.
For a quick introduction, see `Python Virtual Environments in Five Minutes <virtual_environments>`_.

.. tab:: Unix/macOS

    .. code-block:: console

        $ myvenv/bin/pip install git+https://github.com/altendky/ssst

.. tab:: Windows

    .. code-block:: console

        $ myvenv/scripts/pip install git+https://github.com/altendky/ssst

.. _virtual_environments: https://chriswarrick.com/blog/2018/09/04/python-virtual-environments/


Running
-------

Two main means of launching the application are provided.
A directly runnable console script and a Python module runnable using ``python -m``.

.. tab:: Unix/macOS

    .. code-block:: console

        $ myvenv/bin/ssst gui

    .. code-block:: console

        $ myvenv/bin/python -m ssst gui

.. tab:: Windows

    .. code-block:: console

        $ myvenv/scripts/ssst gui

    .. code-block:: console

        $ myvenv/scripts/python -m ssst gui


.. _documentation: https://ssst.readthedocs.io
.. |documentation badge| image:: https://img.shields.io/badge/docs-read%20now-blue.svg?color=royalblue&logo=Read-the-Docs&logoColor=whitesmoke
   :target: `documentation`_
   :alt: Documentation

.. _distribution: https://pypi.org/project/ssst
.. |version badge| image:: https://img.shields.io/pypi/v/ssst.svg?color=indianred&logo=PyPI&logoColor=whitesmoke
   :target: `distribution`_
   :alt: Latest distribution version

.. |python versions badge| image:: https://img.shields.io/pypi/pyversions/ssst.svg?color=indianred&logo=PyPI&logoColor=whitesmoke
   :alt: Supported Python versions
   :target: `distribution`_

.. |python interpreters badge| image:: https://img.shields.io/pypi/implementation/ssst.svg?color=indianred&logo=PyPI&logoColor=whitesmoke
   :alt: Supported Python interpreters
   :target: `distribution`_

.. _issues: https://github.com/altendky/ssst/issues
.. |issues badge| image:: https://img.shields.io/github/issues/altendky/ssst?color=royalblue&logo=GitHub&logoColor=whitesmoke
   :target: `issues`_
   :alt: Issues

.. _repository: https://github.com/altendky/ssst
.. |repository badge| image:: https://img.shields.io/github/last-commit/altendky/ssst.svg?color=seagreen&logo=GitHub&logoColor=whitesmoke
   :target: `repository`_
   :alt: Repository

.. _tests: https://github.com/altendky/ssst/actions?query=branch%3Amaster
.. |tests badge| image:: https://img.shields.io/github/workflow/status/altendky/ssst/CI/master?color=seagreen&logo=GitHub-Actions&logoColor=whitesmoke
   :target: `tests`_
   :alt: Tests

.. _coverage: https://codecov.io/gh/altendky/ssst
.. |coverage badge| image:: https://img.shields.io/codecov/c/github/altendky/ssst/master?color=seagreen&logo=Codecov&logoColor=whitesmoke
   :target: `coverage`_
   :alt: Test coverage
