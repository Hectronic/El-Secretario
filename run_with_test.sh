#!/bin/bash
export PYTHONPATH=$PYTHONPATH:$(pwd)
./venv/bin/python -m unittest discover -v tests
