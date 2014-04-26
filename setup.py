#!/usr/bin/env python

from setuptools import setup

setup(name='pycimc',
      version='0.5.0',
      description='Python interface to Cisco UCS rack-mount server CIMC XML API',
      author='Rob Horner',
      author_email='robert@horners.org',
      py_modules=['pycimc',
                  'pycimcexpect',
                  'exception_mapper'],
      install_requires=[
          "requests >= 2.2.1",
          ],
      )
