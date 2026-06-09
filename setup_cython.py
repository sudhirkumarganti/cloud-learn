"""Cython build configuration for security-critical modules.

Usage (in Dockerfile builder stage):
    pip install cython
    python setup_cython.py build_ext --inplace
    rm core/state_integrity.py core/tier_policy.py core/license_remote.py
"""
from setuptools import setup
from Cython.Build import cythonize

setup(
    ext_modules=cythonize([
        "core/state_integrity.py",
        "core/tier_policy.py",
        "core/license_remote.py",
    ], compiler_directives={"language_level": "3"}),
)
