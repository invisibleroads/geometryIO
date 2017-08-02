"""
GDAL wrapper for reading and writing geospatial data
to a variety of vector formats.

For a list of supported vector formats and driver names,
please see http://www.gdal.org/ogr/ogr_formats.html
"""
import archiveIO
import datetime
import os
import sys
from osgeo import gdal, ogr, osr
from shapely import wkb, geometry


def get_proj4(epsg):
    'Return proj4 from epsg'
    spatial_reference = osr.SpatialReference()
    spatial_reference.ImportFromEPSG(epsg)
    return spatial_reference.ExportToProj4()


proj4LL = get_proj4(4326)
proj4SM = get_proj4(3857)


@archiveIO.save
def save(
        targetPath, sourceProj4, shapelyGeometries, fieldPacks=None,
        fieldDefinitions=None, driverName='ESRI Shapefile', targetProj4=''):
    'Save shapelyGeometries with targetProj4, fieldPacks, fieldDefinitions'
    # Validate arguments
    if not fieldPacks:
        fieldPacks = []
    if not fieldDefinitions:
        fieldDefinitions = []
    if fieldPacks and set(len(x) for x in fieldPacks) != set([len(
            fieldDefinitions)]):
        raise GeometryError('A field definition is required for each field')
    # Make dataSource
    if os.path.exists(targetPath):
        os.remove(targetPath)
    dataDriver = ogr.GetDriverByName(driverName)
    if not dataDriver:
        raise GeometryError('Could not load driver "%s"' % driverName)
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
    for shapelyGeometry, fieldPack in zip(
        shapelyGeometries, fieldPacks
    ) if fieldPacks else ((x, []) for x in shapelyGeometries):
        # Prepare
        feature = ogr.Feature(featureDefinition)
        feature.SetGeometry(transformGeometry(ogr.CreateGeometryFromWkb(
            shapelyGeometry.wkb)))
        for fieldIndex, fieldValue in enumerate(fieldPack):
            feature.SetField2(fieldIndex, fieldValue)
        # Save
        layer.CreateFeature(feature)
    # Return
    return targetPath


def save_points(
        targetPath, sourceProj4, coordinateTuples, fieldPacks=None,
        fieldDefinitions=None, driverName='ESRI Shapefile', targetProj4=''):
    'Save points with targetProj4, fieldPacks, fieldDefinitions'
    return save(targetPath, sourceProj4, [
        geometry.Point(x) for x in coordinateTuples
    ], fieldPacks, fieldDefinitions, driverName, targetProj4)


@archiveIO.load(extensions=['.shp'])
def load(sourcePath, sourceProj4='', targetProj4=''):
    'Load proj4, shapelyGeometries, fieldPacks, fieldDefinitions'
    # Get layer
    try:
        dataSource = ogr.Open(sourcePath)
    except RuntimeError:
        raise GeometryError(
            'Could not open source "%s"' % os.path.basename(sourcePath))
    if not dataSource:
        raise GeometryError(
            'Could not load source "%s"' % os.path.basename(sourcePath))
    layer = dataSource.GetLayer()
    # Get fieldDefinitions from featureDefinition
    featureDefinition = layer.GetLayerDefn()
    fieldIndices = range(featureDefinition.GetFieldCount())
    fieldDefinitions = []
    fieldTypes = []
    for fieldIndex in fieldIndices:
        fieldDefinition = featureDefinition.GetFieldDefn(fieldIndex)
        fieldType = fieldDefinition.GetType()
        fieldTypes.append(fieldType)
        fieldDefinitions.append((fieldDefinition.GetName(), fieldType))
    # Get spatialReference
    spatialReference = layer.GetSpatialRef()
    sourceProj4 = spatialReference.ExportToProj4() if spatialReference else '' or sourceProj4
    # Load shapelyGeometries and fieldPacks
    shapelyGeometries, fieldPacks = [], []
    methodNameByType = {
        ogr.OFTDate: 'GetFieldAsDateTime',
        ogr.OFTDateTime: 'GetFieldAsDateTime',
        ogr.OFTInteger: 'GetFieldAsInteger',
        ogr.OFTIntegerList: 'GetFieldAsIntegerList',
        ogr.OFTReal: 'GetFieldAsDouble',
        ogr.OFTRealList: 'GetFieldAsDoubleList',
        ogr.OFTString: 'GetFieldAsString',
        ogr.OFTStringList: 'GetFieldAsStringList',
        ogr.OFTWideString: 'GetFieldAsString',
        ogr.OFTWideStringList: 'GetFieldAsStringList',
    }

    def get_fieldPack(f):
        fieldPack = []
        for fieldIndex, fieldType in zip(fieldIndices, fieldTypes):
            try:
                methodName = methodNameByType[fieldType]
            except KeyError:
                methodName = 'GetField'
            fieldValue = getattr(f, methodName)(fieldIndex)
            if fieldType in (ogr.OFTDate, ogr.OFTDateTime):
                try:
                    fieldValue = datetime.datetime(*map(int, fieldValue))
                except ValueError:
                    fieldValue = None
            elif fieldType in (ogr.OFTString, ogr.OFTWideString):
                fieldValue = unicode_safely(fieldValue)
            elif fieldType in (ogr.OFTStringList, ogr.OFTWideStringList):
                fieldValue = [unicode_safely(x) for x in fieldValue]
            fieldPack.append(fieldValue)
        return tuple(fieldPack)
    transformGeometry = get_transformGeometry(sourceProj4, targetProj4)
    feature = layer.GetNextFeature()
    while feature:
        gdal_geometry = feature.GetGeometryRef()
        if gdal_geometry:
            shapelyGeometries.append(wkb.loads(transformGeometry(
                gdal_geometry).ExportToWkb()))
            fieldPacks.append(get_fieldPack(feature))
        # Get the next feature
        feature = layer.GetNextFeature()
    # Return
    return targetProj4 or sourceProj4, shapelyGeometries, fieldPacks, fieldDefinitions


def load_points(sourcePath, sourceProj4='', targetProj4=''):
    'Load proj4, points, fieldPacks, fieldDefinitions'
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
    coordinateTransformation = get_coordinateTransformation(
        sourceProj4, targetProj4)

    def transformGeometry(g):
        'Transform a shapelyGeometry or gdalGeometry using coordinateTransformation'
        # Test for shapelyGeometry
        isShapely = isinstance(g, geometry.base.BaseGeometry)
        # If we have a shapelyGeometry, convert it to a gdalGeometry
        if isShapely:
            g = ogr.CreateGeometryFromWkb(g.wkb)
        try:
            g.Transform(coordinateTransformation)
        except RuntimeError as error:
            gdal.ErrorReset()
            raise GeometryError('Could not transform wkt "%s" (%s)' % (g.ExportToWkt(), error))
        # If we originally had a shapelyGeometry, convert it back
        if isShapely:
            g = wkb.loads(g.ExportToWkb())
        # Return
        return g
    # Return
    return transformGeometry


def get_coordinateTransformation(sourceProj4, targetProj4=proj4LL):
    'Return a CoordinateTransformation that can be used with gdalGeometry.transform()'
    source_srs = get_spatialReference(sourceProj4)
    target_srs = get_spatialReference(targetProj4)
    return osr.CoordinateTransformation(source_srs, target_srs)


def get_spatialReference(proj4):
    'Return SpatialReference from proj4'
    spatialReference = osr.SpatialReference()
    try:
        spatialReference.ImportFromProj4(proj4)
    except RuntimeError:
        raise SpatialReferenceError('Could not import proj4 "%s"' % proj4)
    return spatialReference


def get_geometryType(shapelyGeometries):
    'Determine geometry type for layer'
    geometryTypes = list(set(type(x) for x in shapelyGeometries))
    return ogr.wkbUnknown if not geometryTypes or len(geometryTypes) > 1 else {
        geometry.Point: ogr.wkbPoint,
        geometry.point.PointAdapter: ogr.wkbPoint,
        geometry.LineString: ogr.wkbLineString,
        geometry.linestring.LineStringAdapter: ogr.wkbLineString,
        geometry.Polygon: ogr.wkbPolygon,
        geometry.polygon.PolygonAdapter: ogr.wkbPolygon,
        geometry.MultiPoint: ogr.wkbMultiPoint,
        geometry.multipoint.MultiPointAdapter: ogr.wkbMultiPoint,
        geometry.MultiLineString: ogr.wkbMultiLineString,
        geometry.multilinestring.MultiLineStringAdapter:
            ogr.wkbMultiLineString,
        geometry.MultiPolygon: ogr.wkbMultiPolygon,
        geometry.multipolygon.MultiPolygonAdapter: ogr.wkbMultiPolygon,
    }[geometryTypes[0]]


def unicode_safely(x):
    # http://stackoverflow.com/a/23085282/192092
    if not hasattr(x, 'decode'):
        return x
    return x.decode(sys.getfilesystemencoding())


class GeometryError(Exception):
    'Exception raised when there is an error loading or saving geometries'
    pass


class SpatialReferenceError(GeometryError):
    pass


gdal.UseExceptions()
ogr.UseExceptions()
osr.UseExceptions()
