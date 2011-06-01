"""
GDAL wrapper for reading and writing geospatial data 
to a variety of vector formats.

For a list of supported vector formats and driver names,
please see http://www.gdal.org/ogr/ogr_formats.html
"""
import os
import itertools
import archiveIO
from osgeo import gdal, ogr, osr
from shapely import wkb, geometry


proj4LL = '+proj=longlat +datum=WGS84 +no_defs'
proj4SM = '+proj=merc +lon_0=0 +lat_ts=0 +x_0=0 +y_0=0 +a=6378137 +b=6378137 +units=m +no_defs'


@archiveIO.save
def save(targetPath, sourceProj4, shapelyGeometries, fieldPacks=None, fieldDefinitions=None, driverName='ESRI Shapefile', targetProj4=''):
    'Save shapelyGeometries using the given proj4 and fields'
    # Validate arguments
    if not fieldPacks:
        fieldPacks = []
    if not fieldDefinitions:
        fieldDefinitions = []
    if fieldPacks and set(len(x) for x in fieldPacks) != set([len(fieldDefinitions)]):
        raise GeometryError('A field definition is required for each field')
    # Make dataSource
    if os.path.exists(targetPath): 
        os.remove(targetPath)
    dataDriver = ogr.GetDriverByName(driverName)
    if not dataDriver:
        raise GeometryError('Could not load driver: %s' % driverName)
    dataSource = dataDriver.CreateDataSource(targetPath)
    # Make layer
    layerName = os.path.splitext(os.path.basename(targetPath))[0]
    spatialReference = get_spatialReference(targetProj4 or sourceProj4)
    geometryType = get_geometryType(shapelyGeometries)
    layer = dataSource.CreateLayer(layerName, spatialReference, geometryType)
    # Make fieldDefinitions in featureDefinition
    for fieldName, fieldType in fieldDefinitions:
        layer.CreateField(ogr.FieldDefn(fieldName, fieldType))
    featureDefinition = layer.GetLayerDefn()
    # Save features
    transformGeometry = get_transformGeometry(sourceProj4, targetProj4)
    for shapelyGeometry, fieldPack in itertools.izip(shapelyGeometries, fieldPacks) if fieldPacks else ((x, []) for x in shapelyGeometries):
        # Prepare feature
        feature = ogr.Feature(featureDefinition)
        feature.SetGeometry(transformGeometry(ogr.CreateGeometryFromWkb(shapelyGeometry.wkb)))
        for fieldIndex, fieldValue in enumerate(fieldPack):
            feature.SetField(fieldIndex, fieldValue)
        # Save feature
        layer.CreateFeature(feature)
    # Return
    return targetPath


def save_points(targetPath, sourceProj4, coordinateTuples, fieldPacks=None, fieldDefinitions=None, driverName='ESRI Shapefile', targetProj4=''):
    'Save points using the given proj4 and fields'
    return save(targetPath, sourceProj4, [geometry.Point(x) for x in coordinateTuples], fieldPacks, fieldDefinitions, driverName, targetProj4)


@archiveIO.load
def load(sourcePath, sourceProj4='', targetProj4=''):
    'Load proj4, shapelyGeometries, fields'
    # Get layer
    dataSource = ogr.Open(sourcePath)
    if not dataSource:
        raise GeometryError('Could not load %s' % os.path.basename(sourcePath))
    layer = dataSource.GetLayer()
    # Get fieldDefinitions from featureDefinition
    featureDefinition = layer.GetLayerDefn()
    fieldIndices = xrange(featureDefinition.GetFieldCount())
    fieldDefinitions = []
    for fieldIndex in fieldIndices:
        fieldDefinition = featureDefinition.GetFieldDefn(fieldIndex)
        fieldDefinitions.append((fieldDefinition.GetName(), fieldDefinition.GetType()))
    # Get spatialReference
    spatialReference = layer.GetSpatialRef()
    sourceProj4 = spatialReference.ExportToProj4() if spatialReference else '' or sourceProj4
    # Load shapelyGeometries and fieldPacks
    shapelyGeometries, fieldPacks = [], []
    transformGeometry = get_transformGeometry(sourceProj4, targetProj4)
    feature = layer.GetNextFeature()
    while feature:
        # Append
        shapelyGeometries.append(wkb.loads(transformGeometry(feature.GetGeometryRef()).ExportToWkb()))
        fieldPacks.append([feature.GetField(x) for x in fieldIndices])
        # Get the next feature
        feature = layer.GetNextFeature()
    # Return
    return targetProj4 or sourceProj4, shapelyGeometries, fieldPacks, fieldDefinitions


def load_points(sourcePath, sourceProj4='', targetProj4=''):
    'Load proj4, points, fields'
    proj4, shapelyGeometries, fieldPacks, fieldDefinitions = load(sourcePath, sourceProj4, targetProj4)
    return proj4, [(point.x, point.y) for point in shapelyGeometries], fieldPacks, fieldDefinitions


def get_transformPoint(sourceProj4, targetProj4=proj4LL):
    'Return a function that transforms point coordinates from one spatial reference to another'
    if sourceProj4 == targetProj4:
        return lambda x, y: (x, y)
    coordinateTransformation = get_coordinateTransformation(sourceProj4, targetProj4)
    return lambda x, y: coordinateTransformation.TransformPoint(x, y)[:2]


def get_transformGeometry(sourceProj4, targetProj4=proj4LL):
    'Return a function that transforms a geometry from one spatial reference to another'
    if not targetProj4 or sourceProj4 == targetProj4:
        return lambda x: x
    coordinateTransformation = get_coordinateTransformation(sourceProj4, targetProj4)
    def transformGeometry(g):
        'Transform a shapelyGeometry or gdalGeometry using coordinateTransformation'
        # Test for shapelyGeometry
        isShapely = isinstance(g, geometry.base.BaseGeometry)
        # If we have a shapelyGeometry, convert it to a gdalGeometry
        if isShapely:
            g = ogr.CreateGeometryFromWkb(g.wkb)
        try:
            g.Transform(coordinateTransformation)
        except RuntimeError, error:
            gdal.ErrorReset()
            raise GeometryError('Could not transform %s: %s' % (g.ExportToWkt(), error))
        # If we originally had a shapelyGeometry, convert it back
        if isShapely:
            g = wkb.loads(g.ExportToWkb())
        # Return
        return g
    # Return
    return transformGeometry


def get_coordinateTransformation(sourceProj4, targetProj4=proj4LL):
    'Return a CoordinateTransformation that can be used with gdalGeometry.transform()'
    sourceSRS = get_spatialReference(sourceProj4)
    targetSRS = get_spatialReference(targetProj4)
    return osr.CoordinateTransformation(sourceSRS, targetSRS)


def get_spatialReference(proj4):
    'Return a SpatialReference from proj4'
    spatialReference = osr.SpatialReference()
    try:
        spatialReference.ImportFromProj4(proj4)
    except RuntimeError, error:
        raise GeometryError("Could not import proj4='%s'" % proj4)
    return spatialReference


def get_geometryType(shapelyGeometries):
    'Determine geometry type for layer'
    geometryTypes = list(set(type(x) for x in shapelyGeometries))
    return ogr.wkbUnknown if len(geometryTypes) > 1 else {
        geometry.Point: ogr.wkbPoint,
        geometry.point.PointAdapter: ogr.wkbPoint,
        geometry.LineString: ogr.wkbLineString,
        geometry.linestring.LineStringAdapter: ogr.wkbLineString,
        geometry.Polygon: ogr.wkbPolygon,
        geometry.polygon.PolygonAdapter: ogr.wkbPolygon,
        geometry.MultiPoint: ogr.wkbMultiPoint,
        geometry.multipoint.MultiPointAdapter: ogr.wkbMultiPoint,
        geometry.MultiLineString: ogr.wkbMultiLineString,
        geometry.multilinestring.MultiLineStringAdapter: ogr.wkbMultiLineString,
        geometry.MultiPolygon: ogr.wkbMultiPolygon,
        geometry.multipolygon.MultiPolygonAdapter: ogr.wkbMultiPolygon,
    }[geometryTypes[0]]


class GeometryError(Exception):
    'Exception raised when there is an error loading or saving geometries'
    pass


gdal.UseExceptions()
ogr.UseExceptions()
osr.UseExceptions()
