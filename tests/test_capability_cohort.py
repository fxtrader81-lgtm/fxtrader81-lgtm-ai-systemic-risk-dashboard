"""Full-task, different-platform ranking, provenance and history regressions."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from core import capability_cohort as cohort
from core import capability_gap as cap


def fixture(*, revision="a"*40, delta=0, extra=False):
    rows = [
        ("gpt-6", "OpenAI", False, [90+delta,90]),
        ("gpt-5", "OpenAI", False, [85,85]),
        ("claude-5", "Anthropic", False, [95,95]),
        ("gemini-3", "Google", False, [80,80]),
        ("deepseek-v4", "DeepSeek", True, [80,80]),
        ("qwen3", "Alibaba", True, [75,75]),
        ("kimi-k3", "Moonshot AI", True, [70,70]),
        ("qwen-closed", "Alibaba", False, [99,99]),
        ("smaug-open", "Abacus.AI", True, [100,100]),
        ("unknown", "Unknown", False, [100,100]),
    ]
    tasks = ["test_a", "test_b"] + (["test_c"] if extra else [])
    text = "model,"+",".join(tasks)+"\n"
    metadata = {}
    for model, org, opened, scores in rows:
        values = scores+([50] if extra else [])
        text += model+","+",".join(map(str, values))+"\n"
        metadata[model] = {"organization":org,"openweight":opened,"displayName":model}
    return cohort.make_full_snapshot(text, "export const modelLinks = "+json.dumps(metadata)+";",
        {"Category":tasks}, revision=revision, release="2026-06-25", checked_at="2026-10-18T10:00:00+00:00")


class FullTaskMathTests(unittest.TestCase):
    def test_sum_every_task_select_three_different_companies_then_mean(self):
        s = fixture()
        self.assertEqual(s["task_count"],2)
        self.assertEqual([x["total"] for x in s["selected"]["closed"]],[190,180,160])
        self.assertEqual([x["total"] for x in s["selected"]["open"]],[160,150,140])
        self.assertEqual(len({r["company"] for r in s["selected"]["closed"]}),3)
        self.assertAlmostEqual(s["metrics"]["closed_avg"],530/3)
        self.assertEqual(s["metrics"]["open_avg"],150)
        self.assertAlmostEqual(s["metrics"]["signed_gap"],(530/3-150)/(530/3)*100)
        self.assertEqual(s["metrics"]["state"],"SAFE")

    def test_country_is_not_openness_and_unknowns_are_explicit(self):
        s=fixture()
        excluded={r["model"]:r["reason"] for r in s["excluded"]}
        self.assertIn("qwen-closed",excluded)
        self.assertIn("smaug-open",excluded)
        self.assertIn("待核验",excluded["unknown"])

    def test_platform_max_is_one_whole_model_not_best_subtasks(self):
        s=fixture()
        raw=s["raw_csv"].replace('gpt-5,85,85','gpt-5,100,10')
        out=cohort.make_full_snapshot(raw,s["raw_metadata"],s["categories"],
            revision=s["revision"],release=s["release"],checked_at=s["checked_at"])
        openai=next(r for r in out["selected"]["closed"] if r["company"]=="OpenAI")
        self.assertEqual(openai["total"],180)
        self.assertEqual(openai["model"],"gpt-6")

    def test_added_tasks_are_all_included_and_recorded(self):
        a,b=fixture(),fixture(extra=True)
        self.assertEqual(b["selected"]["closed"][0]["total"],240)
        self.assertTrue(any('test_c' in n for n in cohort.describe_change(a,b)))
        self.assertNotEqual(cohort.fingerprint(a),cohort.fingerprint(b))

    def test_missing_or_invalid_tests_do_not_become_zero(self):
        s=fixture()
        for value in ['', 'nan','101']:
            raw=s["raw_csv"].replace('kimi-k3,70,70','kimi-k3,70,'+value)
            with self.assertRaisesRegex(ValueError,'不足三家'):
                cohort.make_full_snapshot(raw,s["raw_metadata"],s["categories"],
                    revision=s["revision"],release=s["release"],checked_at=s["checked_at"])

    def test_categories_only_validate_schema_never_change_weights(self):
        s=fixture()
        with self.assertRaises(ValueError):
            cohort.make_full_snapshot(s["raw_csv"],s["raw_metadata"],{'unknown':['cost']},
                revision=s["revision"],release=s["release"],checked_at=s["checked_at"])
        alt=cohort.make_full_snapshot(s["raw_csv"],s["raw_metadata"],{'a':['test_a'],'b':['test_b']},
                revision=s["revision"],release=s["release"],checked_at=s["checked_at"])
        self.assertEqual(s["metrics"],alt["metrics"])

    def test_reviewed_live_seed_has_all_23_tasks_and_expected_result(self):
        source=json.loads(cohort.SEED.read_text())
        s=cohort.validate_snapshot(source)
        self.assertEqual(s["task_count"],23)
        self.assertEqual(s["row_count"],71)
        self.assertEqual([r["company"] for r in s["selected"]["closed"]],['Anthropic','OpenAI','Meta'])
        self.assertEqual([r["company"] for r in s["selected"]["open"]],['DeepSeek','Alibaba','Moonshot AI'])
        self.assertAlmostEqual(s["metrics"]["closed_avg"],1910.990)
        self.assertAlmostEqual(s["metrics"]["open_avg"],1843.259)
        self.assertAlmostEqual(s["metrics"]["signed_gap"],3.544288562472843)
        self.assertEqual(s["metrics"]["state"],'WARNING')


class SourceParsingTests(unittest.TestCase):
    def test_js_data_only_and_variant_inheritance(self):
        text='''export const modelLinks = {"claude-base": { organization: "Anthropic", url: "https://example.com", variants: [{rawName: "claude-max", displayName: "Max"}], },}; malicious();'''
        data=cohort.parse_metadata(text)
        self.assertEqual(data['claude-max']['organization'],'Anthropic')
        self.assertEqual(data['claude-max']['displayName'],'Max')
        for text in ['export const modelLinks = {"m": process.exit()};',
                     'export const modelLinks = {"m": {},"m": {}};']:
            with self.assertRaises(ValueError):cohort.parse_metadata(text)

    def test_duplicate_models_or_columns_fail(self):
        for raw in ['model,a,a\ngpt-6,2,3\n','model,a\ngpt-6,2\ngpt-6,3\n']:
            with self.assertRaises(ValueError):cohort.parse_full_csv(raw)

    def test_refresh_pins_every_read_to_one_commit_and_latest_release(self):
        s=fixture();seen=[]
        def read(revision,path):
            seen.append((revision,path))
            if path.endswith('constants.js'):
                return 'export const RELEASES = ["2026-01-08", "2026-06-25"];'
            if path.endswith('.csv'):return s['raw_csv']
            if path.endswith('modelLinks.js'):return s['raw_metadata']
            return json.dumps(s['categories'])
        with patch.object(cohort,'resolve_revision',return_value='b'*40),patch.object(cohort,'_read',side_effect=read):
            result=cohort.fetch_latest_snapshot()
        self.assertEqual({sha for sha,path in seen},{'b'*40})
        self.assertEqual(result['release'],'2026-06-25')
        self.assertTrue(any(path=='public/table_2026_06_25.csv' for sha,path in seen))


class FullHistoryTests(unittest.TestCase):
    def test_old_and_new_records_survive_and_same_content_deduplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'history.sqlite3'
            old=cap.current_snapshot(path)
            s=fixture()
            self.assertTrue(cap.adopt(s,path))
            self.assertEqual(len(cap.history(path)),2)
            self.assertIn(old,cap.history(path))
            self.assertEqual(cap.current_snapshot(path)['formula_version'],cohort.VERSION)
            same=copy.deepcopy(s);same['checked_at']='2026-10-19T10:00:00+00:00';same['revision']='b'*40
            self.assertFalse(cap.adopt(same,path))
            self.assertEqual(len(cap.history(path)),2)
            self.assertTrue(cap.adopt(fixture(delta=1),path))
            self.assertEqual(len(cap.history(path)),3)

    def test_bad_refresh_cannot_replace_last_good_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'history.sqlite3';cap.adopt(fixture(),path)
            before=cap.current_snapshot(path)
            broken=fixture();broken['raw_csv']=broken['raw_csv'].replace('kimi-k3,70,70','kimi-k3,70,')
            with self.assertRaises(ValueError):cap.adopt(broken,path)
            self.assertEqual(cap.current_snapshot(path),before)


if __name__=='__main__':unittest.main()
