from datetime import date

from django.core.management import call_command
from django.test import TestCase

from nose.tools import assert_equal

from corehq.motech.models import ConnectionSettings

from ..const import (
    SEND_FREQUENCY_MONTHLY,
    SEND_FREQUENCY_QUARTERLY,
    SEND_FREQUENCY_WEEKLY,
)
from ..models import (
    DataSetMap,
    SQLDataSetMap,
    SQLDataValueMap,
    get_date_range,
    get_info_for_columns,
    get_period,
    get_previous_month,
    get_previous_quarter,
    get_previous_week,
    get_quarter_start_month,
    should_send_on_date,
    get_grouped_datavalues_sets,
    _group_data_by_keys,
)


def test_should_send_on_date():
    kwargs_day_result = [
        (
            {'frequency': SEND_FREQUENCY_WEEKLY, 'day_to_send': 5},
            date(2020, 9, 4),
            True,  # Friday Sep 4, 2020 is the 5th day of the week
        ),
        (
            {'frequency': SEND_FREQUENCY_WEEKLY, 'day_to_send': 5},
            date(2020, 9, 5),
            False,  # Saturday Sep 5, 2020 is not the 5th day of the week
        ),
        (
            {'frequency': SEND_FREQUENCY_MONTHLY, 'day_to_send': 5},
            date(2020, 9, 5),
            True,  # Sep 5 is the 5th day of the month
        ),
        (
            {'frequency': SEND_FREQUENCY_MONTHLY, 'day_to_send': 5},
            date(2020, 9, 4),
            False,  # Sep 4 is not the 5th day of the month
        ),
        (
            {'frequency': SEND_FREQUENCY_QUARTERLY, 'day_to_send': 5},
            date(2020, 7, 5),
            True,  # Jul 5 is the 5th day of the quarter
        ),
        (
            {'frequency': SEND_FREQUENCY_QUARTERLY, 'day_to_send': 5},
            date(2020, 9, 5),
            False,  # Sep 5 is not the 5th day of the quarter
        ),
    ]
    for kwargs, day, expected_result in kwargs_day_result:
        dataset_map = DataSetMap(**kwargs)
        result = should_send_on_date(dataset_map, day)
        assert_equal(result, expected_result)


def test_get_previous_week():
    day_start_end = [
        (date(2020, 9, 4), date(2020, 8, 24), date(2020, 8, 30)),  # Friday
        (date(2020, 9, 5), date(2020, 8, 24), date(2020, 8, 30)),  # Saturday
        (date(2020, 9, 6), date(2020, 8, 24), date(2020, 8, 30)),  # Sunday
        (date(2020, 9, 7), date(2020, 8, 31), date(2020, 9, 6)),  # Monday
    ]
    for day, expected_start, expected_end in day_start_end:
        date_span = get_previous_week(day)
        assert_equal(date_span.startdate, expected_start)
        assert_equal(date_span.enddate, expected_end)


def test_get_previous_month():
    day_start_end = [
        (date(2020, 1, 1), date(2019, 12, 1), date(2019, 12, 31)),
        (date(2020, 12, 31), date(2020, 11, 1), date(2020, 11, 30)),
        (date(2020, 7, 15), date(2020, 6, 1), date(2020, 6, 30)),
    ]
    for day, expected_start, expected_end in day_start_end:
        date_span = get_previous_month(day)
        assert_equal(date_span.startdate, expected_start)
        assert_equal(date_span.enddate, expected_end)


def test_get_previous_quarter():
    day_start_end = [
        (date(2020, 1, 1), date(2019, 10, 1), date(2019, 12, 31)),
        (date(2020, 3, 31), date(2019, 10, 1), date(2019, 12, 31)),
        (date(2020, 10, 1), date(2020, 7, 1), date(2020, 9, 30)),
        (date(2020, 12, 31), date(2020, 7, 1), date(2020, 9, 30)),
        (date(2020, 7, 15), date(2020, 4, 1), date(2020, 6, 30)),
    ]
    for day, expected_start, expected_end in day_start_end:
        date_span = get_previous_quarter(day)
        assert_equal(date_span.startdate, expected_start)
        assert_equal(date_span.enddate, expected_end)


def test_get_quarter_start_month():
    months = range(1, 13)
    start_months = (1, 1, 1, 4, 4, 4, 7, 7, 7, 10, 10, 10)
    for month, expected_month in zip(months, start_months):
        start_month = get_quarter_start_month(month)
        assert_equal(start_month, expected_month)


def test_get_period():
    freq_date_period = [
        (SEND_FREQUENCY_WEEKLY, date(2020, 1, 1), '2020W1'),  # Mon
        (SEND_FREQUENCY_WEEKLY, date(2020, 12, 31), '2020W53'),  # NYE
        (SEND_FREQUENCY_MONTHLY, date(2020, 1, 1), '202001'),  # Jan
        (SEND_FREQUENCY_QUARTERLY, date(2020, 1, 1), '2020Q1'),  # Jan
        (SEND_FREQUENCY_QUARTERLY, date(2020, 10, 1), '2020Q4'),  # Oct
    ]
    for frequency, startdate, expected_period in freq_date_period:
        period = get_period(frequency, startdate)
        assert_equal(period, expected_period)


def test_get_date_range():
    freq_date_startdate = [
        (SEND_FREQUENCY_WEEKLY, date(2021, 1, 1), date(2020, 12, 21)),
        (SEND_FREQUENCY_WEEKLY, date(2020, 12, 31), date(2020, 12, 21)),
        (SEND_FREQUENCY_QUARTERLY, date(2020, 1, 31), date(2019, 10, 1)),
        (SEND_FREQUENCY_QUARTERLY, date(2020, 3, 31), date(2019, 10, 1)),
        (SEND_FREQUENCY_QUARTERLY, date(2020, 10, 1), date(2020, 7, 1)),
    ]
    for frequency, send_date, expected_startdate in freq_date_startdate:
        date_range = get_date_range(frequency, send_date)
        assert_equal(date_range.startdate, expected_startdate)


def _remove_doc_types(dict_):
    """
    Removes "doc_type" keys from values in `dict_`
    """
    result = {}
    for key, value in dict_.items():
        value = value.copy()
        value.pop('doc_type', None)
        result[key] = value
    return result


class GetInfoForColumnsTests(TestCase):
    domain = 'test-domain'
    expected_couch_value = {
        'foo_bar': {
            'category_option_combo_id': 'bar456789ab',
            'column': 'foo_bar',
            'comment': None,
            'data_element_id': 'foo456789ab',
            'doc_type': 'DataValueMap',
            'is_org_unit': False,
            'is_period': False,
        },
        'foo_baz': {
            'category_option_combo_id': 'baz456789ab',
            'column': 'foo_baz',
            'comment': None,
            'data_element_id': 'foo456789ab',
            'doc_type': 'DataValueMap',
            'is_org_unit': False,
            'is_period': False,
        },
        'foo_qux': {
            'category_option_combo_id': 'qux456789ab',
            'column': 'foo_qux',
            'comment': None,
            'data_element_id': 'foo456789ab',
            'doc_type': 'DataValueMap',
            'is_org_unit': False,
            'is_period': False,
        },
        'org_unit_id': {
            'is_org_unit': True,
            'is_period': False,
        }
    }
    expected_sql_value = _remove_doc_types(expected_couch_value)

    def setUp(self):
        self.connection_settings = ConnectionSettings.objects.create(
            domain=self.domain,
            name='test connection',
            url='https://dhis2.example.com/'
        )
        self.dataset_map = DataSetMap.wrap({
            'domain': self.domain,
            'connection_settings_id': self.connection_settings.id,
            'ucr_id': 'c0ffee',
            'description': 'test dataset map',
            'frequency': SEND_FREQUENCY_MONTHLY,
            'day_to_send': 5,
            'org_unit_column': 'org_unit_id',
            'datavalue_maps': [{
                'column': 'foo_bar',
                'data_element_id': 'foo456789ab',
                'category_option_combo_id': 'bar456789ab',
            }, {
                'column': 'foo_baz',
                'data_element_id': 'foo456789ab',
                'category_option_combo_id': 'baz456789ab',
            }, {
                'column': 'foo_qux',
                'data_element_id': 'foo456789ab',
                'category_option_combo_id': 'qux456789ab',
            }]
        })
        self.dataset_map.save()
        call_command('populate_sqldatasetmap')
        self.sqldataset_map = SQLDataSetMap.objects.get(
            domain=self.domain,
            couch_id=self.dataset_map._id,
        )

    def tearDown(self):
        self.sqldataset_map.delete()
        self.dataset_map.delete()
        self.connection_settings.delete()

    def test_couch(self):
        info_for_columns = get_info_for_columns(self.dataset_map)
        self.assertEqual(info_for_columns, self.expected_couch_value)

    def test_sql(self):
        info_for_columns = get_info_for_columns(self.sqldataset_map)
        self.assertEqual(info_for_columns, self.expected_sql_value)


class TestDifferentDataSetMaps(TestCase):
    domain = 'test-domain'

    def setUp(self):
        self.map_1 = SQLDataSetMap.objects.create(
            domain=self.domain,
            ucr_id='c0ffee',
            day_to_send=1,
        )
        SQLDataValueMap.objects.create(
            dataset_map=self.map_1,
            column='foo',
            data_element_id='bar',
            comment='foo bar'
        )
        self.map_2 = SQLDataSetMap.objects.create(
            domain=self.domain,
            ucr_id='c0ffee',
            day_to_send=1,
        )
        SQLDataValueMap.objects.create(
            dataset_map=self.map_2,
            column='spam',
            data_element_id='bacon',
            comment='spam spam'
        )

    def tearDown(self):
        self.map_1.delete()
        self.map_2.delete()

    def test_caching(self):
        info_1 = get_info_for_columns(self.map_1)
        info_2 = get_info_for_columns(self.map_2)
        self.assertNotEqual(info_1, info_2)
        self.assertEqual(info_1, {'foo': {
            'column': 'foo',
            'data_element_id': 'bar',
            'category_option_combo_id': '',
            'comment': 'foo bar',
            'is_org_unit': False,
            'is_period': False,
        }})
        self.assertEqual(info_2, {'spam': {
            'column': 'spam',
            'data_element_id': 'bacon',
            'category_option_combo_id': '',
            'comment': 'spam spam',
            'is_org_unit': False,
            'is_period': False,
        }})


class TestGetGroupedDatasets(TestCase):

    def test_group_data_by_keys(self):
        data_list = [
            {'dataElement': 'dataElementID1', 'period': '202102', 'value': 90456},
            {'dataElement': 'dataElementID2', 'period': '202103', 'value': 90456},
            {'dataElement': 'dataElementID3', 'period': '202104', 'value': 135},
            {'dataElement': 'dataElementID4', 'period': '202105', 'value': 90333},
            {'dataElement': 'dataElementID5', 'period': '202106', 'value': 90333},
            {'dataElement': 'dataElementID6', 'period': '202103', 'value': 90456},
            {'dataElement': 'dataElementID7', 'period': '202102', 'value': 90210}
        ]
        num_unique_periods = 5
        result = _group_data_by_keys(data_list, ['period'])

        self.assertEqual(len(result), num_unique_periods)
        for key_value, key_grouped in result.items():
            if key_value == ('202102',):
                self.assertEqual(
                    key_grouped,
                    [
                        {'dataElement': 'dataElementID1', 'value': 90456},
                        {'dataElement': 'dataElementID7', 'value': 90210}
                    ]
                )
            elif key_value == ('202103',):
                self.assertEqual(
                    key_grouped,
                    [
                        {'dataElement': 'dataElementID2', 'value': 90456},
                        {'dataElement': 'dataElementID6', 'value': 90456}
                    ]
                )
            elif key_value == ('202104',):
                self.assertEqual(
                    key_grouped,
                    [{'dataElement': 'dataElementID3', 'value': 135}]
                )
            elif key_value == ('202105',):
                self.assertEqual(
                    key_grouped,
                    [{'dataElement': 'dataElementID4', 'value': 90333}]
                )
            else:
                self.assertEqual(
                    key_grouped,
                    [{'dataElement': 'dataElementID5', 'value': 90333}]
                )

    def test_group_by_period(self):
        template_dataset = {'dataSet': 'p1UpPrpg1QX', 'orgUnit': 'g8dWMTyEZGZ'}

        data_list = [
            {'dataElement': 'dataElementID1', 'period': '202102', 'value': 90456},
            {'dataElement': 'dataElementID2', 'period': '202103', 'value': 90456},
            {'dataElement': 'dataElementID3', 'period': '202104', 'value': 135},
            {'dataElement': 'dataElementID4', 'period': '202105', 'value': 90333},
            {'dataElement': 'dataElementID5', 'period': '202106', 'value': 90333},
            {'dataElement': 'dataElementID6', 'period': '202103', 'value': 90456},
            {'dataElement': 'dataElementID7', 'period': '202102', 'value': 90210}
        ]

        grouped_result = get_grouped_datavalues_sets(
            group_by_keys=['period'],
            template_dataset=template_dataset,
            data_list=data_list
        )

        expected_results = {
            '202102': [
                {'dataElement': 'dataElementID1', 'value': 90456},
                {'dataElement': 'dataElementID7', 'value': 90210}
            ],
            '202103': [
                {'dataElement': 'dataElementID2', 'value': 90456},
                {'dataElement': 'dataElementID6', 'value': 90456}
            ],
            '202104': [
                {'dataElement': 'dataElementID3', 'value': 135}
            ],
            '202105': [
                {'dataElement': 'dataElementID4', 'value': 90333}
            ],
            '202106': [
                {'dataElement': 'dataElementID5', 'value': 90333}
            ]
        }

        self.assertEqual(len(grouped_result), 5)

        for res in grouped_result:
            self.assertIn('period', res)
            self.assertIn('dataValues', res)
            self.assertEqual(expected_results[res['period']], res['dataValues'])

    def test_group_by_orgUnit(self):
        template_dataset = {'dataSet': 'p1UpPrpg1QX', 'period': '202104'}

        data_list = [
            {'dataElement': 'dataElementID1', 'orgUnit': 'orgUnit1', 'value': 90456},
            {'dataElement': 'dataElementID2', 'orgUnit': 'orgUnit1', 'value': 90456},
            {'dataElement': 'dataElementID3', 'orgUnit': 'orgUnit2', 'value': 135},
            {'dataElement': 'dataElementID4', 'orgUnit': 'orgUnit3', 'value': 135}
        ]

        grouped_result = get_grouped_datavalues_sets(
            group_by_keys=['orgUnit'],
            template_dataset=template_dataset,
            data_list=data_list
        )

        expected_results = {
            'orgUnit1': [
                {'dataElement': 'dataElementID1', 'value': 90456},
                {'dataElement': 'dataElementID2', 'value': 90456}
            ],
            'orgUnit2': [
                {'dataElement': 'dataElementID3', 'value': 135}
            ],
            'orgUnit3': [
                {'dataElement': 'dataElementID4', 'value': 135}
            ]
        }

        self.assertEqual(len(grouped_result), 3)

        for res in grouped_result:
            self.assertIn('orgUnit', res)
            self.assertIn('dataValues', res)
            self.assertEqual(expected_results[res['orgUnit']], res['dataValues'])

    def test_group_by_orgUnit_and_period(self):
        template_dataset = {'dataSet': 'p1UpPrpg1QX'}

        data_list = [
            {'dataElement': 'dataElementID1', 'orgUnit': 'orgUnit1', 'period': '202101', 'value': 90456},
            {'dataElement': 'dataElementID2', 'orgUnit': 'orgUnit1', 'period': '202101', 'value': 90456},
            {'dataElement': 'dataElementID3', 'orgUnit': 'orgUnit1', 'period': '202102', 'value': 90456},
            {'dataElement': 'dataElementID4', 'orgUnit': 'orgUnit2', 'period': '202102', 'value': 135},
            {'dataElement': 'dataElementID5', 'orgUnit': 'orgUnit3', 'period': '202103', 'value': 135}
        ]

        grouped_result = get_grouped_datavalues_sets(
            group_by_keys=['orgUnit', 'period'],
            template_dataset=template_dataset,
            data_list=data_list
        )

        expected_results = [
            {'dataElement': 'dataElementID1', 'value': 90456},
            {'dataElement': 'dataElementID2', 'value': 90456}
        ]

        self.assertEqual(len(grouped_result), 4)

        result_of_interest = None
        for result in grouped_result:
            if result.get('orgUnit') == 'orgUnit1' and result.get('period') == '202101':
                result_of_interest = result
                break

        self.assertEqual(result_of_interest.get('dataValues'), expected_results)
