# -*- coding: utf-8 -*-

import datetime

from nose.tools import raises
from nose.tools import assert_equal

from .. import columns, periods
from ..reforms import Reform, compose_reforms, updated_legislation_items
from ..formulas import dated_function
from ..variables import Variable, DatedVariable
from ..periods import Instant
from ..tools import assert_near
from .dummy_country import Familles
from .test_countries import TestTaxBenefitSystem

tax_benefit_system = TestTaxBenefitSystem()


def test_formula_neutralization():

    class test_rsa_neutralization(Reform):
        def apply(self):
            self.neutralize_column('rsa')

    reform = test_rsa_neutralization(tax_benefit_system)

    year = 2013
    scenario = reform.new_scenario().init_single_entity(
        period = year,
        famille = dict(depcom = '75101'),
        parent1 = dict(),
        parent2 = dict(),
        )
    simulation = scenario.new_simulation(debug = True, reference = True)
    rsa = simulation.calculate('rsa', period = '2013-01')
    assert_near(rsa, 300, absolute_error_margin = 0)
    revenu_disponible = simulation.calculate('revenu_disponible')
    assert_near(revenu_disponible, 3600, absolute_error_margin = 0)

    reform_simulation = scenario.new_simulation(debug = True)
    rsa_reform = reform_simulation.calculate('rsa', period = '2013-01')
    assert_near(rsa_reform, 0, absolute_error_margin = 0)
    revenu_disponible_reform = reform_simulation.calculate('revenu_disponible')
    assert_near(revenu_disponible_reform, 0, absolute_error_margin = 0)


def test_input_variable_neutralization():

    class test_salaire_brut_neutralization(Reform):
        def apply(self):
            self.neutralize_column('salaire_brut')

    reform = test_salaire_brut_neutralization(tax_benefit_system)

    year = 2013
    scenario = reform.new_scenario().init_single_entity(
        period = year,
        famille = dict(depcom = '75101'),
        parent1 = dict(
            salaire_brut = 120000,
            ),
        parent2 = dict(
            salaire_brut = 60000,
            ),
        )
    simulation = scenario.new_simulation(reference = True)
    salaire_brut_annuel = simulation.calculate('salaire_brut')
    assert_near(salaire_brut_annuel, [120000, 60000], absolute_error_margin = 0)
    salaire_brut_mensuel = simulation.calculate('salaire_brut', period = '2013-01')
    assert_near(salaire_brut_mensuel, [10000, 5000], absolute_error_margin = 0)
    revenu_disponible = simulation.calculate('revenu_disponible')
    assert_near(revenu_disponible, [60480, 30240], absolute_error_margin = 0)

    reform_simulation = scenario.new_simulation()
    salaire_brut_annuel_reform = reform_simulation.calculate('salaire_brut')
    assert_near(salaire_brut_annuel_reform, [0, 0], absolute_error_margin = 0)
    salaire_brut_mensuel_reform = reform_simulation.calculate('salaire_brut', period = '2013-01')
    assert_near(salaire_brut_mensuel_reform, [0, 0], absolute_error_margin = 0)
    revenu_disponible_reform = reform_simulation.calculate('revenu_disponible')
    assert_near(revenu_disponible_reform, [3600, 3600], absolute_error_margin = 0)


def test_updated_legislation_items():
    def check_updated_legislation_items(description, items, start_instant, stop_instant, value, expected_items):
        new_items = updated_legislation_items(items, start_instant, stop_instant, value)
        assert_equal(map(dict, new_items), expected_items)

    yield(
        check_updated_legislation_items,
        u'Replace an item by a new item',
        [
            {
                "start": "2013-01-01",
                "stop": "2013-12-31",
                "value": 0.0,
                },
            ],
        periods.period('year', 2013).start,
        periods.period('year', 2013).stop,
        1,
        [
            {
                "start": "2013-01-01",
                "stop": "2013-12-31",
                "value": 1.0,
                },
            ],
        )
    yield(
        check_updated_legislation_items,
        u'Insert a new item in the middle of an existing item',
        [
            {
                "start": "2010-01-01",
                "stop": "2013-12-31",
                "value": 0.0,
                },
            ],
        periods.period('year', 2011).start,
        periods.period('year', 2011).stop,
        1,
        [
            {
                "start": "2010-01-01",
                "stop": "2010-12-31",
                "value": 0.0,
                },
            {
                "start": "2011-01-01",
                "stop": "2011-12-31",
                "value": 1.0,
                },
            {
                "start": "2012-01-01",
                "stop": "2013-12-31",
                "value": 0.0,
                },
            ],
        )


def test_add_variable():

    class nouvelle_variable(Variable):
        column = columns.IntCol
        label = u"Nouvelle variable introduite par la réforme"
        entity_class = Familles

        def function(self, simulation, period):
            return period, self.zeros() + 10

    class test_add_variable(Reform):

        def apply(self):
            self.add_variable(nouvelle_variable)

    reform = test_add_variable(tax_benefit_system)

    year = 2013

    scenario = reform.new_scenario().init_single_entity(
        period = year,
        parent1 = dict(),
        )

    assert tax_benefit_system.get_column('nouvelle_variable') is None
    reform_simulation = scenario.new_simulation(debug = True)
    nouvelle_variable1 = reform_simulation.calculate('nouvelle_variable', period = '2013-01')
    assert_near(nouvelle_variable1, 10, absolute_error_margin = 0)


def test_add_dated_variable():
    class nouvelle_dated_variable(DatedVariable):
        column = columns.IntCol
        label = u"Nouvelle variable introduite par la réforme"
        entity_class = Familles

        @dated_function(datetime.date(2010, 1, 1))
        def function_2010(self, simulation, period):
            return period, self.zeros() + 10

        @dated_function(datetime.date(2011, 1, 1))
        def function_apres_2011(self, simulation, period):
            return period, self.zeros() + 15

    class test_add_variable(Reform):
        def apply(self):
            self.add_variable(nouvelle_dated_variable)

    reform = test_add_variable(tax_benefit_system)

    scenario = reform.new_scenario().init_single_entity(
        period = 2013,
        parent1 = dict(),
        )

    reform_simulation = scenario.new_simulation(debug = True)
    nouvelle_dated_variable1 = reform_simulation.calculate('nouvelle_dated_variable', period = '2013-01')
    assert_near(nouvelle_dated_variable1, 15, absolute_error_margin = 0)


def test_add_variable_with_reference():

    class revenu_disponible(Variable):

        def function(self, simulation, period):
            return period, self.zeros() + 10

    class test_add_variable_with_reference(Reform):
        def apply(self):
            self.update_variable(revenu_disponible)

    reform = test_add_variable_with_reference(tax_benefit_system)

    year = 2013
    scenario = reform.new_scenario().init_single_entity(
        period = year,
        parent1 = dict(),
        )

    revenu_disponible_reform = reform.get_column('revenu_disponible')
    revenu_disponible_reference = tax_benefit_system.get_column('revenu_disponible')

    assert revenu_disponible_reform is not None
    assert revenu_disponible_reform.entity_class.key_plural == revenu_disponible_reference.entity_class.key_plural
    assert revenu_disponible_reform.name == revenu_disponible_reference.name
    assert revenu_disponible_reform.label == revenu_disponible_reference.label

    reform_simulation = scenario.new_simulation()
    revenu_disponible1 = reform_simulation.calculate('revenu_disponible', period = '2013-01')
    assert_near(revenu_disponible1, 10, absolute_error_margin = 0)


@raises(Exception)
def test_wrong_reform():
    class wrong_reform(Reform):
        # A Reform must implement an `apply` method
        pass

    wrong_reform(tax_benefit_system)


def test_compose_reforms():

    class first_reform(Reform):
        class nouvelle_variable(Variable):
            column = columns.IntCol
            label = u"Nouvelle variable introduite par la réforme"
            entity_class = Familles

            def function(self, simulation, period):
                return period, self.zeros() + 10

        def apply(self):
            self.add_variable(self.nouvelle_variable)

    class second_reform(Reform):
        class nouvelle_variable(Variable):
            column = columns.IntCol
            label = u"Nouvelle variable introduite par la réforme"
            entity_class = Familles

            def function(self, simulation, period):
                return period, self.zeros() + 20

        def apply(self):
            self.update_variable(self.nouvelle_variable)

    reform = compose_reforms([first_reform, second_reform], tax_benefit_system)
    year = 2013
    scenario = reform.new_scenario().init_single_entity(
        period = year,
        parent1 = dict(),
        )

    reform_simulation = scenario.new_simulation(debug = True)
    nouvelle_variable1 = reform_simulation.calculate('nouvelle_variable', period = '2013-01')
    assert_near(nouvelle_variable1, 20, absolute_error_margin = 0)


def test_modify_legislation():

    def modify_legislation_json(reference_legislation_json_copy):
        reform_legislation_subtree = {
            "@type": "Node",
            "description": "Node added to the legislation by the reform",
            "children": {
                "new_param": {
                    "@type": "Parameter",
                    "description": "New parameter",
                    "format": "boolean",
                    "values": [{'start': u'2000-01-01', 'stop': u'2014-12-31', 'value': True}],
                    },
                },
            }
        reference_legislation_json_copy['children']['new_node'] = reform_legislation_subtree
        return reference_legislation_json_copy

    class test_modify_legislation(Reform):
        def apply(self):
            self.modify_legislation_json(modifier_function = modify_legislation_json)

    reform = test_modify_legislation(tax_benefit_system)

    legislation_new_node = reform.get_legislation()['children']['new_node']
    assert legislation_new_node is not None

    instant = Instant((2013, 1, 1))
    compact_legislation = reform.get_compact_legislation(instant)
    assert compact_legislation.new_node.new_param is True
