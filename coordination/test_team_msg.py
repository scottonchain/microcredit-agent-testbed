"""Check the team-msg/1 parser and validator, including the example in team-msg.md."""
import copy
from pathlib import Path
import unittest

if __package__:
    from .team_msg import FENCE, parse, validate
else:
    from team_msg import FENCE, parse, validate

DOC = Path(__file__).with_name('team-msg.md').read_text()
SIGNATURE = 'Claude (AI agent). Credit Among Strangers: https://github.com/scottonchain/microcredit-vision'


class TeamMsgTests(unittest.TestCase):
    def setUp(self):
        self.msg, _ = parse(FENCE.search(DOC).group(0))

    def errors(self, **changes):
        msg = copy.deepcopy(self.msg)
        for key, value in changes.items():
            if value is None and key != 're':
                msg.pop(key, None)
            else:
                msg[key] = value
        return validate(msg)

    def test_documented_example_is_valid(self):
        self.assertEqual(validate(self.msg), [])

    def test_parse_fenced_and_bare(self):
        block = FENCE.search(DOC).group(0)
        msg, sig = parse(block + '\n\n' + SIGNATURE)
        self.assertEqual((msg['id'], sig), (self.msg['id'], SIGNATURE))
        bare = block.split('\n', 1)[1].rsplit('```', 1)[0]
        msg, sig = parse(bare + '-- \n' + SIGNATURE)
        self.assertEqual(msg, self.msg)
        self.assertTrue(sig.endswith('microcredit-vision'))

    def test_unknown_version_is_rejected_outright(self):
        self.assertEqual(self.errors(v='team-msg/2'), ["v must be 'team-msg/1'"])

    def test_sender_and_recipients(self):
        self.assertTrue(self.errors(id='codex-20261008T1612Z'))
        self.assertTrue(self.errors(to=['claude']))
        self.assertTrue(self.errors(to=[]))
        self.assertTrue(self.errors(to=['codex', 'codex']))

    def test_replies_need_re(self):
        self.assertTrue(self.errors(kind='accept', task=None))
        self.assertEqual(self.errors(kind='accept', task=None, re='codex-20261008T1700Z'), [])

    def test_handoff_needs_every_handoff_field(self):
        task = dict(self.msg['task'])
        del task['fallback']
        self.assertIn('task missing fallback', self.errors(task=task))
        self.assertEqual(self.errors(kind='ask', task={k: task[k] for k in ('owner', 'by', 'accept')}), [])

    def test_email_reason_is_required(self):
        self.assertIn('missing email', self.errors(email=None))
        self.assertTrue(self.errors(email={'state': 'up', 'checked': '2026-10-08T16:10Z', 'error': 'x'}))

    def test_privacy_screen(self):
        self.assertTrue(self.errors(body='Write to someone@example.org about it'))
        self.assertTrue(self.errors(body='see claude.ai/code/' + 'session_' + 'abc'))
        self.assertEqual(self.errors(body='Reply to codex-microcredit@agentmail.to when it is back'), [])

    def test_limits(self):
        self.assertTrue(self.errors(subj='x' * 81))
        self.assertTrue(self.errors(body='x' * 1501))
        self.assertTrue(self.errors(extra=1))


if __name__ == '__main__':
    unittest.main()
