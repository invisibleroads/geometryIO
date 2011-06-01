'Tests for geometryIO'
import os
import shutil
import itertools
import tempfile
import unittest
from osgeo import ogr
from shapely import geometry

import geometryIO


shapelyGeometries = [
    geometry.Polygon([(0, 0), (0, 10), (10, 10), (10, 0), (0, 0)]),
    geometry.Polygon([(10, 0), (10, 10), (20, 10), (20, 0), (10, 0)]),
]
fieldPacks = [
    ('xxx', 11111, 44444.44),
    ('yyy', 22222, 88888.88),
]
fieldDefinitions = [
    ('Name', ogr.OFTString),
    ('Population', ogr.OFTInteger),
    ('GDP', ogr.OFTReal),
]


class TestGeometryIO(unittest.TestCase):
    'Demonstrate usage'

    index = 0

    def setUp(self):
        self.temporaryFolder = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temporaryFolder)

    def getPath(self, fileExtension):
        'Return a path with the given fileExtension in temporaryFolder'
        self.index += 1
        return os.path.join(self.temporaryFolder, str(self.index) + fileExtension)

    def test(self):
        'Run tests'

        print 'Save and load a shapefile without attributes'
        path = self.getPath('.shp')
        geometryIO.save(path, geometryIO.proj4LL, shapelyGeometries)
        result = geometryIO.load(path)
        self.assert_('+proj=longlat' in result[0])
        self.assertEqual(len(result[1]), len(shapelyGeometries))

        print 'Overwrite an existing compressed shapefile'
        geometryIO.save(path, geometryIO.proj4LL, shapelyGeometries)

        print 'Save and load a shapefile with attributes'
        path = self.getPath('.shp')
        geometryIO.save(path, geometryIO.proj4LL, shapelyGeometries, fieldPacks, fieldDefinitions)
        result = geometryIO.load(path)
        self.assertEqual(len(result[2]), len(fieldPacks))
        for shapelyGeometry, fieldPack in itertools.izip(result[1], result[2]):
            print
            for fieldValue, (fieldName, fieldType) in itertools.izip(fieldPack, result[3]):
                print '%s = %s' % (fieldName, fieldValue)
            print shapelyGeometry

        print 'Save a shapefile with attributes with different targetProj4'
        path = self.getPath('.shp')
        geometryIO.save(path, geometryIO.proj4LL, shapelyGeometries, fieldPacks, fieldDefinitions, targetProj4=geometryIO.proj4SM)
        result = geometryIO.load(path)
        self.assert_('+proj=longlat' not in result[0])

        print 'Load a shapefile with attributes with different targetProj4'
        path = self.getPath('.shp')
        geometryIO.save(path, geometryIO.proj4LL, shapelyGeometries, fieldPacks, fieldDefinitions)
        result = geometryIO.load(path, targetProj4=geometryIO.proj4SM)
        self.assert_('+proj=longlat' not in result[0])

        print 'Save and load a compressed shapefile without attributes using save'
        path = self.getPath('.shp.zip')
        geometryIO.save(path, geometryIO.proj4LL, shapelyGeometries)
        result = geometryIO.load(path)
        self.assert_('+proj=longlat' in result[0])
        self.assertEqual(len(result[1]), len(shapelyGeometries))

        print 'Save and load a compressed shapefile with attributes using save'
        path = self.getPath('.shp.zip')
        geometryIO.save(path, geometryIO.proj4LL, shapelyGeometries, fieldPacks, fieldDefinitions)
        result = geometryIO.load(path)
        self.assertEqual(len(result[2]), len(fieldPacks))

        print 'Test saving and loading compressed shapefiles of point coordinates'
        path = self.getPath('.shp.tar.gz')
        geometryIO.save_points(path, geometryIO.proj4LL, [(0, 0)], fieldPacks, fieldDefinitions)
        result = geometryIO.load_points(path)
        self.assertEqual(result[1], [(0, 0)])

        print 'Test get_transformPoint'
        transformPoint0 = geometryIO.get_transformPoint(geometryIO.proj4LL, geometryIO.proj4LL)
        transformPoint1 = geometryIO.get_transformPoint(geometryIO.proj4LL, geometryIO.proj4SM)
        self.assertNotEqual(transformPoint0(0, 0), transformPoint1(0, 0))

        print 'Test get_transformGeometry'
        transformGeometry = geometryIO.get_transformGeometry(geometryIO.proj4LL, geometryIO.proj4SM)
        self.assertEqual(type(transformGeometry(geometry.Point(0, 0))), type(geometry.Point(0, 0)))
        self.assertEqual(type(transformGeometry(ogr.CreateGeometryFromWkt('POINT (0 0)'))), type(ogr.CreateGeometryFromWkt('POINT (0 0)')))
        with self.assertRaises(geometryIO.GeometryError):
            transformGeometry(geometry.Point(1000, 1000))

        print 'Test get_coordinateTransformation'
        geometryIO.get_coordinateTransformation(geometryIO.proj4LL, geometryIO.proj4SM)

        print 'Test get_spatialReference'
        geometryIO.get_spatialReference(geometryIO.proj4LL)
        with self.assertRaises(geometryIO.GeometryError):
            geometryIO.get_spatialReference('')

        print 'Test get_geometryType'
        geometryIO.get_geometryType(shapelyGeometries)

        print 'Test save() when a fieldPack has fewer fields than definitions'
        with self.assertRaises(geometryIO.GeometryError):
            path = self.getPath('.shp')
            geometryIO.save(path, geometryIO.proj4LL, shapelyGeometries, [x[1:] for x in fieldPacks], fieldDefinitions)

        print 'Test save() when a fieldPack has more fields than definitions'
        with self.assertRaises(geometryIO.GeometryError):
            path = self.getPath('.shp')
            geometryIO.save(path, geometryIO.proj4LL, shapelyGeometries, [x * 2 for x in fieldPacks], fieldDefinitions)

        print 'Test save() when the driverName is unrecognized'
        with self.assertRaises(geometryIO.GeometryError):
            path = self.getPath('.shp')
            geometryIO.save(path, geometryIO.proj4LL, shapelyGeometries, driverName='')

        print 'Test load() when format is unrecognized'
        with self.assertRaises(geometryIO.GeometryError):
            path = self.getPath('')
            geometryIO.load(path)
