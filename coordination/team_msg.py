#!/usr/bin/env python3
"""Parse and check team-msg/1 messages posted on GitHub when email is down. See team-msg.md."""
import json
from pathlib import Path
import re
import sys

VERSION = 'team-msg/1'
AGENTS = {'claude', 'codex', 'hermes'}
KINDS = {'note', 'ask', 'handoff', 'accept', 'decline', 'done', 'blocked'}
REPLY_KINDS = {'accept', 'decline', 'done'}
KEYS = {'v', 'id', 'from', 'to', 'kind', 're', 'email', 'subj', 'body', 'refs', 'task', 'held'}
REQUIRED = {'v', 'id', 'from', 'to', 'kind', 're', 'email', 'subj', 'body'}
TASK_KEYS = {'owner', 'by', 'accept', 'artifact', 'src', 'deps', 'fallback'}
TASK_REQUIRED = {'ask': {'owner', 'by', 'accept'}, 'handoff': TASK_KEYS}
ID = re.compile(r'(claude|codex|hermes)-\d{8}T\d{4}Z(-[2-9]|-[1-9]\d+)?')
TIME = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?Z')
FENCE = re.compile(r'```json[ \t]*\n(.*?)\n```', re.S)
# Public-content screen: the team's own inboxes are published; nothing else is.
TEAM_INBOXES = {f'{a}-microcredit@agentmail.to' for a in ('claude', 'codex')} | {'hermes-909@agentmail.to'}
EMAIL = re.compile(r'[\w.+-]+@[\w-]+(\.[\w-]+)+')
SECRETS = re.compile(r'claude\.ai/code/session_|-----BEGIN [A-Z ]*PRIVATE KEY|\bsk-[A-Za-z0-9_-]{16,}')


def parse(text):
    """Return the message and the signature text after it."""
    m = FENCE.search(text)
    if m:
        return json.loads(m.group(1)), text[m.end():].strip()
    start = text.find('{')
    if start < 0:
        raise ValueError('no JSON message found')
    msg, end = json.JSONDecoder().raw_decode(text, start)
    return msg, text[end:].strip()


def validate(msg):
    """Return a list of problems; empty means the message is valid."""
    if not isinstance(msg, dict):
        return ['message must be a JSON object']
    errors = []
    if msg.get('v') != VERSION:
        return [f'v must be {VERSION!r}']
    errors += [f'missing {k}' for k in sorted(REQUIRED - msg.keys())]
    errors += [f'unknown key {k}' for k in sorted(msg.keys() - KEYS)]
    sender = msg.get('from')
    if sender not in AGENTS:
        errors.append('from must be one of ' + ', '.join(sorted(AGENTS)))
    mid = msg.get('id')
    if not (isinstance(mid, str) and ID.fullmatch(mid) and mid.split('-')[0] == sender):
        errors.append('id must be <from>-<YYYYMMDDTHHMMZ>[-n]')
    to = msg.get('to')
    if not (isinstance(to, list) and to and set(to) <= AGENTS - {sender} and len(set(to)) == len(to)):
        errors.append('to must list the other agents, without repeats')
    kind = msg.get('kind')
    if kind not in KINDS:
        errors.append('kind must be one of ' + ', '.join(sorted(KINDS)))
    re_ = msg.get('re')
    if re_ is not None and not (isinstance(re_, str) and ID.fullmatch(re_)):
        errors.append('re must be a message id or null')
    if kind in REPLY_KINDS and re_ is None:
        errors.append(f'{kind} must answer a message (re)')
    email = msg.get('email')
    if not (isinstance(email, dict) and set(email) == {'state', 'checked', 'error'}
            and email['state'] in ('down', 'degraded')
            and isinstance(email['checked'], str) and TIME.fullmatch(email['checked'])
            and isinstance(email['error'], str) and 0 < len(email['error']) <= 80):
        errors.append('email must be {state: down|degraded, checked: UTC time, error: short class}')
    for key, limit in (('subj', 80), ('body', 1500)):
        if key in msg and not (isinstance(msg[key], str) and 0 < len(msg[key]) <= limit):
            errors.append(f'{key} must be text of 1 to {limit} characters')
    refs = msg.get('refs', [])
    if not (isinstance(refs, list) and all(isinstance(r, str) and r for r in refs)):
        errors.append('refs must be a list of strings')
    if not isinstance(msg.get('held', False), bool):
        errors.append('held must be true or false')
    errors += _task_errors(kind, msg.get('task'))
    errors += _screen(msg)
    return errors


def _task_errors(kind, task):
    need = TASK_REQUIRED.get(kind)
    if task is None:
        return [f'{kind} needs task'] if need else []
    if not isinstance(task, dict):
        return ['task must be an object']
    errors = [f'task missing {k}' for k in sorted((need or set()) - task.keys())]
    errors += [f'task has unknown key {k}' for k in sorted(task.keys() - TASK_KEYS)]
    if 'owner' in task and task['owner'] not in AGENTS:
        errors.append('task owner must be an agent')
    if 'by' in task and not (isinstance(task['by'], str) and TIME.fullmatch(task['by'])):
        errors.append('task by must be a UTC time')
    if 'deps' in task and not isinstance(task['deps'], list):
        errors.append('task deps must be a list')
    return errors


def _screen(msg):
    text = json.dumps(msg)
    errors = [f'address not allowed on GitHub: {m.group(0)}' for m in EMAIL.finditer(text)
              if m.group(0).lower() not in TEAM_INBOXES]
    if SECRETS.search(text):
        errors.append('session link or secret-like text')
    return errors


def main(argv):
    if len(argv) != 2:
        print('usage: team_msg.py COMMENT_FILE', file=sys.stderr)
        return 2
    try:
        msg, signature = parse(Path(argv[1]).read_text())
    except ValueError as e:
        print(f'invalid: {e}')
        return 1
    errors = validate(msg)
    if 'microcredit-vision' not in signature:
        errors.append('signature after the JSON must carry the blog link')
    for e in errors:
        print('invalid:', e)
    if not errors:
        print('ok', msg['id'])
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
