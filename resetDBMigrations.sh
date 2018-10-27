#!/bin/bash

read -p "This will restart the database and restore default values. Are you sure? [y/n]" -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
        rm db.sqlite3
        find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
        find . -path "*/migrations/*.pyc"  -delete
        python manage.py makemigrations filler
        python manage.py migrate
        python manage.py loaddata */fixtures/*
fi