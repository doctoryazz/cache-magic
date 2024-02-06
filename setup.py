from setuptools import setup

from codecs import open
from os import path

# Get the long description from the README file
long_description = ''
try:
    with open('README.rst', encoding='utf8') as f:
        long_description = f.read()
except IOError:
    print("could not locate README")
    pass


setup(
    name='cache-magic',
    version='1.0.4.1',
    packages=['cache_magic'],
    url='https://github.com/doctoryazz/cache-magic',
    long_description=long_description,
    license='BSD-3-Clause',
    author='Doctor Yazz',
    author_email='doctoryazz@gmail.com',
    description='Versatile cache line magic for jupyter notebooks, based on https://pypi.org/project/cache-magic/',
    classifiers=[
        'Development Status :: 7 - Inactive',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Framework :: Jupyter',
        'Intended Audience :: Science/Research',
        'License :: Other/Proprietary License',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Scientific/Engineering :: Information Analysis'
    ],
    install_requires=[
        'astunparse',
        'IPython',
        'tabulate'
    ],
)
