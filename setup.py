# -*- coding: utf-8 -*-
from setuptools import find_packages
from setuptools import setup


long_description = open('README.rst').read() + '\n'
changelog = open('CHANGELOG.rst').read()

setup(
    name='twitter-analyzer',
    version='1.0.1',
    description='Analyze your twitter account',
    long_description=long_description + changelog,
    keywords=['asyncio', 'twitter', 'sqlite'],
    author='Nathan Van Gheem',
    author_email='vangheem@gmail.com',
    classifiers=[
        'License :: OSI Approved :: BSD License',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    url='https://github.com/vangheem/twitter-analyzer',
    license='BSD',
    setup_requires=[
        'pytest-runner',
    ],
    zip_safe=True,
    include_package_data=True,
    packages=find_packages(),
    install_requires=[
        'aiohttp',
        'python-dateutil',
        'textblob',
        'click',
        'sqlalchemy',
        'sqlalchemy_aio',
        'peony-twitter[aiohttp]',
    ],
    extras_require={
        'test': [
            'pytest',
            'pytest-asyncio>=0.8.0',
            'pytest-cov',
            'coverage>=4.0.3'
        ]
    },
    entry_points={
        'console_scripts': [
            'tanalyze = tanalyzer.cli:cli'
        ]
    }
)
