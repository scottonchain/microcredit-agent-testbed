import contextlib, copy, datetime, io, json, unittest
from unittest.mock import patch
import q


def run(*args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = q.main(list(args))
    return rc, buf.getvalue()


class QTest(unittest.TestCase):
    def test_prefix_lists_ids(self):
        rc, out = run("action:bootstrap")
        self.assertEqual(rc, 0)
        self.assertIn("action:bootstrap-candidate-by-next-sync", out)
        self.assertTrue(all(l.startswith("action:bootstrap") for l in out.strip().splitlines()))

    def test_full_record_is_json(self):
        _, out = run("-f", "action:bootstrap-candidate-by-next-sync")
        self.assertEqual(json.loads(out)["id"], "action:bootstrap-candidate-by-next-sync")

    def test_open_filters_done_and_owner(self):
        _, out = run("--open", "c")
        self.assertTrue(out.strip())
        for l in out.strip().splitlines():
            self.assertIn(" claude ", l)
            self.assertNotIn(" done ", l)

    def test_codex_lane_includes_coordinator_obligations(self):
        actions = [
            {"id": "action:codex-open", "owner_id": "agent:codex", "status": "ready"},
            {"id": "action:coordinator-open", "owner_id": "agent:coordinator", "status": "ready"},
            {"id": "action:claude-open", "owner_id": "agent:claude", "status": "ready"},
            {"id": "action:hermes-open", "owner_id": "agent:hermes", "status": "ready"},
            {"id": "action:codex-done", "owner_id": "agent:codex", "status": "done"},
            {"id": "action:coordinator-cancelled", "owner_id": "agent:coordinator", "status": "cancelled"},
        ]
        with patch.object(q, "load", return_value=({"actions": actions}, {})):
            _, out = run("--open", "x")
            _, exact = run("--open", "agent:codex")
        ids = {line.split()[0] for line in out.splitlines()}
        self.assertEqual(ids, {"action:codex-open", "action:coordinator-open"})
        self.assertEqual({line.split()[0] for line in exact.splitlines()}, {"action:codex-open"})

    def test_goal_names_are_visible_without_dumping_full_records(self):
        _, out = run("goal:poverty")
        self.assertIn("Measurable alleviation of human poverty", out)

    def test_missing_arguments_unknown_ids_and_invalid_hours_have_usage_errors(self):
        for arguments in (("-f",), ("-f", "action:missing"), ("--grep",), ("--due", "nan"), ("--due", "-1"), ("--due", "inf")):
            with self.subTest(arguments=arguments), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as result:
                run(*arguments)
            self.assertEqual(result.exception.code, 2)

    def test_grep_and_contains(self):
        _, out = run("--grep", "manager gate")
        self.assertIn("ev:claude-bootstrap-candidate-pr28-20261008", out)
        _, out = run("contains:manager-gate")
        self.assertIn("manager-gate", out)


class LearningRecallTest(unittest.TestCase):
    def setUp(self):
        learning = {
            'assumption': 'A cash advance removes the order bottleneck.',
            'result': 'inconclusive', 'finding': 'No order evidence was obtained.',
            'blocker_kind': 'distribution', 'evidence_ids': ['ev:source'],
            'counterevidence_ids': ['ev:challenge'],
            'rules_out': ['Claiming a qualified borrower.'],
            'does_not_rule_out': ['A different evidenced case.'],
            'alternatives': [{'mechanism': 'Customer prepayment',
                              'avoids_dependency': 'An external loan',
                              'cheapest_test': 'Inspect the payment schedule',
                              'transfer_limit': 'Needs buyer consent',
                              'related_ids': ['hyp:deposit']}],
            'revisit_when': ['New assigned order evidence'], 'tags': ['cash', 'credit'],
            'freshness': {'observed_at': '2026-10-01T00:00:00Z',
                          'recheck_by': '2026-10-31T00:00:00Z',
                          'recheck_on': ['Before using mutable terms']},
        }
        self.model = {k: [] for k in q.KINDS}
        self.model.update(model_version='test', updated_at='2026-11-01T00:00:00Z')
        self.model['actions'] = [
            {'id': 'action:closed', 'title': 'Closed qualification', 'status': 'cancelled', 'learning': learning},
            {'id': 'action:completed', 'title': 'Completed screen', 'status': 'done', 'learning': copy.deepcopy(learning)},
            {'id': 'action:unannotated', 'title': 'cash', 'status': 'ready'},
        ]
        self.model['evidence'] = [{'id': 'ev:source', 'summary': 'Limited coverage', 'limitations': ['No market census']},
                                  {'id': 'ev:challenge', 'summary': 'Conflicting observation'}]
        self.model['hypotheses'] = [{'id': 'hyp:deposit', 'theory': 'A deposit may avoid credit'}]
        self.model['coverage'] = [{'id': 'coverage:scope', 'limitations': ['Only one channel']}]
        self.index = {r['id']: (k, r) for k in q.KINDS for r in self.model[k]}
        self.now = datetime.datetime(2026, 11, 1, tzinfo=datetime.timezone.utc)

    def recall(self, query='cash', limit=5):
        return q.recall(self.model, self.index, query, limit, now=self.now)

    def test_closed_and_cancelled_learning_remains_retrievable(self):
        result = self.recall()
        self.assertEqual({r['status'] for r in result['results']}, {'done', 'cancelled'})
        self.assertEqual(result['learning_records_available'], 2)
        self.assertEqual(result['matching_records'], 2)

    def test_original_counterevidence_and_analogy_are_returned_without_loss(self):
        result = self.recall()['results'][0]
        linked = {r['record']['id']: r['record'] for r in result['linked_records']}
        self.assertEqual(set(linked), {'ev:source', 'ev:challenge', 'hyp:deposit'})
        self.assertEqual(linked['ev:source']['limitations'], ['No market census'])
        self.assertEqual(result['learning']['alternatives'][0]['transfer_limit'], 'Needs buyer consent')
        self.assertTrue(result['refresh_due'])

    def test_null_refresh_date_keeps_event_triggers(self):
        self.model['actions'][0]['learning']['freshness']['recheck_by'] = None
        result = self.recall('action:closed')['results'][0]
        self.assertFalse(result['refresh_due'])
        self.assertEqual(result['learning']['freshness']['recheck_on'], ['Before using mutable terms'])

    def test_limit_order_and_read_only_behavior(self):
        original = copy.deepcopy(self.model)
        result = self.recall(limit=1)
        self.assertTrue(result['truncated'])
        self.assertEqual(result['results'][0]['action_id'], 'action:closed')
        self.assertEqual(result['matching_records'], 2)
        self.assertEqual(self.model, original)

    def test_no_match_is_explicitly_incomplete_retrieval(self):
        result = self.recall('unicorn')
        self.assertEqual(result['results'], [])
        self.assertIn('retrieval gap', result['limits'])
        self.assertEqual(result['learning_records_available'], 2)

    def test_missing_reference_fails_instead_of_omitting_evidence(self):
        del self.index['ev:challenge']
        with self.assertRaisesRegex(ValueError, 'unresolved references'):
            self.recall()

    def test_coverage_is_a_supported_alternative_reference(self):
        self.assertIn('coverage', q.KINDS)
        self.model['actions'][0]['learning']['alternatives'][0]['related_ids'].append('coverage:scope')
        result = self.recall('action:closed')['results'][0]
        self.assertIn('coverage:scope', {r['record']['id'] for r in result['linked_records']})

    def test_exact_linked_ids_whitespace_and_unknown_ids(self):
        self.model['entities'] = [{'id': 'goal:earnings', 'name': 'Human earnings'}]
        self.index['goal:earnings'] = ('entities', self.model['entities'][0])
        self.model['actions'][0]['learning']['alternatives'][0]['related_ids'] += ['goal:earnings', 'coverage:scope']
        for ident in ('ev:source', 'ev:challenge', 'hyp:deposit'):
            with self.subTest(ident=ident):
                self.assertEqual(self.recall(ident)['matching_records'], 2)
                self.assertEqual(self.recall('  ' + ident + '\n'), self.recall(ident))
        for ident in ('goal:earnings', 'coverage:scope', 'action:closed'):
            with self.subTest(ident=ident):
                result = self.recall(ident)
                self.assertEqual([r['action_id'] for r in result['results']], ['action:closed'])
                self.assertEqual(result['results'][0]['matched_terms'], [ident])
        for ident in ('ev:missing', 'hyp:missing', 'action:missing', 'action:unannotated'):
            self.assertEqual(self.recall(ident)['results'], [])

    def test_cli_json_and_bad_arguments(self):
        with patch.object(q, 'load', return_value=(self.model, self.index)):
            _, out = run('--recall', 'cash', '--limit', '1')
        self.assertEqual(json.loads(out)['model_version'], 'test')
        for args in (('--recall', ''), ('--recall', '---'), ('--recall', '_'), ('--recall', 'cash', '--limit', '0'),
                     ('--recall', 'cash', '--limit', '21'), ('--limit', '2'),
                     ('--recall', 'cash', '--open'), ('prefix', '--recall', 'cash')):
            with self.subTest(args=args):
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as result:
                    run(*args)
                self.assertEqual(result.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
