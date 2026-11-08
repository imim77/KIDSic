"""Subsidy presentation keeps tariffs and proposed changes distinct."""

import json
import unittest
from pathlib import Path

from KIDSic.services.concrete.subsidy import SubsidyPolicyPresenter


class SubsidyPresenterTests(unittest.TestCase):
    def setUp(self):
        sql = (
            Path(__file__).resolve().parents[1] / "src/KIDSic/db/seeds/"
            "2026-11-04_municipal_subsidies.sql"
        ).read_text()
        self.policies = {
            p["policy_key"]: p for p in json.loads(sql.split("$subsidy_snapshot$")[1])
        }
        self.presenter = SubsidyPolicyPresenter()

    def policy(self, key):
        return self.presenter.present(self.policies[key + "-20261104"])

    def test_all_city_types_keep_readable_rates_and_sources(self):
        for policy in self.policies.values():
            result = self.presenter.present(policy)
            self.assertTrue(result.sources)
            self.assertTrue(result.conditions)
            self.assertTrue(all(rate.label for rate in result.rates))
        private = self.policy("zagreb-private")
        self.assertEqual(private.amount_kind, "city_subsidy")
        self.assertEqual(
            [r.city_subsidy_cents for r in private.rates], [35254, 37245, 39236, 41226]
        )
        self.assertIn("1040,01 €", private.rates[0].label)
        public = self.policy("zagreb-municipal")
        self.assertEqual(public.amount_kind, "parent_fee")
        self.assertEqual(len(public.rates), 8)
        self.assertTrue(all(r.city_subsidy_cents is None for r in public.rates))
        self.assertTrue(any("najpovoljnija" in note for note in public.notes))
        self.assertTrue(any("75 %" in relief for relief in public.reliefs))
        varazdin = self.policy("varazdin-municipal")
        self.assertEqual(varazdin.rates[0].parent_fee_cents, 9000)
        self.assertEqual(varazdin.rates[0].city_subsidy_cents, 36000)

    def test_partial_amount_is_unknown_and_proposal_never_becomes_a_rate(self):
        partial = self.policy("varazdin-childminder")
        self.assertEqual(partial.verification_status, "partial")
        self.assertEqual(partial.rates, [])
        rijeka = self.policy("rijeka-childminder")
        self.assertEqual([r.city_subsidy_cents for r in rijeka.rates], [26000])
        self.assertTrue(any("nije uključena" in note for note in rijeka.notes))
