import os
from setuptools import setup, find_packages

os.chdir(os.path.dirname(os.path.realpath(__file__)))


def get_requirements():
    req_lines = open('requirements.txt', 'r').readlines()
    reqs = []
    for line in req_lines:
        line = line.strip()
        if line and not line.startswith('#'):
            reqs.append(line)
    return reqs

VERSION_PATH = os.path.join('evennia', 'VERSION.txt')


def get_version():
    return open(VERSION_PATH).read().strip()


def package_data():
    file_set = []
    for root, dirs, files in os.walk('evennia'):
        for f in files:
            file_name = os.path.relpath(os.path.join(root, f), 'evennia')
            file_set.append(file_name)
    return file_set


def template_data():
    """
    Finds all of the static and template dirs in the project and adds 
    them to the package data.

    By default setup.py only installs Python modules.
    """
    data = []
    for dirname, _, files in os.walk("game_template"):
        for root, ___, current_files in os.walk(dirname):
            for f in current_files:
                file_name = os.path.join(root, f)
                data.append((os.path.join('share', 'evennia', root), [file_name]))
    return data

setup(
    name='evennia',
    version=get_version(),
    description='A full-featured MUD building toolkit.',
    packages=find_packages(exclude=['game_template', 'game_template.*']),
    scripts=['bin/evennia', 'bin/evennia_runner.py'],
    install_requires=get_requirements(),
    package_data={'': package_data()},
    data_files=template_data(),
    zip_safe=False
)
