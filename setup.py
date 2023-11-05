#!/usr/bin/env python3

# Copyright (C) 2007-2017  CAMd
# Please see the accompanying LICENSE file for further information.

import os
import sys
from glob import glob
from os.path import join

from setuptools import find_packages, setup
from setuptools.command.build_py import build_py as _build_py
from setuptools_scm import ScmVersion

python_min_version = (3, 8)
python_requires = '>=' + '.'.join(str(num) for num in python_min_version)


if sys.version_info < python_min_version:
    raise SystemExit(f'Python {python_requires} is required!')


install_requires = [
    'numpy>=1.18.5',  # June 2020
    'scipy>=1.4.1',  # December 2019
    'matplotlib>=3.3.4',  # January 2021 (3.3.0 is July 2020)
]


extras_require = {
    'docs': [
        'sphinx',
        'sphinx_rtd_theme',
        'pillow',
    ],
    'test': [
        'pytest>=6.2.5',
        'pytest-xdist>=2.1.0',
    ],
}

# Optional: spglib >= 1.9


with open('README.rst') as fd:
    long_description = fd.read()


package_data = {
    'ase': [
        'spacegroup/spacegroup.dat',
        'collections/*.json',
        'db/templates/*',
        'db/static/*',
        # make ASE a PEP 561 compliant package so that
        # other packages can use ASE's type hints:
        'py.typed',
    ],
    'ase.test': ['pytest.ini', 'testdata/*', 'testdata/*/*', 'testdata/*/*/*'],
}


class build_py(_build_py):
    """Custom command to build translations."""

    def __init__(self, *args, **kwargs):
        _build_py.__init__(self, *args, **kwargs)
        # Keep list of files to appease bdist_rpm.  We have to keep track of
        # all the installed files for no particular reason.
        self.mofiles = []

    def run(self):
        """Compile translation files (requires gettext)."""
        _build_py.run(self)
        msgfmt = 'msgfmt'
        status = os.system(msgfmt + ' -V')
        if status == 0:
            for pofile in sorted(glob('ase/gui/po/*/LC_MESSAGES/ag.po')):
                dirname = join(self.build_lib, os.path.dirname(pofile))
                if not os.path.isdir(dirname):
                    os.makedirs(dirname)
                mofile = join(dirname, 'ag.mo')
                print()
                print(f'Compile {pofile}')
                status = os.system(
                    '%s -cv %s --output-file=%s 2>&1' % (msgfmt, pofile, mofile)
                )
                assert status == 0, 'msgfmt failed!'
                self.mofiles.append(mofile)

    def get_outputs(self, *args, **kwargs):
        return _build_py.get_outputs(self, *args, **kwargs) + self.mofiles


def set_version(version: ScmVersion) -> str:
    from setuptools_scm.version import guess_next_version

    # ! Add appropriate version specs

    return version.format_next_version(guess_next_version, "{guessed}b{distance}")


setup(
    name='ase',
    use_scm_version={"version_scheme": set_version},
    description='Atomic Simulation Environment',
    url='https://wiki.fysik.dtu.dk/ase',
    maintainer='ASE-community',
    maintainer_email='ase-users@listserv.fysik.dtu.dk',
    license='LGPLv2.1+',
    platforms=['unix'],
    packages=find_packages(),
    python_requires=python_requires,
    install_requires=install_requires,
    extras_require=extras_require,
    package_data=package_data,
    entry_points={'console_scripts': ['ase=ase.cli.main:main']},
    long_description=long_description,
    cmdclass={'build_py': build_py},
    classifiers=[
        'Development Status :: 6 - Mature',
        'License :: OSI Approved :: '
        'GNU Lesser General Public License v2 or later (LGPLv2+)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Topic :: Scientific/Engineering :: Physics',
    ],
)
