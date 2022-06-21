#!/usr/bin/env python
import os

from setuptools import setup, find_namespace_packages

version = os.getenv('SEMVER')

install_requires = ['PyYAML == 5.3.1',
                    'timeloop==1.0.2']

setup(name=os.getenv('APP'),
      version=version,
      description='Example package Hi',
      author='Matthew Kennedy',
      packages=find_namespace_packages(include=['example.*']),
      install_requires=install_requires,
      zip_safe=False)
