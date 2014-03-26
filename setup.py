#!/usr/bin/env python

from distutils.core import setup

setup(name='pycimc',
      version='0.1',
      description='Python interface to Cisco UCS rack-mount server CIMC XML API',
      author='Rob Horner',
      author_email='robert@horners.org',
      py_modules=['pycimc', 'pycimcexpect'],
      )
