#!/usr/bin/python2

from distutils.core import setup, Extension

setup(name='rpmhelper', version='0.02',
      description='Helper scripts for rpm',
      author='Levin Du', author_email='zsdjw@21cn.com',
      data_files=[('bin', ['rpm-diff',
                           'rpm-findold',
                           'rpm-findnewest',
                           'rpm-parsespec',
                           'mb-init', 
                           'mb-build', 
                           'mb-prepare', 
                           'mb-pull-pkg', 
                           'mb-push-pkg', 
                           'mb-fetch-fcpkg', 
                           ])],
      url='http://www.linuxfans.org',
      packages=['rpmhelper'])
