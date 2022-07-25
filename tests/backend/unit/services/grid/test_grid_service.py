import json
import geojson

from backend.models.dtos.grid_dto import GridDTO
from backend.models.dtos.project_dto import DraftProjectDTO
from backend.models.postgis.utils import InvalidGeoJson
from backend.services.grid.grid_service import GridService
from tests.backend.base import BaseTestCase
from tests.backend.helpers.test_helpers import get_canned_json
import re


class TestGridService(BaseTestCase):
    def test_feature_collection_to_multi_polygon_dissolve(self):
        # arrange
        grid_json = get_canned_json("test_grid.json")
        grid_dto = GridDTO(grid_json)
        aoi_geojson = geojson.loads(json.dumps(grid_dto.area_of_interest))
        expected = geojson.loads(
            json.dumps(get_canned_json("multi_polygon_dissolved.json"))
        )

        # act
        result = GridService.merge_to_multi_polygon(aoi_geojson, True)

        # assert coordinates are same. Done separately due to floating point rounding
        for expected_coords, result_coords in zip(
            expected["coordinates"][0][0], result["coordinates"][0][0]
        ):
            self.assertAlmostEqual(expected_coords[0], result_coords[0])
            self.assertAlmostEqual(expected_coords[1], result_coords[1])

        # assert everything besides floating points are the same
        split_expected = re.split(r"\[\[\[\[.*?]]]]", str(expected))
        split_result = re.split(r"\[\[\[\[.*?]]]]", str(result))
        self.assertEqual(split_expected, split_result)

    def test_feature_collection_to_multi_polygon_nodissolve(self):
        # arrange
        grid_json = get_canned_json("test_grid.json")
        grid_dto = GridDTO(grid_json)
        expected = geojson.loads(json.dumps(get_canned_json("multi_polygon.json")))
        aoi_geojson = geojson.loads(json.dumps(grid_dto.area_of_interest))

        # act
        result = GridService.merge_to_multi_polygon(aoi_geojson, False)

        # assert coordinates are same. Done separately due to floating point rounding
        for expected_coords, result_coords in zip(
            expected["coordinates"][0][0], result["coordinates"][0][0]
        ):
            self.assertAlmostEqual(expected_coords[0], result_coords[0])
            self.assertAlmostEqual(expected_coords[1], result_coords[1])

        # assert everything besides floating points are the same
        split_expected = re.split(r"\[\[\[\[.*?]]]]", str(expected))
        split_result = re.split(r"\[\[\[\[.*?]]]]", str(result))
        self.assertEqual(split_expected, split_result)

    def test_trim_grid_to_aoi_clip(self):
        # arrange
        grid_json = get_canned_json("test_grid.json")

        grid_dto = GridDTO(grid_json)
        expected = geojson.loads(
            json.dumps(get_canned_json("clipped_feature_collection.json"))
        )
        grid_dto.clip_to_aoi = True

        # act
        result = GridService.trim_grid_to_aoi(grid_dto)

        # assert
        self.assertEqual(str(expected), str(result))

    def test_trim_grid_to_aoi_noclip(self):
        # arrange

        grid_json = get_canned_json("test_grid.json")
        grid_dto = GridDTO(grid_json)
        grid_dto.clip_to_aoi = False

        expected = geojson.loads(json.dumps(get_canned_json("feature_collection.json")))

        # act
        result = GridService.trim_grid_to_aoi(grid_dto)

        # assert
        self.assertEqual(str(expected), str(result))

    def test_tasks_from_aoi_features(self):
        # arrange
        grid_json = get_canned_json("test_arbitrary.json")
        grid_dto = GridDTO(grid_json)
        expected = geojson.loads(
            json.dumps(get_canned_json("tasks_from_aoi_features.json"))
        )

        # act
        result = GridService.tasks_from_aoi_features(grid_dto.area_of_interest)
        # assert
        self.assertEqual(str(expected), str(result))

    def test_feature_collection_multi_polygon_with_zcoord_nodissolve(self):
        # arrange
        project_json = get_canned_json("canned_kml_project.json")
        project_dto = DraftProjectDTO(project_json)
        expected = geojson.loads(json.dumps(get_canned_json("2d_multi_polygon.json")))
        aoi_geojson = geojson.loads(json.dumps(project_dto.area_of_interest))

        # act
        result = GridService.merge_to_multi_polygon(aoi_geojson, dissolve=False)

        # assert coordinates are same. Done separately due to floating point rounding
        for expected_coords, result_coords in zip(
            expected["coordinates"][0][0], result["coordinates"][0][0]
        ):
            self.assertAlmostEqual(expected_coords[0], result_coords[0])
            self.assertAlmostEqual(expected_coords[1], result_coords[1])

        # assert everything besides floating points are the same
        split_expected = re.split(r"\[\[\[\[.*?]]]]", str(expected))
        split_result = re.split(r"\[\[\[\[.*?]]]]", str(result))
        self.assertEqual(split_expected, split_result)

    def test_feature_collection_multi_polygon_with_zcoord_dissolve(self):
        # arrange
        project_json = get_canned_json("canned_kml_project.json")
        project_dto = DraftProjectDTO(project_json)
        expected = geojson.loads(json.dumps(get_canned_json("2d_multi_polygon.json")))
        aoi_geojson = geojson.loads(json.dumps(project_dto.area_of_interest))

        # act
        result = GridService.merge_to_multi_polygon(aoi_geojson, dissolve=True)

        # assert coordinates are same. Done separately due to floating point rounding
        for expected_coords, result_coords in zip(
            expected["coordinates"][0][0], result["coordinates"][0][0]
        ):
            self.assertAlmostEqual(expected_coords[0], result_coords[0])
            self.assertAlmostEqual(expected_coords[1], result_coords[1])

        # assert everything besides floating points are the same
        split_expected = re.split(r"\[\[\[\[.*?]]]]", str(expected))
        split_result = re.split(r"\[\[\[\[.*?]]]]", str(result))
        self.assertEqual(split_expected, split_result)

    def test_raises_InvalidGeoJson_when_geometry_is_linestring(self):

        # arrange
        grid_json = get_canned_json("CHAI-Escuintla-West2.json")
        grid_dto = GridDTO(grid_json)
        grid_dto.clip_to_aoi = True

        # Act / Assert
        with self.assertRaises(InvalidGeoJson):
            GridService.merge_to_multi_polygon(grid_dto.area_of_interest, dissolve=True)

    def test_cant_create_aoi_with_non_multipolygon_type(self):
        # Arrange
        bad_geom = geojson.Polygon(
            [[(2.38, 57.322), (23.194, -20.28), (-120.43, 19.15), (2.38, 57.322)]]
        )
        bad_feature = geojson.Feature(geometry=bad_geom)
        # bad_feature_collection = geojson.FeatureCollection([bad_feature])

        # Act / Assert
        with self.assertRaises(InvalidGeoJson):
            # Only geometries of type MultiPolygon are valid
            GridService.merge_to_multi_polygon(
                geojson.dumps(bad_feature), dissolve=True
            )

    def test_cant_create_aoi_with_invalid_multipolygon(self):
        bad_multipolygon = geojson.MultiPolygon(
            [[(2.38, 57.322), (23.194, -20.28), (-120.43, 19.15), (2.38)]]
        )
        bad_feature = geojson.Feature(geometry=bad_multipolygon)
        bad_feature_collection = geojson.FeatureCollection([bad_feature])

        # Act / Assert
        with self.assertRaises(InvalidGeoJson):
            # Only geometries of type MultiPolygon are valid
            GridService.merge_to_multi_polygon(
                geojson.dumps(bad_feature_collection), dissolve=True
            )

    # def trim_grid_to_roads(self): # TODO
    #     # arrange
    #     grid_json = get_canned_json("test_trim_road.json")

    #     grid_dto = GridDTO(grid_json)
    #     expected = geojson.loads(
    #         json.dumps(get_canned_json("clipped_feature_collection.json"))
    #     )
    #     grid_dto.clip_to_aoi = False

    #     # act
    #     result = GridService.trim_grid_to_roads(grid_dto)
    #     # assert
    #     self.assertEqual(str(expected), str(result))

    def test_tile_to_bbox(self):
        x, y, z = 34789738, 23734005, 26
        expected = {
            "west": 6.626697778701782,
            "south": 46.522057511538904,
            "east": 6.626703143119812,
            "north": 46.52206120266217,
        }
        result = GridService._tile_to_bbox(x, y, z)
        for expected_float, result_float in zip(expected, result):
            self.assertAlmostEqual(expected_float, result_float)

    def test_task_grid_road_imagery_completeness(self):
        # arrange
        grid_json = get_canned_json("test_trim_road.json")

        grid_dto = GridDTO(grid_json)
        expected = geojson.loads(
            json.dumps(get_canned_json("road_imagery_completion.json"))
        )
        grid_dto.clip_to_aoi = False

        # act
        roads = GridService.trim_grid_to_roads(grid_dto)
        result = GridService._task_grid_road_imagery_completeness(roads)

        # assert coordinates are same. Done separately due to floating point rounding
        for expected_coords, result_coords in zip(
            expected["roads_with_images"][0]["geometry"]["coordinates"][0],
            result["roads_with_images"][0]["geometry"]["coordinates"][0],
        ):
            self.assertAlmostEqual(expected_coords[0], result_coords[0])
            self.assertAlmostEqual(expected_coords[1], result_coords[1])

        # assert everything besides floating points are the same TODO
        # split_expected = re.split(r"\[\[\[.*?]]]", str(expected))
        # split_result = re.split(r"\[\[\[.*?]]]", str(result))
        # self.assertEqual(split_expected, split_result)
