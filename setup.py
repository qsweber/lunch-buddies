from setuptools import find_packages, setup

setup(
    name='lunch-buddies',
    version='0.0.1',
    description='Lunch buddies',
    author='Quinn Weber',
    maintainer='Quinn Weber',
    maintainer_email='quinnsweber@gmail.com',
    packages=find_packages(exclude=('tests',)),
    install_requires=(
        'flask',
        'boto3',
    ),
)
