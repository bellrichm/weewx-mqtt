#! /bin/bash
PYTHONPATH=bin:../weewx/bin coverage3 run -p --branch -m unittest discover bin/user/tests; 
coverage combine
coverage html --include bin/user/mqtt.py