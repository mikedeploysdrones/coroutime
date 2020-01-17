from setuptools import setup, find_packages


with open('LICENSE') as f:
    license = f.read()

setup(
    name='coroutime',
    version='0.2.0',
    description='A package for timing Tornado coroutines',
    long_description='',
    author_email='coroutime@gmail.com',
    url='https://github.com/coroutime/coroutime',
    license=license,
    packages=find_packages(exclude=('tests', 'docs'))
)
