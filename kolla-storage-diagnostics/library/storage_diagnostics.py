#!/usr/bin/python
"""Ansible entrypoint; collection logic is in the bundled module_utils module."""
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.storage_diag import collect
import datetime as dt
import re

DOCUMENTATION = r'''
---
module: storage_diagnostics
short_description: Read-only FC and multipath evidence for Kolla hosts
description: Collect bounded Linux and container evidence without storage mutations.
options:
  options:
    type: dict
    description: Collection options documented in README.md.
author: Local infrastructure tooling
'''


def main():
    module = AnsibleModule(argument_spec={'options': {'type': 'dict', 'default': {}, 'options': {
        'runtime': {'type': 'str', 'default': 'auto', 'choices': ['auto', 'podman', 'docker', 'none']},
        'containers': {'type': 'list', 'elements': 'str', 'default': [
            'multipathd', 'nova_compute', 'cinder_volume', 'cinder_backup', 'glance_api', 'nova_libvirt']},
        'node_config_directory': {'type': 'path', 'default': '/etc/kolla'},
        'log_directory': {'type': 'path', 'default': '/var/log/kolla'},
        'since': {'type': 'str', 'default': ''}, 'until': {'type': 'str', 'default': ''},
        'boot': {'type': 'int', 'default': 0},
        'wwid': {'type': 'str', 'default': ''}, 'volume_id': {'type': 'str', 'default': ''},
        'request_id': {'type': 'str', 'default': ''},
        'command_timeout': {'type': 'int', 'default': 10},
        'command_budget': {'type': 'int', 'default': 180},
        'max_output_bytes': {'type': 'int', 'default': 262144},
        'max_devices': {'type': 'int', 'default': 2048},
        'log_tail_bytes': {'type': 'int', 'default': 1048576},
        'log_lines': {'type': 'int', 'default': 2000},
        'max_log_files': {'type': 'int', 'default': 40},
    }}}, supports_check_mode=True)
    def invalid(message):
        # Only fixed validation messages are surfaced. Never forward raw exceptions/parameters.
        module.fail_json(msg=message, diagnostic_error=message)
    if module.check_mode:
        invalid('Check mode does not collect diagnostic evidence; use --list-hosts for scope review.')
    options = module.params['options']
    bounds = {'command_timeout': (1, 60), 'command_budget': (10, 1800),
              'max_output_bytes': (4096, 4194304), 'max_devices': (1, 16384),
              'log_tail_bytes': (4096, 8388608), 'log_lines': (10, 20000), 'max_log_files': (1, 200)}
    for name, (low, high) in bounds.items():
        if not low <= options[name] <= high:
            invalid('%s must be between %s and %s' % (name, low, high))
    timestamps = {}
    for name in ('since', 'until'):
        if options[name]:
            try:
                timestamp = dt.datetime.fromisoformat(options[name].replace('Z', '+00:00'))
                if timestamp.tzinfo is None:
                    raise ValueError('timezone required')
                timestamps[name] = timestamp
                options[name] = timestamp.astimezone(dt.timezone.utc).isoformat()
            except ValueError:
                invalid('%s must be ISO-8601 with timezone, e.g. 2026-10-14T09:00:00Z' % name)
    if 'since' in timestamps and 'until' in timestamps and timestamps['since'] >= timestamps['until']:
        invalid('since must precede until')
    if options['until'] and not options['since']:
        invalid('Specify since together with until')
    if options['boot'] > 0:
        invalid('boot must be 0 (current) or a negative previous-boot offset')
    if not 1 <= len(options['containers']) <= 32 or any(
            not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', n) for n in options['containers']):
        invalid('containers must contain 1..32 literal container names, without paths or patterns')
    for name in ('node_config_directory', 'log_directory'):
        if not options[name].startswith('/'):
            invalid('%s must be absolute' % name)
    for name in ('wwid', 'volume_id', 'request_id'):
        if len(options[name]) > 256 or '\n' in options[name]:
            invalid('%s must be a single identifier up to 256 characters' % name)
    module.exit_json(changed=False, report=collect(options))


if __name__ == '__main__':
    main()
