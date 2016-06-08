import sys, os
import logging as L
L.basicConfig(level='DEBUG')

sys.path.append(os.path.dirname(__file__))

from slicer.slicer_main import run_standalone
sys.exit(run_standalone())