#!/usr/bin/env python3
"""No infrastructure targets: temporary fixture module + loopback refused SSH."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

SOURCE = Path(__file__).resolve().parents[1]
FIXTURE_MODULE = '''#!/usr/bin/python
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.storage_diag import analyze
m = AnsibleModule(argument_spec={"options": {"type": "dict", "default": {}}})
r = {"schema_version": 1, "evidence": {
 "kernel": {"status": "ok", "data": {"text": "sd 9:0:1:7: [sdb] Logical unit not supported"}},
 "config:docker:nova_compute": {"status": "missing", "data": {}}
}, "limitations": ["Synthetic integration fixture, not a real host"]}
r["findings"] = analyze(r)
m.exit_json(changed=False, report=r)
'''


def main():
    with tempfile.TemporaryDirectory(prefix='storage-diag-test-') as temp:
        root = Path(temp)
        project = root / 'project'
        shutil.copytree(SOURCE, project, ignore=shutil.ignore_patterns('artifacts', '__pycache__'))
        (project / 'library/storage_diagnostics.py').write_text(FIXTURE_MODULE)
        inventory = root / 'inventory.ini'
        inventory.write_text('[storage]\n'
                             'unreachable ansible_host=127.0.0.1 ansible_port=1 ansible_user=storage_diag_test '
                             'ansible_ssh_common_args="-o BatchMode=yes -o ConnectTimeout=1 -o ConnectionAttempts=1"\n'
                             'compute_ok ansible_connection=local ansible_python_interpreter=' + sys.executable + '\n'
                             'excluded ansible_connection=local ansible_python_interpreter=' + sys.executable + '\n')
        env = dict(os.environ, ANSIBLE_LOCAL_TEMP=str(root / 'ansible-local'),
                   ANSIBLE_REMOTE_TEMP=str(root / 'ansible-remote'), ANSIBLE_HOST_KEY_CHECKING='False',
                   ANSIBLE_SSH_CONTROL_PATH_DIR=str(root / 'ansible-cp'),
                   ANSIBLE_SSH_ARGS='-F /dev/null -o ControlMaster=no',
                   ANSIBLE_NOCOLOR='1', ANSIBLE_TIMEOUT='2')
        cmd = ['ansible-playbook', '-i', str(inventory), str(project / 'diagnose.yml'),
               '--limit', 'unreachable,compute_ok', '-e', 'storage_diag_become=false']
        result = subprocess.run(cmd + ['--syntax-check'], env=env, capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stdout + result.stderr
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=60)
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)
        runs = list((project / 'artifacts').glob('storage-diag-*'))
        assert len(runs) == 1, runs
        summary = json.loads((runs[0] / 'summary.json').read_text())
        assert set(summary['hosts']) == {'unreachable', 'compute_ok'}, summary
        assert summary['hosts']['unreachable']['status'] == 'unreachable', summary
        assert summary['hosts']['compute_ok']['status'] == 'ok', summary
        assert 'scsi_lun_not_supported' in summary['hosts']['compute_ok']['finding_codes'], summary
        assert 'container_config_missing' in summary['hosts']['compute_ok']['finding_codes'], summary
        assert (runs[0] / 'index.md').exists()
        for path in runs[0].rglob('*'):
            if path.is_file():
                assert path.stat().st_mode & 0o777 == 0o600, path
        before = set((project / 'artifacts').glob('*'))
        checked = subprocess.run(cmd + ['--check'], env=env, capture_output=True, text=True, timeout=30)
        assert checked.returncode != 0, checked.stdout
        assert set((project / 'artifacts').glob('*')) == before, 'check mode created artifacts'
        # Exercise real bundled Ansible module import/validation; invalid timestamp exits BEFORE collection.
        shutil.copy2(SOURCE / 'library/storage_diagnostics.py', project / 'library/storage_diagnostics.py')
        params = root / 'invalid.json'
        params.write_text(json.dumps({'storage_diag_become': False, 'storage_diag_options': {'since': 'bad'}}))
        invalid = subprocess.run(['ansible-playbook', '-i', str(inventory), str(project / 'diagnose.yml'),
                                  '--limit', 'compute_ok', '-e', '@' + str(params)], env=env,
                                 capture_output=True, text=True, timeout=60)
        assert invalid.returncode == 0, invalid.stdout + invalid.stderr
        runs_after = set((project / 'artifacts').glob('*')) - before
        assert len(runs_after) == 1
        invalid_run = runs_after.pop()
        invalid_summary = json.loads((invalid_run / 'summary.json').read_text())
        assert invalid_summary['hosts']['compute_ok']['status'] == 'collector_failed', invalid_summary
        invalid_record = json.loads(next((invalid_run / 'records').glob('*.json')).read_text())
        assert 'ISO-8601' in invalid_record['transport_note'], invalid_record
        print('PASS: syntax; --limit; unreachable-first host; fixture evidence; private files; check-mode; real module packaging/validation')


if __name__ == '__main__':
    main()
