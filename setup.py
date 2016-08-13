import os
from setuptools import setup, find_packages

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "bloodedguild-forums-api",
    version = "0.0.1",
    author = "Jake Torrance",
    author_email = "andrewjcarter@gmail.com",
    packages = find_packages(),
    description = ("An demonstration of how to create, document, and publish "
                                   "to the cheese shop a5 pypi.org."),
    #packages = ['bloodedguild_api','bloodedguild_api.api'],
    keywords = "example documentation tutorial",
    url = "bloodedguild_forums_api",
    long_description=read('README'),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Topic :: Utilities",
        "License :: OSI Approved :: BSD License",
    ],
)
