#!/usr/bin/env python
import os

from setuptools import setup, find_namespace_packages

version = f"{os.getenv('VERSION')}{os.getenv('PRE_RELEASE')}"

install_requires = ['PyYAML == 5.3.1',
                    'timeloop==1.0.2']

setup(name='example-greeting',
      version=version,
      description='Example package Hi',
      author='Matthew Kennedy',
      packages=find_namespace_packages(include=['example.*']),
      install_requires=install_requires,
      zip_safe=False)
