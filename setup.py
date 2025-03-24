#!/usr/bin/env python3

from setuptools import setup
import sys
import os

# Import the build function from build.py
sys.path.insert(0, os.path.abspath('.'))
from build import build

if __name__ == "__main__":
    kwargs = {}
    build(kwargs)
    setup(**kwargs)