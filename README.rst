geometryIO
==========
Here is a GDAL wrapper for reading and writing geospatial data to a variety of vector formats.  For a list of supported vector formats and driver names, please see http://www.gdal.org/ogr/ogr_formats.html
 

Installation
------------
You may need to install the geospatial dependencies separately.
::

    yum -y install gdal-devel geos-devel proj-devel

Install the package.
::

    easy_install -U geometryIO


Usage
-----
::

    import geometryIO
    import itertools
    import datetime
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
                datetime.date(1939, 9, 1),
            ), (
                'yyy', 
                22222, 
                88888.88, 
                datetime.date(1950, 6, 25),
            ),
        ],
        # Define attributes
        fieldDefinitions=[
            ('Name', ogr.OFTString),
            ('Population', ogr.OFTInteger),
            ('GDP', ogr.OFTReal),
            ('Updated', ogr.OFTDate),
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
    for shapelyGeometry, fieldPack in itertools.izip(shapelyGeometries, fieldPacks):
        print
        for fieldValue, (fieldName, fieldType) in itertools.izip(fieldPack, fieldDefinitions):
            print '%s = %s' % (fieldName, fieldValue)
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
