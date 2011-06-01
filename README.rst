geometryIO
==========
Here is a GDAL wrapper for reading and writing geospatial data to a variety of vector formats.  For a list of supported vector formats and driver names, please see http://www.gdal.org/ogr/ogr_formats.html
 

Installation
------------
Here are instructions for installing ``geometryIO`` in a `virtualenv <http://www.virtualenv.org>`_
::

    # Prepare isolated environment
    ENV=$HOME/Projects/env
    virtualenv --no-site-packages $ENV 
    # Activate isolated environment
    source $ENV/bin/activate
    # Install GDAL
    wget http://download.osgeo.org/gdal/gdal-1.8.0.tar.gz
    tar xzvf gdal-1.8.0.tar.gz
    cd gdal-1.8.0
    ./configure --prefix=$ENV --with-python
    make install
    # Install package
    export LD_LIBRARY_PATH=$ENV/lib:$LD_LIBRARY_PATH
    easy_install -U geometryIO


Usage
-----
Prepare environment
::

    ENV=$HOME/Projects/env
    source $ENV/bin/activate
    export LD_LIBRARY_PATH=$ENV/lib:$LD_LIBRARY_PATH
    ipython

Run code
::

    import geometryIO
    import itertools
    from osgeo import ogr
    from shapely import geometry

    geometryIO.save(
        # Save to a compressed shapefile
        targetPath='polygons.shp.zip',
        # Declare that source coordinates are in longitude and latitude
        sourceProj4=geometryIO.proj4LL,
        # Specify geometries using shapely
        shapelyGeometries=[
            geometry.Polygon([(0, 0), (0, 10), (10, 10), (10, 0), (0, 0)]),
            geometry.Polygon([(10, 0), (10, 10), (20, 10), (20, 0), (10, 0)]),
        ],
        # Specify attributes for each geometry
        fieldPacks=[
            (
                'xxx', 
                11111, 
                44444.44, 
            ), (
                'yyy', 
                22222, 
                88888.88, 
            ),
        ],
        # Define attributes
        fieldDefinitions=[
            ('Name', ogr.OFTString),
            ('Population', ogr.OFTInteger),
            ('GDP', ogr.OFTReal),
        ],
        # Specify desired vector format
        driverName='ESRI Shapefile', 
        # Transform coordinates to spherical mercator
        targetProj4=geometryIO.proj4SM)

    proj4, shapelyGeometries, fieldPacks, fieldDefinitions = geometryIO.load(
        # Load from a compressed shapefile
        sourcePath='polygons.shp.zip', 
        # Transform coordinates to longitude and latitude
        targetProj4=geometryIO.proj4LL)
    for shapelyGeometry, fPack in itertools.izip(shapelyGeometries, fieldPacks):
        print
        for fValue, (fName, fType) in itertools.izip(fPack, fieldDefinitions):
            print '%s = %s' % (fName, fValue)
        print shapelyGeometry

    geometryIO.save_points(
        # Save to a compressed shapefile
        targetPath='points.shp.tar.gz',
        # Declare that source coordinates are in longitude and latitude
        sourceProj4=geometryIO.proj4LL,
        # Specify coordinates
        coordinateTuples=[
            (0, +1),
            (+1, 0),
            (0, -1),
            (-1, 0),
        ])
    print geometryIO.load_points('points.shp.tar.gz')[1]
