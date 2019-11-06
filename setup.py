from setuptools import setup, find_packages

setup(
    name="offline-trans",
    version="0.0.2",
    description="transport docker iamges fast by only contain diff layers",
    install_requires=[
        'Click',
    ],
    packages=find_packages(include=['offline_trans']),
    entry_points='''
        [console_scripts]
        offline_trans=offline_trans.cli:cli
    '''
)