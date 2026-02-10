#!python
from setuptools import setup, find_packages
from os.path import exists

readme = open('README.md') if exists('README.md') else open('../README.md')
version = open('gnucash_web/version.txt')

setup(
    name='gnucash_web',
    version=version.read().strip(),
    author='Joshua Bachmeier',
    author_email='joshua@bachmeier.cc',
    description='A simple, easy to use, mobile-friendly webinterface for GnuCash intended for self-hosting',
    long_description=readme.read(),
    long_description_content_type='text/markdown; charset=UTF-8; variant=GFM',
    url='https://github.com/joshuabach/gnucash-web',
    project_urls={
        'Bug Tracker' : 'https://github.com/joshuabach/gnucash-web/issues',
        'Source Code' : 'https://github.com/joshuabach/gnucash-web',
    },
    license='GPLv3+',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Framework :: Flask',
        'Intended Audience :: Financial and Insurance Industry',
        'Intended Audience :: Information Technology',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application'
    ],
    keywords=['bootstrap', 'flask', 'web', 'gnucash'],

    packages=find_packages(),
    package_data={
        'gnucash_web': [
            'version.txt',
            'templates/*.j2',
            'static/*.js', 'static/*.css',
            'static/bootstrap/css/*.min.css',
            'static/bootstrap/js/*.min.js',
            'static/bootstrap-icon-font/*.css',
            'static/bootstrap-icon-font/fonts/*',
            'static/selectize/css/*.css',
            'static/selectize/js/*.js',
            'static/img/official/*/apps/*',
        ],
    },

    # Python 3.10+ required for modern Flask/Werkzeug compatibility
    python_requires=">=3.10",

    # piecash 1.2.1 requires SQLAlchemy 1.x (does not support 2.0 yet)
    install_requires=[
        'Flask>=3.0.0',
        'Werkzeug>=3.0.0',
        'piecash>=1.2.0',
        'SQLAlchemy>=1.4,<2.0',
        'babel>=2.9.1',
        'requests>=2.27.1',
    ],
    extras_require={
        'pgsql': 'psycopg2',
        'mysql': 'mysqlclient',
    },

    entry_points={
        'console_scripts': [
            'gnucash-web = gnucash_web:cli',
        ],
    },
)
