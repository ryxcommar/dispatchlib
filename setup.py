import re
from setuptools import setup


with open('dispatchlib/__init__.py', encoding='utf8') as f:
    version = re.search(r"__version__ = '(.*?)'", f.read()).group(1)

with open('README.md', encoding='utf8') as f:
    long_description = f.read()


setup(
    name='dispatchlib',
    version=version,
    project_urls={
        'Documentation': 'https://ryxcommar.github.io/dispatchlib/',
        'Source': 'https://github.com/ryxcommar/dispatchlib',
        'Tracker': 'https://github.com/ryxcommar/dispatchlib/issues',
    },
    author='ryxcommar',
    author_email='ryxcommar@gmail.com',
    description='Tools for creating dispatchable functions.',
    long_description=long_description,
    py_modules=['dispatchlib'],
    license='MIT',
    python_requires='>=3.6',
    install_requires=[
        'sortedcontainers>=2',
        'typeguard>=2.9'
    ],
)
