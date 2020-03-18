#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from setuptools import setup, find_packages

__version__ = os.getenv("VERSION", "0.1")

setup(
    name="pitcher",
    author_email="ben.kersten@twobulls.com",
    version=__version__,
    license="MIT",
    description="Microframework",
    packages=find_packages(exclude=["tests"]),
)
