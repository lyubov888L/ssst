import setuptools
import os
import sys
# Must insert directory of setup.py to path in order to import local file versioneer because of PEP 517.
sys.path.insert(0, os.path.dirname(__file__))
import versioneer

setuptools.setup(
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
)
