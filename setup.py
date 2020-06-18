#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from setuptools import setup, find_packages

__version__ = os.getenv("VERSION", "0.0.1")

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="pitcher",
    author="Ben Kersten",
    author_email="ben.kersten@twobulls.com",
    version=__version__,
    license="MIT",
    url="https://github.com/twobulls/pitcher",
    description="Python web framework for API Gateway",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(exclude=["tests"]),
    python_requires='>=3.7',
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
)
