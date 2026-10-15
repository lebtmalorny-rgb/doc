import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
import warnings
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'module_utils'))
from storage_diag import (Runner, analyze, config_projection, redact,
                          collect_topology, collect_processes, collect, docker_socket_owner)
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from render_report import render


class DiagnosticsTests(unittest.TestCase):
    def test_secrets_removed_but_volume_correlation_preserved(self):
        value = ('password=secret42 auth_password = "two words"\n'
                 'Authorization: Bearer TOKEN123\n'
                 '{"connection_info": {"auth_password": "chap-secret"}, '
                 '"volume_id": "11111111-2222-3333-4444-555555555555"}\n'
                 'transport_url=rabbit://alice:pass@host:5672/vhost\n'
                 'X-Auth-Token: other-token')
        cleaned = redact(value)
        for secret in ('secret42', 'two words', 'TOKEN123', 'chap-secret', 'pass@', 'other-token'):
            self.assertNotIn(secret, cleaned)
        self.assertIn('11111111-2222-3333-4444-555555555555', cleaned)

    def test_service_config_whitelist_excludes_credentials_and_non_storage_options(self):
        raw = ('[DEFAULT]\ntransport_url=rabbit://user:pass@mq\n'
               'enabled_backends=dorado\n[libvirt]\nvolume_use_multipath=true\n'
               '[dorado]\nvolume_driver=cinder.volume.drivers.huawei.huawei_driver.HuaweiFCDriver\n'
               'san_password=top-secret\nuse_multipath_for_image_xfer=true\n'
               '[backend1]\nstore=cinder\ncinder_use_multipath=true\n')
        projected = config_projection(raw)
        self.assertEqual(projected['libvirt']['volume_use_multipath'], 'true')
        self.assertEqual(projected['backend1']['store'], 'cinder')
        self.assertNotIn('secret', json.dumps(projected))
        self.assertNotIn('transport_url', json.dumps(projected))

    def test_escaped_quotes_do_not_leak_secret_suffixes(self):
        samples = [json.dumps({'auth_password': 'prefix"SECRET_TAIL'}),
                   "{'password': 'prefix\\'SECRET_TAIL'}", '{"password": "unfinished-secret']
        for sample in samples:
            cleaned = redact(sample)
            self.assertNotIn('SECRET_TAIL', cleaned)
            self.assertNotIn('unfinished-secret', cleaned)

    def test_long_log_token_does_not_make_redaction_quadratic(self):
        script = ('import sys; sys.path.insert(0, ' + repr(str(Path(__file__).resolve().parents[1] / 'module_utils')) +
                  '); from storage_diag import redact; print(len(redact("a" * 500000)))')
        result = Runner(timeout=2, max_bytes=128, budget=4).run([sys.executable, '-c', script])
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['stdout'].strip(), '500000')

    def test_distinct_errors_do_not_prove_mapping_removed(self):
        report = {'evidence': {
            'kernel': {'status': 'ok', 'data': {'text': 'sd 9:0:1:7: [sdb] Logical unit not supported'}},
            'log:nova': {'status': 'ok', 'data': {'text': '/etc/multipath.conf does not exist, blacklisting all devices'}},
        }}
        findings = analyze(report)
        codes = {f['code'] for f in findings}
        self.assertIn('scsi_lun_not_supported', codes)
        self.assertIn('client_config_error', codes)
        self.assertNotIn('mapping_removed', codes)
        item = next(f for f in findings if f['code'] == 'scsi_lun_not_supported')
        self.assertEqual(item['kind'], 'observation')
        self.assertEqual(item['evidence'], ['kernel'])

    def test_empty_or_failed_checks_never_produce_healthy_verdict(self):
        findings = analyze({'evidence': {'kernel': {'status': 'timeout', 'data': {}}}})
        self.assertIn('incomplete_collection', {f['code'] for f in findings})
        self.assertNotIn('healthy', json.dumps(findings))

    def test_staged_runtime_config_mismatch_is_observation(self):
        findings = analyze({'evidence': {
            'config:staged:nova_compute': {'status': 'ok', 'data': {'sha256': 'aaa', 'complete': True}},
            'config:docker:nova_compute': {'status': 'ok', 'data': {'sha256': 'bbb', 'complete': True}},
        }})
        match = next(f for f in findings if f['code'] == 'config_delivery_mismatch')
        self.assertEqual(match['kind'], 'observation')

    def test_truncated_configs_not_compared_as_equal_or_different(self):
        findings = analyze({'evidence': {
            'config:staged:nova_compute': {'status': 'ok', 'data': {'sha256': 'aaa', 'complete': False}},
            'config:docker:nova_compute': {'status': 'ok', 'data': {'sha256': 'bbb', 'complete': True}},
        }})
        self.assertNotIn('config_delivery_mismatch', {f['code'] for f in findings})

    def test_runner_timeout_and_output_cap(self):
        runner = Runner(timeout=0.2, max_bytes=128, budget=4)
        result = runner.run([sys.executable, '-c', 'import time; print("started", flush=True); time.sleep(10)'])
        self.assertEqual(result['status'], 'timeout')
        self.assertIn('started', result['stdout'])
        result = runner.run([sys.executable, '-c', 'print("x" * 1000000)'])
        self.assertEqual(result['status'], 'ok')
        self.assertTrue(result['truncated'])
        self.assertLessEqual(len(result['stdout']), 128)

    def test_runner_missing_command_and_exhausted_budget_are_explicit(self):
        runner = Runner(timeout=1, max_bytes=128, budget=2)
        self.assertEqual(runner.run(['/nonexistent/storage-diag'])['status'], 'missing')
        runner.deadline = time.monotonic() - 1
        self.assertEqual(runner.run([sys.executable, '-c', 'pass'])['status'], 'skipped')

    def test_timeout_still_applies_after_child_closes_both_output_streams(self):
        runner = Runner(timeout=0.1, max_bytes=128, budget=2)
        result = runner.run([sys.executable, '-c',
                             'import os,time; os.close(1); os.close(2); time.sleep(1)'])
        self.assertEqual(result['status'], 'timeout')
        self.assertLess(result['duration_seconds'], 0.8)

    def test_delayed_kill_delivery_does_not_block_reaping_indefinitely(self):
        runner = Runner(timeout=0.05, max_bytes=128, budget=1)
        pids = []
        real_killpg = os.killpg
        try:
            with warnings.catch_warnings(record=True):
                # An intentionally un-reaped Popen emits ResourceWarning; cleanup below reaps it.
                with patch('storage_diag.os.killpg', side_effect=lambda pid, sig: pids.append(pid)):
                    result = runner.run([sys.executable, '-c', 'import time; time.sleep(0.8)'])
            self.assertEqual(result['status'], 'timeout')
            self.assertTrue(result.get('reap_pending'))
            self.assertLess(result['duration_seconds'], 0.6)
        finally:
            for pid in pids:
                try:
                    real_killpg(pid, 9)
                    os.waitpid(pid, 0)
                except (ProcessLookupError, ChildProcessError):
                    pass

    def test_active_host_socket_with_container_daemon_is_flagged(self):
        findings = analyze({'evidence': {
            'systemd': {'status': 'ok', 'data': {'stdout': 'Id=multipathd.socket\nActiveState=active\n'}},
            'container:podman:multipathd': {'status': 'ok', 'data': {'state': {'Running': True}}},
        }})
        self.assertIn('host_socket_with_container_daemon', {f['code'] for f in findings})

    def test_missing_kernel_tool_is_incomplete_not_success(self):
        findings = analyze({'evidence': {'kernel': {'status': 'missing', 'data': {}}}})
        self.assertIn('incomplete_collection', {f['code'] for f in findings})

    def test_sysfs_preserves_hctl_wwid_holders_and_fc_port(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            def put(path, value):
                p = root / path
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(value)
            scsi = root / 'sys/devices/host9/target9:0:1/9:0:1:7'
            scsi.mkdir(parents=True)
            put('sys/class/block/sdb/dev', '8:16')
            (root / 'sys/class/block/sdb/device').symlink_to(scsi)
            put('sys/devices/host9/target9:0:1/9:0:1:7/wwid', 'naa.60001234')
            put('sys/devices/host9/target9:0:1/9:0:1:7/state', 'running')
            (root / 'sys/class/block/sdb/holders/dm-2').mkdir(parents=True)
            put('sys/class/fc_host/host9/port_name', '0x1000000123456789')
            put('sys/class/fc_transport/target9:0:1/port_name', '0x2000000123456789')
            put('run/udev/data/b8:16', 'E:ID_WWN=0x60001234\nE:UNRELATED_SECRET=ignored\n')
            data = collect_topology(root, 100)
            disk = data['block'][0]
            self.assertEqual(disk['hctl'], '9:0:1:7')
            self.assertEqual(disk['wwid'], 'naa.60001234')
            self.assertEqual(disk['holders'], ['dm-2'])
            self.assertEqual(disk['initiator_wwpn'], '0x1000000123456789')
            self.assertEqual(disk['target_wwpn'], '0x2000000123456789')
            self.assertNotIn('UNRELATED_SECRET', json.dumps(data))

    def test_process_collection_omits_commandline_credentials(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            p = root / 'proc/123'
            p.mkdir(parents=True)
            (p / 'comm').write_text('multipathd\n')
            (p / 'cmdline').write_text('multipathd --password supersecret')
            (p / 'cgroup').write_text('0::/system.slice/multipathd.service\n')
            data = collect_processes(root, 100)
            self.assertEqual(data['multipathd'][0]['pid'], 123)
            self.assertNotIn('supersecret', json.dumps(data))

    def test_unrelated_dockerd_cannot_authorize_access_to_host_socket(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'proc/net').mkdir(parents=True)
            (root / 'proc/net/unix').write_text(
                'Num RefCount Protocol Flags Type St Inode Path\n'
                '000: 00000002 00000000 00010000 0001 01 111 /var/run/docker.sock\n')
            (root / 'proc/123/fd').mkdir(parents=True)
            (root / 'proc/123/fd/3').symlink_to('socket:[222]')
            (root / 'var/run').mkdir(parents=True)
            (root / 'var/run/docker.sock').touch()
            (root / 'proc/123/root').symlink_to(root)
            result = docker_socket_owner([{'pid': 123}], root)
            self.assertFalse(result['verified'])

    def test_matching_socket_fd_and_host_filesystem_identity_allow_docker(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'var/run').mkdir(parents=True)
            (root / 'var/run/docker.sock').touch()
            (root / 'proc/net').mkdir(parents=True)
            (root / 'proc/net/unix').write_text(
                'Num RefCount Protocol Flags Type St Inode Path\n'
                '000: 00000002 00000000 00010000 0001 01 111 /var/run/docker.sock\n')
            (root / 'proc/123/fd').mkdir(parents=True)
            (root / 'proc/123/fd/3').symlink_to('socket:[111]')
            (root / 'proc/123/root').symlink_to(root)
            result = docker_socket_owner([{'pid': 123}], root)
            self.assertTrue(result['verified'])
            self.assertEqual(result['pid'], 123)

    def test_full_collection_projects_inspect_and_service_secrets_before_output(self):
        calls = []
        def run(runner, argv):
            calls.append(argv)
            output = ''
            if argv[0] == 'journalctl':
                self.assertEqual(argv[argv.index('--since') + 1], '2026-10-14 09:00:00.000000 UTC')
                self.assertEqual(argv[argv.index('--until') + 1], '2026-10-14 10:00:00.000000 UTC')
            if argv[0] == 'docker':
                action = argv[3]
                self.assertIn(action, ('ps', 'inspect', 'exec', 'logs'))
                if action == 'ps':
                    output = 'nova_compute\nmultipathd\n'
                elif action == 'inspect':
                    output = json.dumps([{'State': {'Running': True, 'Pid': 123},
                        'Config': {'Image': 'kolla:test', 'Env': ['PASSWORD=inspect-secret']}, 'Mounts': []}])
                elif action == 'exec':
                    command = argv[9:]
                    self.assertIn(command[0], ('cat', '/var/lib/kolla/venv/bin/python', 'python3'))
                    if command == ['cat', '/etc/multipath.conf']:
                        output = 'defaults {\n}\n'
                    elif command == ['cat', '/etc/nova/nova.conf']:
                        output = '[libvirt]\nvolume_use_multipath=true\n[keystone_authtoken]\npassword=config-secret\n'
                    else:
                        output = '{}'
                elif action == 'logs':
                    output = 'os_brick password=log-secret Logical unit not supported'
            return {'status': 'ok', 'stdout': output, 'stderr': '', 'rc': 0, 'truncated': False}
        with tempfile.TemporaryDirectory() as temp, \
                patch('storage_diag.platform.system', return_value='Linux'), \
                patch('storage_diag.collect_topology', return_value={'block': [], 'fc': {}}), \
                patch('storage_diag.collect_processes', return_value={'dockerd': [{'pid': 1}], 'multipathd': []}), \
                patch('storage_diag.docker_socket_owner', return_value={'verified': True, 'pid': 1}), \
                patch('storage_diag.read_file', return_value={'status': 'missing', 'data': {}}), \
                patch('storage_diag.shutil.which', side_effect=lambda name: '/usr/bin/docker' if name == 'docker' else None), \
                patch.object(Runner, 'run', run):
            report = collect({'runtime': 'docker', 'containers': ['nova_compute', 'multipathd'],
                              'node_config_directory': temp, 'log_directory': temp,
                              'since': '2026-10-14T09:00:00+00:00', 'until': '2026-10-14T10:00:00+00:00'})
        serialized = json.dumps(report)
        for secret in ('inspect-secret', 'config-secret', 'log-secret'):
            self.assertNotIn(secret, serialized)
        settings = report['evidence']['service_settings:docker:nova_compute']['data']['settings']
        self.assertEqual(settings['libvirt']['volume_use_multipath'], 'true')
        self.assertIn('scsi_lun_not_supported', {f['code'] for f in report['findings']})
        self.assertFalse(any(argv[0] in ('multipath', 'multipathd', 'virsh') for argv in calls))

    def test_report_includes_manifest_hosts_even_when_record_absent(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'records').mkdir()
            (root / 'manifest.json').write_text(json.dumps({'hosts': ['compute03', '../ctrl01']}))
            (root / 'records/one.json').write_text(json.dumps({
                'host': 'compute03', 'status': 'ok', 'report': {
                    'schema_version': 1, 'evidence': {}, 'findings': [], 'limitations': []}}))
            render(root)
            summary = json.loads((root / 'summary.json').read_text())
            self.assertEqual(summary['hosts']['../ctrl01']['status'], 'missing_record')
            self.assertIn('compute03', (root / 'index.md').read_text())
            self.assertEqual(len(list((root / 'hosts').glob('*.md'))), 2)
            self.assertEqual(os.stat(root / 'summary.json').st_mode & 0o777, 0o600)


if __name__ == '__main__':
    unittest.main()
