from distutils.core import setup
setup(
   name='my-archiver',
   version='0.1',
   packages=[
    'sys',
    'os',
    'io',
    're',
    'argparse',
    'getopt',
    'subprocess',
    'requests',
    'urllib',
    'pathlib',
    'json',
    'csv',
    'bs4',
    'PIL',
    'shutil',
    'tqdm',
    ],
   license='MIT',
   long_description=open('README.txt').read(),
)