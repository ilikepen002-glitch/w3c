"""Explicit input for current-map tests; never silently substitute the root map."""
import os
from pathlib import Path
import unittest


def candidate_map(variable='PYTHON_CANDIDATE_MAP'):
    path = os.environ.get(variable)
    if not path:
        raise unittest.SkipTest('Actual map NOT COVERED: supply --candidate-map to Run-PythonChecks.py or set ' + variable)
    path = Path(path).resolve(strict=True)
    if not path.is_file():
        raise ValueError('Candidate map must be a file: ' + str(path))
    return path
