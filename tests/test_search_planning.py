import json
import unittest

from ai_mechanic.search_planning import parse_search_plan


class SearchPlanningTests(unittest.TestCase):
    def test_vehicle_context_is_not_embedded(self):
        plan = json.dumps({
            'vehicle_context': 'RAV4 2012 ZDX925 2WD',
            'tasks': [{'component': 'alternator', 'operation': 'mounting bolt torque'}],
        })
        self.assertEqual(parse_search_plan(plan, 'original'), ['generator mounting bolt torque'])

    def test_multiple_tasks_keep_distinct_searches(self):
        plan = json.dumps({'tasks': [
            {'component': 'roof lining', 'operation': 'removal'},
            {'component': 'alternator', 'operation': 'installation'},
        ]})
        self.assertEqual(parse_search_plan(plan, 'original'),
                         ['headlining removal', 'generator installation'])

    def test_empty_plan_falls_back(self):
        self.assertEqual(parse_search_plan('{"tasks":[]}', 'original'), ['original'])

    def test_malformed_plan_rejected(self):
        with self.assertRaises(ValueError):
            parse_search_plan('[]', 'original')
