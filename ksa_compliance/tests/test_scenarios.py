from ksa_compliance.tests.case import ZatcaTestCase
from ksa_compliance.tests.scenarios import DRIFTING, SCENARIOS


class TestScenarios(ZatcaTestCase):
    """Tests that scenarios that are supposed to exercise drift do so."""

    def test_drifting_scenarios_exist(self):
        self.assertLessEqual(DRIFTING, {scenario.name for scenario in SCENARIOS})

    def test_drift_is_as_declared(self):
        self.for_each_scenario(
            lambda scenario, invoice, xml: self.assertEqual(
                xml.sum_line_vat != xml.bt110_total_vat_amount, scenario.drifts
            )
        )
