"""Make the worker-authored module importable as ``purl`` regardless of the
directory pytest is invoked from. The gate test imports ``from purl import
parse_purl``; the worker writes ``gate/purl.py`` next to this file.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
