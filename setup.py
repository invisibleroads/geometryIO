import os

from setuptools import setup, find_packages


here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.rst')).read()
CHANGES = open(os.path.join(here, 'CHANGES.rst')).read()


setup(
    name='geometryIO',
    version='0.9.7',
    description='GDAL wrapper for reading and writing geospatial data to a variety of vector formats',
    long_description=README + '\n\n' +  CHANGES,
    license='MIT',
    classifiers=[
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'License :: OSI Approved :: MIT License',
    ],
    keywords='gdal shapely shapefile',
    author='Roy Hyunjin Han',
    author_email='rhh@crosscompute.com',
    url='https://github.com/invisibleroads/geometryIO',
    install_requires=[
        'archiveIO',
        # 'GDAL',
        # 'shapely',
    ],
    packages=find_packages(),
    include_package_data=True,
    test_suite='geometryIO.tests',
    tests_require=['nose'],
    zip_safe=True)
