"""Admission records must not silently discard private product guardrails."""
import json
from pathlib import Path
import tempfile
import unittest

from emit_admission_records import private_obligations


class PrivateCaseObligationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'obligations.json'
        self.row = {'case_identity_sha256': 'a' * 64,
                    'treatment': 'replace-product-guardrail', 'reason': 'Preserve source custody boundary',
                    'negative_control': 'Reject injected production-custody claim',
                    'positive_control': 'Accept bounded transport credentials',
                    'target_gate': 'production source checks', 'after_execution': 'required'}

    def load(self, rows, commit='b' * 40):
        self.path.write_text(json.dumps({'source': 'lab', 'source_commit': commit,
                                        'source_case_count': len(rows), 'cases': rows}))
        return private_obligations(self.path, 'b' * 40)

    def test_explicit_positive_and_negative_obligation_accepted(self):
        self.assertEqual(self.load([self.row])['a' * 64], self.row)

    def test_duplicate_cannot_hide_missing_case(self):
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            self.load([self.row, self.row])

    def test_blanket_retirement_rejected(self):
        self.row['treatment'] = 'exclude-private-repository-maintenance'
        with self.assertRaisesRegex(ValueError, 'unreviewed'):
            self.load([self.row])

    def test_replacement_without_positive_control_rejected(self):
        self.row.pop('positive_control')
        with self.assertRaisesRegex(ValueError, 'positive/negative'):
            self.load([self.row])

    def test_changed_source_rejected(self):
        with self.assertRaisesRegex(ValueError, 'source drift'):
            self.load([self.row], 'c' * 40)


if __name__ == '__main__':
    unittest.main()
