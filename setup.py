#!/usr/bin/env python

import os
import sys

from setuptools import setup, find_packages


setup(
    name='jamespath',
    version='0.0.1',
    description='JSON Matching Expressions',
    long_description=open('README.rst').read(),
    author='James Saryerwinnie',
    author_email='js@jamesls.com',
    url='https://github.com/boto/jamespath',
    scripts=[],
    packages=find_packages(),
    install_requires=[
        'ply==3.4',
    ],
    classifiers=(
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
    ),
)
