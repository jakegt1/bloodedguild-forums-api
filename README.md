# Bloodedguild Forums API
This is a python flask API written as a backend for a MVC frontend written in react.js.

## Requirements
* python3
* python-flask
* flask-jwt

(Both flask-jwt and python-flask can be installed via pip3.)

It also requires a postgres backend that can be configured in config.py. The SQL used in the database is available at https://github.com/jakegt1/bloodedguild-forums-sql. 

## Setup
Setup using python3 setup.py install as normal. 

To test manually, do python3 setup.py develop then python3 -m bloodedguild_forums_api.
