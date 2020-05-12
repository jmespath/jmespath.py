#!/usr/bin/env python

import io
import sys
import warnings

from setuptools import setup, find_packages


if sys.version_info[:2] <= (2, 6) or ((3, 0) <= sys.version_info[:2] <= (3, 3)):
    python_ver = '.'.join(str(x) for x in sys.version_info[:3])

    warnings.warn(
        'You are using Python {0}, which will no longer be supported in '
        'version 0.11.0'.format(python_ver),
        DeprecationWarning)


setup(
    name='jmespath',
    version='0.10.0',
    description='JSON Matching Expressions',
    long_description=io.open('README.rst', encoding='utf-8').read(),
    author='James Saryerwinnie',
    author_email='js@jamesls.com',
    url='https://github.com/jmespath/jmespath.py',
    scripts=['bin/jp.py'],
    packages=find_packages(exclude=['tests']),
    license='MIT',
    python_requires='>=2.6, !=3.0.*, !=3.1.*, !=3.2.*',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],
)
