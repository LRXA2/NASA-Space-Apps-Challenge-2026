"""Local contracts for the environmental CSV interface; fixtures are fictional."""
from copy import deepcopy
import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import run_pipeline as engine


def fixture():
    policy = engine.read_json(HERE / "examples/demo_policy.json")
    rows = engine.load_rows(HERE / "examples/sites.csv", engine.validate_policy(policy)[0])
    metadata = engine.read_json(HERE / "examples/evidence.json")["rows"]
    return policy, rows, metadata


class EnvironmentCsvTests(unittest.TestCase):
    def test_score_normalization_and_output_fields(self):
        policy, rows, meta = fixture()
        result, _, detail, _ = engine.assess(rows[:1], policy, meta)
        self.assertEqual(result[0]["rad_score_status"], "Context_only")
        self.assertEqual(result[0]["terrain_score"], 80)
        self.assertEqual(result[0]["solar_illumination_score"], 80)
        self.assertEqual(result[0]["habitability_score"], 80)
        self.assertEqual(result[0]["final_rec_score"], 80)
        self.assertEqual(result[0]["operational_suitability"], "Not assessed")
        self.assertEqual(len(detail), 2)

    def test_gate_first_failure_and_missing_hard_evidence(self):
        policy, rows, meta = fixture()
        result, _, _, _ = engine.assess(rows, policy, meta)
        by = {r["id"]: r for r in result}
        self.assertEqual(by["B_fail"]["hard_gate_status"], "Failed")
        self.assertEqual(by["B_fail"]["final_rec_score"], "")
        self.assertEqual(by["C_unknown"]["hard_gate_status"], "Unknown")
        self.assertEqual(by["C_unknown"]["rank"], "")
        self.assertEqual(len(result), len(rows))

    def test_missing_soft_evidence_does_not_reweight(self):
        policy, rows, meta = fixture()
        result = engine.assess([rows[3]], policy, meta)[0][0]
        self.assertEqual(result["hard_gate_status"], "Passed")
        self.assertEqual(result["terrain_score"], 70)
        self.assertEqual(result["habitability_score"], "")
        self.assertEqual(result["final_rec_score"], "")

    def test_failed_dominates_unknown(self):
        policy, rows, meta = fixture()
        policy["hard_rules"].append(dict(id="unknown_limit", metric="solar_visibility_median", operator="ge", limit=None, reason="Not adopted"))
        self.assertEqual(engine.assess([rows[1]], policy, meta)[0][0]["hard_gate_status"], "Failed")

    def test_ties_are_stable_and_periods_do_not_mix(self):
        policy, rows, meta = fixture()
        result = engine.assess(list(reversed(rows)), policy, meta)[0]
        ranks = {r["id"]: r["rank"] for r in result}
        self.assertEqual(ranks["A_pass"], 1)
        self.assertEqual(ranks["F_tie"], 2)
        self.assertEqual(ranks["E_other_period"], 1)
        self.assertEqual([r["id"] for r in result], [r["id"] for r in reversed(rows)])

    def test_equivalent_utc_offsets_share_rank_group(self):
        policy, rows, meta = fixture()
        rows[5]["start_utc"] = "2023-06-01T08:00:00+08:00"
        self.assertEqual(engine.assess(rows, policy, meta)[0][5]["rank"], 2)

    def test_default_policy_has_no_fake_limits_or_weights(self):
        policy, rows, meta = fixture()
        default = engine.read_json(HERE / "environmental_policy.json")
        for metrics in meta.values():
            for item in metrics.values():
                item["basis"] = "modeled"
        result = engine.assess(rows, default, meta)[0]
        self.assertTrue(all(r["hard_gate_status"] == "Unknown" for r in result))
        self.assertTrue(all(r["final_rec_score"] == "" for r in result))
        self.assertTrue(all(d["weight"] is None for d in default["domains"]))
        self.assertEqual(default["hard_rules"], [])

    def test_empty_hard_gate_does_not_pass(self):
        policy, rows, meta = fixture()
        policy["hard_rules"] = []
        self.assertEqual(engine.assess(rows[:1], policy, meta)[0][0]["hard_gate_status"], "Unknown")

    def test_unresolved_domain_weight_withholds_aggregate(self):
        policy, rows, meta = fixture()
        next(d for d in policy["domains"] if d["id"] == "terrain")["weight"] = None
        self.assertEqual(engine.assess(rows[:1], policy, meta)[0][0]["final_rec_score"], "")

    def test_context_evidence_is_not_local(self):
        policy, rows, meta = fixture()
        for scope in ("orbital", "global", "regional"):
            with self.subTest(scope=scope):
                changed = deepcopy(meta)
                changed["A_pass"]["slope_q90_deg"]["scope"] = scope
                result = engine.assess(rows[:1], policy, changed)[0][0]
                self.assertEqual(result["hard_gate_status"], "Unknown")
                self.assertEqual(result["final_rec_score"], "")

    def test_wrong_body_candidate_or_quality_is_unknown(self):
        policy, rows, meta = fixture()
        for field, value in (("body", "Earth"), ("candidate_id", "other_site"), ("quality", "rejected"), ("support_count", 0)):
            with self.subTest(field=field):
                changed = deepcopy(meta)
                changed["A_pass"]["slope_q90_deg"][field] = value
                self.assertEqual(engine.assess(rows[:1], policy, changed)[0][0]["hard_gate_status"], "Unknown")

    def test_missing_metadata_never_passes(self):
        policy, rows, _ = fixture()
        result = engine.assess(rows[:1], policy, {})[0][0]
        self.assertEqual(result["hard_gate_status"], "Unknown")
        self.assertEqual(result["evidence_coverage"], "0/2")

    def test_unit_or_quantity_mismatch_is_error(self):
        policy, rows, meta = fixture()
        for field in ("unit", "quantity"):
            with self.subTest(field=field):
                changed = deepcopy(meta)
                changed["A_pass"]["slope_q90_deg"][field] = "wrong"
                with self.assertRaisesRegex(ValueError, "unit/quantity"):
                    engine.assess(rows[:1], policy, changed)

    def test_synthetic_cannot_leak_into_real_policy(self):
        policy, rows, meta = fixture()
        policy["mode"] = "environmental"
        with self.assertRaisesRegex(ValueError, "Synthetic"):
            engine.assess(rows[:1], policy, meta)

    def test_missing_or_mismatched_window_is_unknown(self):
        policy, rows, meta = fixture()
        metric = next(m for m in policy["metrics"] if m["id"] == "solar_visibility_median")
        metric["temporal_support"] = "window"
        item = meta["A_pass"]["solar_visibility_median"]
        item["temporal_support"] = "window"
        result = engine.assess(rows[:1], policy, meta)[0][0]
        self.assertEqual(result["solar_illumination_score_status"], "Unknown")
        item.update(start_utc=rows[0]["start_utc"], stop_utc="2023-06-15T00:00:00Z")
        self.assertEqual(engine.assess(rows[:1], policy, meta)[0][0]["final_rec_score"], "")
        item["stop_utc"] = rows[0]["stop_utc"]
        self.assertEqual(engine.assess(rows[:1], policy, meta)[0][0]["final_rec_score"], 80)

    def test_static_cannot_be_relabeled_as_window(self):
        policy, rows, meta = fixture()
        meta["A_pass"]["slope_q90_deg"]["temporal_support"] = "window"
        self.assertEqual(engine.assess(rows[:1], policy, meta)[0][0]["hard_gate_status"], "Unknown")

    def test_malformed_nonfinite_and_out_of_domain_values_error(self):
        policy, rows, meta = fixture()
        for value in ("NaN", "inf", "bad", "-1", "91"):
            with self.subTest(value=value):
                changed = deepcopy(rows[:1])
                changed[0]["slope_q90_deg"] = value
                with self.assertRaises(ValueError):
                    engine.assess(changed, policy, meta)

    def test_utility_clipping_and_preferred_range(self):
        pref = dict(direction="higher", lower=0, upper=10)
        self.assertEqual(engine.utility(-2, pref), 0)
        self.assertEqual(engine.utility(12, pref), 1)
        pref.update(direction="lower")
        self.assertEqual(engine.utility(12, pref), 0)
        pref.update(direction="target_range", preferred_lower=3, preferred_upper=7)
        self.assertEqual(engine.utility(5, pref), 1)
        self.assertAlmostEqual(engine.utility(1.5, pref), .5)
        self.assertAlmostEqual(engine.utility(8.5, pref), .5)

    def test_unequal_domain_weights_and_zero_score(self):
        policy, rows, meta = fixture()
        rows[0]["solar_visibility_median"] = "0.6"
        next(d for d in policy["domains"] if d["id"] == "terrain")["weight"] = 3
        self.assertAlmostEqual(engine.assess(rows[:1], policy, meta)[0][0]["final_rec_score"], 75)
        rows[0].update(solar_visibility_median="0", slope_q90_deg="10")
        policy["hard_rules"][0]["limit"] = 10
        result = engine.assess(rows[:1], policy, meta)[0][0]
        self.assertEqual(result["final_rec_score"], 0)
        self.assertEqual(result["rank"], 1)

    def test_all_nine_domain_columns_can_be_scored_with_explicit_synthetic_policy(self):
        policy, rows, meta = fixture()
        metric_map = {m["id"]: m for m in policy["metrics"]}
        row = rows[0]
        for domain in policy["domains"]:
            metric = next(m for m in metric_map.values() if m["domain"] == domain["id"])
            upper = 1 if metric["unit"] == "fraction" else 10
            row[metric["column"]] = str(upper / 2)
            pref = dict(metric=metric["id"], direction="higher", lower=0, upper=upper, weight=1,
                        reason="Synthetic arithmetic only", source="Fictional software test")
            if domain["id"] in {"exosphere", "plasma_charging"}:
                pref.update(direction="target_range", preferred_lower=3, preferred_upper=7)
            domain.update(scored=True, weight=1, preferences=[pref])
            meta[row["id"]][metric["id"]] = dict(
                body="Moon", candidate_id=row["candidate_id"], scope="candidate", basis="synthetic",
                quality="qualified", source="Fictional software test", support_count=1,
                unit=metric["unit"], quantity=metric["quantity"], temporal_support=metric["temporal_support"],
                start_utc=row["start_utc"], stop_utc=row["stop_utc"])
        result = engine.assess([row], policy, meta)[0][0]
        self.assertTrue(all(result[c + "_status"] == "Scored" for c in engine.DOMAIN_COLUMNS.values()))
        self.assertAlmostEqual(result["final_rec_score"], 100 * 5.5 / 9)

    def test_unconfigured_mode_cannot_issue_numerical_scores(self):
        policy, _, _ = fixture()
        policy["mode"] = "unconfigured"
        with self.assertRaisesRegex(ValueError, "explicit assessment mode"):
            engine.validate_policy(policy)

    def test_shared_proxy_cannot_be_weighted_twice(self):
        policy, _, _ = fixture()
        next(m for m in policy["metrics"] if m["id"] == "slope_q90_deg")["evidence_family"] = "sun_visibility"
        with self.assertRaisesRegex(ValueError, "Repeated scored evidence"):
            engine.validate_policy(policy)

    def test_policy_rejects_earth_visibility_and_invalid_weights(self):
        policy, _, _ = fixture()
        for value in (0, -1, "1", True):
            with self.subTest(weight=value):
                changed = deepcopy(policy)
                next(d for d in changed["domains"] if d["scored"])["weight"] = value
                with self.assertRaises(ValueError):
                    engine.validate_policy(changed)
        policy["metrics"][0]["column"] = "earth_visibility_median"
        with self.assertRaisesRegex(ValueError, "Earth visibility"):
            engine.validate_policy(policy)

    def test_missing_domain_and_duplicate_metrics_rejected(self):
        policy, _, _ = fixture()
        changed = deepcopy(policy)
        changed["domains"].pop()
        with self.assertRaises(ValueError):
            engine.validate_policy(changed)
        policy["metrics"].append(deepcopy(policy["metrics"][0]))
        with self.assertRaises(ValueError):
            engine.validate_policy(policy)

    def test_csv_validation(self):
        policy, _, _ = fixture()
        metrics = engine.validate_policy(policy)[0]
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.csv"
            for text in ("id,id\na,b\n", "id,candidate_id,start_utc,stop_utc,evidence_ref\n", "id,candidate_id,start_utc,stop_utc,evidence_ref\na,b,2023-01-01,2023-01-02,\n"):
                p.write_text(text)
                with self.assertRaises(ValueError):
                    engine.load_rows(p, metrics)
            with (HERE / "examples/sites.csv").open(newline="") as h:
                rows = list(csv.reader(h))
            for bad_rows in (rows + [rows[1]], [rows[0] + ["typo_metric"], rows[1] + ["1"]], [rows[0], rows[1] + ["extra"]]):
                with p.open("w", newline="") as h:
                    csv.writer(h).writerows(bad_rows)
                with self.assertRaises(ValueError):
                    engine.load_rows(p, metrics)

    def test_real_csv_output_hashes_provenance_and_overwrite_protection(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "results.csv"
            record = engine.run(HERE / "examples/sites.csv", output, HERE / "examples/demo_policy.json")
            self.assertEqual(record["input_rows"], 6)
            self.assertEqual(record["ranked_rows"], 3)
            for item in record["outputs"]:
                self.assertEqual(engine.sha256(item["path"]), item["sha256"])
            with output.open(newline="") as h:
                rows = list(csv.DictReader(h))
            self.assertEqual(rows[1]["final_rec_score"], "")
            with self.assertRaises(FileExistsError):
                engine.run(HERE / "examples/sites.csv", output, HERE / "examples/demo_policy.json")

    def test_inputs_cannot_be_overwritten_even_explicitly(self):
        with self.assertRaisesRegex(ValueError, "must not overwrite"):
            engine.run(HERE / "examples/sites.csv", HERE / "examples/sites.csv", HERE / "examples/demo_policy.json", overwrite=True)

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate JSON"):
            json.loads('{"id":1,"id":2}', object_pairs_hook=engine.unique_object)


if __name__ == "__main__":
    unittest.main()
