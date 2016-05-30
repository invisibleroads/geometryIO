# -*- coding: utf-8 -*-
from geometryIO import (
    GeometryError, save, save_points, load, load_points,
    get_coordinateTransformation, get_geometryType, get_spatialReference,
    get_transformPoint, get_transformGeometry, proj4LL, proj4SM)
from osgeo.ogr import CreateGeometryFromWkt, OFTString, OFTInteger, OFTReal, OFTDate, wkbPolygon
from shapely.geometry import Polygon, Point
import os
import datetime
import shutil
import tempfile
import unittest


sourceGeometries = [
    Polygon([(0, 0), (0, 10), (10, 10), (10, 0), (0, 0)]),
]
fieldPacks = [
    ('xxx', 11111, 44444.44),
]
fieldDefinitions = [
    ('Name', OFTString),
    ('Population', OFTInteger),
    ('GDP', OFTReal),
]


class TestGeometryIO(unittest.TestCase):

    def test_save_and_load_work(self):
        path = self.get_path('.shp.zip')
        save(path, proj4LL, sourceGeometries)
        targetProj4, targetGeometries = load(path)[:2]
        self.assert_('+proj=longlat' in targetProj4)
        for sourceGeometry, targetGeometry in zip(sourceGeometries, targetGeometries):
            self.assert_(sourceGeometry.equals(targetGeometry))

    def test_save_and_load_attributes_work(self):
        fieldPacks = [(
            # 'Спасибо'.decode('utf-8'),
            datetime.datetime(2000, 1, 1),
        )]
        fieldDefinitions = [
            # ('String', OFTString),
            ('Date', OFTDate),
        ]
        path = self.get_path()
        save(path, proj4LL, sourceGeometries, fieldPacks, fieldDefinitions)
        for sourceField, targetField in zip(fieldPacks[0], load(path)[2][0]):
            self.assertEqual(sourceField, targetField)

    def test_save_and_load_points_work(self):
        path = self.get_path('.shp.tar.gz')
        save_points(path, proj4LL, [(0, 0)], fieldPacks, fieldDefinitions)
        self.assertEqual(load_points(path)[1], [(0, 0)])

    def test_save_with_targetProj4_works(self):
        path = self.get_path()
        save(path, proj4LL, sourceGeometries, targetProj4=proj4SM)
        self.assert_('+proj=longlat' not in load(path)[0])

    def test_load_with_targetProj4_works(self):
        path = self.get_path()
        save(path, proj4LL, sourceGeometries)
        self.assert_('+proj=longlat' not in load(path, targetProj4=proj4SM)[0])

    def test_save_overwrites_existing_targetPath(self):
        path = self.get_path()
        for x in range(2):
            save(path, proj4LL, sourceGeometries)

    def test_save_raises_exceptions(self):
        path = self.get_path()
        # A geometry has fewer attributes than are actually defined
        with self.assertRaises(GeometryError):
            save(path, proj4LL, sourceGeometries, [x[1:] for x in fieldPacks], fieldDefinitions)
        # A geometry has more attributes than are actually defined
        with self.assertRaises(GeometryError):
            save(path, proj4LL, sourceGeometries, [x * 2 for x in fieldPacks], fieldDefinitions)
        # The driverName is unrecognized
        with self.assertRaises(GeometryError):
            save(path, proj4LL, sourceGeometries, driverName='')

    def test_load_raises_exceptions(self):
        # The format is unrecognized
        path = self.get_path('')
        with self.assertRaises(GeometryError):
            load(path)

    def test_get_coordinateTransformation_runs(self):
        get_coordinateTransformation(proj4LL, proj4SM)

    def test_get_geometryType(self):
        self.assertEqual(get_geometryType(sourceGeometries), wkbPolygon)

    def test_get_spatialReference_runs(self):
        get_spatialReference(proj4LL)
        with self.assertRaises(GeometryError):
            get_spatialReference('')

    def test_get_transformGeometry_runs(self):
        transformGeometry = get_transformGeometry(proj4LL, proj4SM)
        self.assertEqual(type(transformGeometry(Point(0, 0))), type(Point(0, 0)))
        self.assertEqual(type(transformGeometry(CreateGeometryFromWkt('POINT (0 0)'))), type(CreateGeometryFromWkt('POINT (0 0)')))
        with self.assertRaises(GeometryError):
            transformGeometry(Point(1000, 1000))

    def test_get_transformPoint_runs(self):
        transformPoint0 = get_transformPoint(proj4LL, proj4LL)
        transformPoint1 = get_transformPoint(proj4LL, proj4SM)
        self.assertNotEqual(transformPoint0(0, 0), transformPoint1(0, 0))

    def get_path(self, fileExtension='.shp'):
        'Return a temporaryFolder path with the given fileExtension'
        self.pathIndex += 1
        return os.path.join(self.temporaryFolder, str(self.pathIndex) + fileExtension)

    def setUp(self):
        self.temporaryFolder = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temporaryFolder)

    pathIndex = 0
