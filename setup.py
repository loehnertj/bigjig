import sys
if sys.version_info[0] < 3:
    raise RuntimeError("python 3 only")
import os
from setuptools import setup

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

# TODO: Fail without pyqt4

setup(
    name = "bigjig",
    version = "0.0.1",
    author = "Johannes Loehnert",
    author_email = "loehnert.kde@gmx.de",
    description = ("Serious jigsaw puzzle game"),
    license = "BSD",
    keywords = "game",
    url = "https://github.com/loehnertj/bigjig",
    packages=['neatocom', 'puzzleboard', 'qtpuzzle', 'slicer'],
    entry_points = {
        'gui_scripts': [
            'bigjig = qtpuzzle.__main__:main'
            ],
        },
    long_description=read('README'),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Topic :: Games/Entertainment :: Puzzle Games",
        "License :: OSI Approved :: BSD License",
    ],
)

