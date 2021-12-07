from setuptools import setup, find_packages

setup(
    name='gsa',
    version='0.0.1',
    url="http://github.com/mailund/gsa",
    author="Thomas Mailund",
    author_email="thomas@mailund.dk",
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'gsa=gsa.main:main',
        ],
    },
    install_requires=[
        'colorama',
        'types-colorama',
        'pyyaml',
        'pystr'
    ],
)
