import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))

requires = [
    'falcon==3.0.*',
    'falcon-sqla==0.2.0',
    'configparser==5.0.*',
    'psycopg2==2.8.4',
    'gunicorn==20.1.*',
    'alembic==1.5.*',
    'SQLAlchemy==1.3.*',
]

tests_require = [
    'pytest>= 3.7.4, <=6.1.2',
    'pytest-cov',
]

setup(
    name='cyberdas',
    version='0.0',
    description='CyberDAS API',
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Falcon',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
    ],
    author='CyberDAS Development',
    author_email='ivanakostelov@gmail.com',
    url='https://github.com/CyberDAS-Dev/API',
    keywords='',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    extras_require={
        'testing': tests_require,
    },
    install_requires=requires,
    entry_points={
       'console_scripts': [
           'initialize_db = cyberdas.scripts.initialize_db:main'
       ],
    },
)
