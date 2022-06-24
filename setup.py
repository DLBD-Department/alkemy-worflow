#!/usr/bin/env python
import os
from pathlib import Path
from setuptools import setup, find_packages

HERE = Path(__file__).parent

install_requires = [line.rstrip() for line in open(HERE / 'requirements.txt')]

VERSION_FILE = HERE / 'alkemy_workflow' / 'VERSION'

with open(VERSION_FILE) as f:
    version = f.read().strip()

setup(
    name='alkemy_workflow',
    version=version,
    description='Alkemy Workflow',
    long_description='Alkemy Git Workflow',
    classifiers=[
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ],
    keywords='git workflow',
    url='https://github.com/DLBD-Department/alkemy-worflow',
    license='MIT',
    packages=find_packages(exclude=['ez_setup', 'examples']),
    include_package_data=True,
    zip_safe=True,
    install_requires=install_requires,
    entry_points={
        'console_scripts': [
            'aw=alkemy_workflow.cli:main',
        ],
    },
    test_suite='tests',
    tests_require=['pytest'],
)
