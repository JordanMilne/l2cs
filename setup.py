#!/usr/bin/env python2.7

try:
    from setuptools import setup
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup

setup(
    name='l2cs',
    version="1.0.1",
    author='Keith Mitchell',
    author_email='kemitche@reddit.com',
    description=("Rewrites queries from lucene syntax to"
                 " Amazon Cloudsearch syntax"),
    license='BSD',
    url="http://github.com/kemitche/l2cs",
    install_requires=["whoosh>=2.3"],
    py_modules=['l2cs'],
    include_package_data=True,
    test_suite="test_l2cs",
)
