#!/usr/bin/env python

import os
import sys
import io

from setuptools import setup, find_packages


setup(
    name='jmespath',
    version='0.9.0',
    description='JSON Matching Expressions',
    long_description=io.open('README.rst', encoding='utf-8').read(),
    author='James Saryerwinnie',
    author_email='js@jamesls.com',
    url='https://github.com/jmespath/jmespath.py',
    scripts=['bin/jp.py'],
    packages=find_packages(exclude=['tests']),
    classifiers=(
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ),
)
