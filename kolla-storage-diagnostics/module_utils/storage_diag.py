"""Bounded, read-only Linux/Kolla storage evidence. Python >= 3.8, stdlib only."""
import configparser
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import selectors
import shutil
import signal
import socket
import subprocess
import time


SECRET_KEY = (r'(?:[\w.-]{0,128}(?:password|passwd|secret|token)[\w.-]{0,64}|'
              r'authorization|auth_key|access_key|private_key)')
CONFIG_KEYS = frozenset((
    'volume_use_multipath', 'volume_enforce_multipath',
    'use_multipath_for_image_xfer', 'enforce_multipath_for_image_xfer',
    'cinder_use_multipath', 'cinder_enforce_multipath', 'enabled_backends',
    'enabled_import_methods', 'default_backend', 'default_store', 'stores',
    'store', 'volume_driver', 'volume_backend_name', 'image_volume_cache_enabled',
))
SIGNALS = re.compile(
    r'multipath|os[_-]brick|fibre.?channel|dorado|huawei|logical unit not supported|'
    r'I/O error|buffer I/O|blk_update_request|scsi.{0,300}(?:error|sense|offline|reject)|'
    r'\b(?:attach|detach|unmap|terminate_connection|initialize_connection)\b', re.I)


def utcnow():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def redact(value):
    """Best-effort masking; this is not an anonymizer or a security boundary."""
    if isinstance(value, dict):
        return {k: ('<redacted>' if re.fullmatch(SECRET_KEY, str(k), re.I)
                    else redact(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    if not isinstance(value, str):
        return value
    value = re.sub(r'(?im)\b(Authorization|X-Auth-Token)\s*:\s*[^\r\n]+',
                   r'\1: <redacted>', value)
    value = re.sub(r'(?i)(?<![a-z0-9+.-])([a-z][a-z0-9+.-]{0,31}://[^\s/@:]+:)[^\s/@]+@',
                   r'\1<redacted>@', value)
    # Quoted JSON/Python/INI values, then unquoted assignments.
    pattern = r'(?i)(?<![\w.-])([\"\x27]?' + SECRET_KEY + r'[\"\x27]?\s*[:=]\s*)'
    # Escape-aware quotes. End-of-line branch also masks values truncated by the byte cap.
    quoted = r'(?:"(?:\\.|[^"\\\r\n])*(?:"|$)|\x27(?:\\.|[^\x27\\\r\n])*(?:\x27|$))'
    value = re.sub(pattern + quoted, r'\1"<redacted>"', value, flags=re.M)
    value = re.sub(pattern + r'(?![\"\x27])[^\s,;}]+', r'\1<redacted>', value)
    return value


def config_projection(text):
    parser = configparser.ConfigParser(interpolation=None, strict=False)
    parser.read_string(text)
    result = {}
    for section in ['DEFAULT'] + parser.sections():
        values = parser.defaults() if section == 'DEFAULT' else parser[section]
        selected = {k: values[k] for k in CONFIG_KEYS if k in values}
        if selected:
            result[section] = selected
    return result


class Runner:
    """No shell. Drain both pipes, retaining only a bounded prefix per stream."""
    def __init__(self, timeout=10, max_bytes=262144, budget=180):
        self.timeout = timeout
        self.max_bytes = max_bytes
        self.deadline = time.monotonic() + budget

    def run(self, argv):
        start = time.monotonic()
        result = {'argv': argv, 'stdout': '', 'stderr': '', 'rc': None,
                  'status': 'skipped', 'truncated': False}
        remaining = min(self.timeout, self.deadline - start)
        if remaining <= 0:
            result['reason'] = 'command_time_budget_exhausted'
            return result
        env = dict(os.environ, LC_ALL='C', LANG='C')
        try:
            proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    stdin=subprocess.DEVNULL, env=env, start_new_session=True)
        except FileNotFoundError:
            result['status'] = 'missing'
            return result
        except OSError as exc:
            result.update(status='error', stderr=str(exc))
            return result
        buffers = {'stdout': bytearray(), 'stderr': bytearray()}
        timed_out = False
        with selectors.DefaultSelector() as selector:
            selector.register(proc.stdout, selectors.EVENT_READ, 'stdout')
            selector.register(proc.stderr, selectors.EVENT_READ, 'stderr')
            while selector.get_map() or proc.poll() is None:
                if time.monotonic() - start >= remaining:
                    timed_out = True
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    break
                for key, _ in selector.select(timeout=min(0.1, remaining)):
                    chunk = os.read(key.fileobj.fileno(), 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    buf = buffers[key.data]
                    available = max(0, self.max_bytes - len(buf))
                    buf.extend(chunk[:available])
                    result['truncated'] |= len(chunk) > available
        proc.stdout.close()
        proc.stderr.close()
        try:
            proc.wait(timeout=0.2)
        except subprocess.TimeoutExpired:
            result['reap_pending'] = True
        result.update(rc=proc.returncode, status='timeout' if timed_out else
                      ('ok' if proc.returncode == 0 else 'error'),
                      duration_seconds=round(time.monotonic() - start, 3))
        result.update({k: bytes(v).decode('utf-8', 'replace') for k, v in buffers.items()})
        return result


def read_file(path, limit=262144, tail=False):
    try:
        with open(path, 'rb') as stream:
            if tail:
                stream.seek(0, 2)
                size = stream.tell()
                stream.seek(max(0, size - limit))
                data = stream.read(limit)
                truncated = size > limit
            else:
                data = stream.read(limit + 1)
                truncated = len(data) > limit
                data = data[:limit]
        return {'status': 'ok', 'data': {'text': data.decode('utf-8', 'replace'),
                'sha256': hashlib.sha256(data).hexdigest() if not truncated else None,
                'complete': not truncated, 'truncated': truncated, 'path': str(path)}}
    except FileNotFoundError:
        return {'status': 'missing', 'data': {'path': str(path)}}
    except OSError as exc:
        return {'status': 'error', 'data': {'path': str(path), 'error': str(exc)}}


def small(path):
    item = read_file(path, 8192)
    if item['status'] == 'ok':
        return item['data']['text'].strip()
    return None


def names(path):
    try:
        return sorted(p.name for p in path.iterdir())
    except OSError:
        return []


def collect_topology(root=Path('/'), max_devices=2048):
    root = Path(root)
    block_root = root / 'sys/class/block'
    candidates = [n for n in names(block_root) if re.fullmatch(r'sd[a-z]+|dm-\d+', n)]
    blocks = []
    for name in candidates[:max_devices]:
        p = block_root / name
        device = p / 'device'
        hctl = device.resolve().name if device.exists() else None
        if not re.fullmatch(r'\d+:\d+:\d+:\d+', hctl or ''):
            hctl = None
        entry = {'name': name, 'major_minor': small(p / 'dev'), 'hctl': hctl,
                 'holders': names(p / 'holders'), 'slaves': names(p / 'slaves')}
        for key in ('wwid', 'state', 'vendor', 'model', 'rev', 'timeout'):
            entry[key] = small(device / key)
        for key in ('name', 'uuid', 'suspended'):
            entry['dm_' + key] = small(p / 'dm' / key)
        entry['size_sectors'] = small(p / 'size')
        if hctl:
            entry['initiator_wwpn'] = small(root / 'sys/class/fc_host' /
                                           ('host' + hctl.split(':')[0]) / 'port_name')
            entry['target_wwpn'] = small(root / 'sys/class/fc_transport' /
                                        ('target' + hctl.rsplit(':', 1)[0]) / 'port_name')
        udev_path = root / 'run/udev/data' / ('b' + (entry['major_minor'] or 'unknown'))
        udev = read_file(udev_path, 65536)
        entry['udev_status'] = udev['status']
        entry['udev'] = {}
        if udev['status'] == 'ok':
            for line in udev['data']['text'].splitlines():
                if line.startswith('E:') and '=' in line:
                    key, value = line[2:].split('=', 1)
                    if key in ('ID_WWN', 'ID_WWN_WITH_EXTENSION', 'ID_SERIAL', 'ID_SERIAL_SHORT',
                               'ID_PATH', 'DM_UUID', 'DM_NAME', 'DM_MULTIPATH_DEVICE_PATH'):
                        entry['udev'][key] = value
        blocks.append(entry)
    fc = {}
    for cls, fields in (
            ('fc_host', ('port_name', 'node_name', 'port_state', 'speed', 'symbolic_name')),
            ('fc_transport', ('port_name', 'node_name')),
            ('fc_remote_ports', ('port_name', 'node_name', 'port_state', 'roles'))):
        base = root / 'sys/class' / cls
        candidates_fc = names(base)
        fc[cls] = [{'name': n, **{k: small(base / n / k) for k in fields}}
                   for n in candidates_fc[:max_devices]]
        fc[cls + '_truncated'] = len(candidates_fc) > max_devices
    return {'block': blocks, 'fc': fc, 'block_total': len(candidates),
            'truncated': len(candidates) > max_devices,
            'sysfs_present': block_root.is_dir(),
            'note': 'Current snapshot; historic sdX names may have been reused. Null means unavailable.'}


def collect_processes(root=Path('/'), max_processes=32768):
    proc = Path(root) / 'proc'
    result = {'multipathd': [], 'qemu': [], 'dockerd': [], 'truncated': False}
    pids = [p for p in names(proc) if p.isdigit()]
    result['truncated'] = len(pids) > max_processes
    for pid in pids[:max_processes]:
        p = proc / pid
        comm = small(p / 'comm')
        group = ('multipathd' if comm == 'multipathd' else 'dockerd' if comm == 'dockerd'
                 else 'qemu' if comm and ('qemu' in comm or comm == 'kvm') else None)
        if not group:
            continue
        entry = {'pid': int(pid), 'comm': comm, 'cgroup': small(p / 'cgroup')}
        for namespace in ('mnt', 'net', 'pid'):
            try:
                entry[namespace + '_namespace'] = os.readlink(p / 'ns' / namespace)
            except OSError:
                entry[namespace + '_namespace'] = None
        if group == 'qemu':
            fd_names = names(p / 'fd')
            entry['fd_truncated'] = len(fd_names) > 4096
            entry['block_candidates'] = []
            entry['fd_readable'] = os.access(p / 'fd', os.R_OK | os.X_OK)
            for fd in fd_names[:4096]:
                try:
                    target = os.readlink(p / 'fd' / fd)
                    if target.startswith('/dev/'):
                        entry['block_candidates'].append({'fd': fd, 'path': target})
                except OSError:
                    pass
        result[group].append(entry)
    result['note'] = 'No cmdline/environment collected. Open FD snapshot is not proof of exclusive ownership.'
    return result


def docker_socket_owner(daemons, root=Path('/')):
    """Fail closed unless an existing dockerd holds the specific host socket.

    A visible daemon alone can be DinD or another instance. /proc/net/unix
    identifies listening kernel socket inodes; /proc/PID/fd proves ownership;
    /proc/PID/root prevents confusing the same pathname in another mount tree.
    This remains a point-in-time observation, not a lock against daemon exit.
    """
    root = Path(root)
    result = {'verified': False, 'reason': 'No verified dockerd owner of the host Docker socket'}
    sockets = read_file(root / 'proc/net/unix', 1048576)
    if sockets['status'] != 'ok' or not sockets['data']['complete']:
        return result
    host_path = root / 'var/run/docker.sock'
    try:
        host_stat = host_path.stat()
        aliases = {'/var/run/docker.sock', '/run/docker.sock'}
        inodes = set()
        for line in sockets['data']['text'].splitlines()[1:]:
            fields = line.split(maxsplit=7)
            if len(fields) == 8 and fields[7] in aliases and int(fields[3], 16) & 0x10000:
                inodes.add(fields[6])
        for daemon in daemons:
            proc = root / 'proc' / str(daemon['pid'])
            daemon_stat = (proc / 'root/var/run/docker.sock').stat()
            if (host_stat.st_dev, host_stat.st_ino) != (daemon_stat.st_dev, daemon_stat.st_ino):
                continue
            for fd in names(proc / 'fd')[:4096]:
                try:
                    target = os.readlink(proc / 'fd' / fd)
                except OSError:
                    continue
                if target.startswith('socket:[') and target[8:-1] in inodes:
                    return {'verified': True, 'pid': daemon['pid'], 'socket': '/var/run/docker.sock',
                            'reason': 'Matching listening socket FD and filesystem identity'}
    except (OSError, ValueError):
        pass
    return result


def excerpt(text, identifiers=(), max_lines=2000, context=2):
    lines = text.splitlines()
    wanted = set()
    for i, line in enumerate(lines):
        if SIGNALS.search(line) or any(token and token in line for token in identifiers):
            wanted.update(range(max(0, i - context), min(len(lines), i + context + 1)))
    indices = sorted(wanted)
    # Most recent matching context is more useful for an incident than earliest.
    selected = indices[-max_lines:]
    return {'text': '\n'.join(lines[i] for i in selected),
            'matched_context_lines': len(indices), 'excerpt_truncated': len(indices) > max_lines}


def analyze(report):
    evidence = report.get('evidence', {})
    findings = []
    def add(code, title, refs, next_step, kind='observation'):
        findings.append({'code': code, 'kind': kind, 'title': title,
                         'evidence': refs, 'next_step': next_step})
    rules = (
        ('scsi_lun_not_supported', r'Logical unit not supported',
         'SCSI сообщает: адресуемый LUN не поддерживается через этот путь.',
         'Сопоставить время, H:C:T:L, WWID, WWPN и Host LUN ID с mapping/audit Dorado. '
         'Неверный mapping и оставшийся после detach путь — разные гипотезы; сообщение не выбирает одну.'),
        ('client_config_error', r'multipath\.conf.{0,100}(?:does not exist|No such file)|blacklisting all devices',
         'Есть сообщение об отсутствующем конфиге / blacklist всех устройств.',
         'Определить процесс/контейнер автора, проверить его /etc/multipath.conf и цепочку доставки Kolla. '
         'Это не объясняет SCSI 25/00 автоматически.'),
        ('io_error', r'I/O error|blk_update_request.*error|Buffer I/O',
         'В собранном фрагменте есть ошибки I/O.',
         'Установить WWID и потребителя; сверить живые пути и время ошибки. Не удалять карту действующего тома.'),
        ('detach_error', r'(?:disconnect|detach|terminate_connection).{0,200}(?:fail|error|exception)|'
                         r'(?:fail|error|exception).{0,200}(?:disconnect|detach|terminate_connection)',
         'Найдены строки об ошибках отключения тома.',
         'По request_id/volume UUID собрать порядок os-brick cleanup и Huawei unmap; '
         'проверить всех потребителей, включая image-transfer/backup/Glance.'),
    )
    for code, pattern, title, next_step in rules:
        refs = [k for k, v in evidence.items() if
                (k.startswith('log:') or k in ('kernel', 'service_journal')) and
                re.search(pattern, v.get('data', {}).get('text', '') or
                          v.get('data', {}).get('stdout', ''), re.I)]
        if refs:
            add(code, title, refs, next_step)
    topology = evidence.get('topology', {}).get('data', {})
    bad = [b['name'] for b in topology.get('block', []) if b.get('state') in
           ('offline', 'blocked', 'transport-offline', 'quiesce')]
    if bad:
        add('scsi_path_state', 'Пути в нерабочем/приостановленном состоянии: ' + ', '.join(bad), ['topology'],
            'Сопоставить пути с картой и FC-портами; состояние sysfs не заменяет checker multipathd.')
    offline = [p['name'] for p in topology.get('fc', {}).get('fc_host', [])
               if p.get('port_state') and p['port_state'].lower() != 'online']
    if offline:
        add('fc_port_not_online', 'FC-порты не Online: ' + ', '.join(offline), ['topology'],
            'Сравнить с ожидаемыми задействованными портами; проверить HBA, fabric и zoning.')
    procs = evidence.get('processes', {}).get('data', {})
    if len(procs.get('multipathd', [])) > 1:
        add('multiple_multipathd', 'В host PID namespace видны несколько процессов multipathd.', ['processes'],
            'По PID/cgroup/namespace и inspect установить владельцев; проверить конкуренцию за общие устройства. '
            'Количество процессов само по себе не доказывает конфликт.')
    systemd = evidence.get('systemd', {}).get('data', {}).get('stdout', '')
    socket_active = any('Id=multipathd.socket' in block and 'ActiveState=active' in block
                        for block in systemd.split('\n\n'))
    daemon_containers = [k for k, v in evidence.items() if k.startswith('container:') and
                         'multipathd' in k and v.get('data', {}).get('state', {}).get('Running')]
    if socket_active and daemon_containers:
        add('host_socket_with_container_daemon',
            'Активен host multipathd.socket при работающем контейнере multipathd.',
            ['systemd'] + daemon_containers,
            'Проверить владельцев и namespace сокета/демона до клиентских запросов. '
            'Сокет может активировать второй service; это ещё не доказательство двух активных демонов.')
    for key, value in evidence.items():
        if not key.startswith('config:') or key.startswith(('config:staged:', 'config:host')):
            continue
        _, runtime, container = key.split(':', 2)
        staged_key = 'config:staged:' + container
        staged = evidence.get(staged_key, {})
        if value['status'] == 'missing':
            add('container_config_missing', container + ': /etc/multipath.conf отсутствует.', [key],
                'Проверить, использует ли этот сервис FC/multipath. Для Glance это зависит от Cinder store. '
                'Сопоставить service settings, staged файл и config_files Kolla; не считать это причиной 25/00.')
        if value['status'] == staged.get('status') == 'ok':
            a, b = value['data'], staged['data']
            if a.get('complete') and b.get('complete') and a.get('sha256') != b.get('sha256'):
                add('config_delivery_mismatch', container + ': runtime и staged multipath.conf различаются.',
                    [key, staged_key], 'Проверить config.json, bind mounts, источник override и время '
                    'последнего применения Kolla. SHA файлов не показывает текущую политику демона.')
    required = {'kernel', 'systemd', 'lsblk', 'dm_info', 'dm_tree', 'processes', 'topology', 'log_files'}
    incomplete = [k for k, v in evidence.items() if v.get('status') in
                  ('error', 'timeout', 'skipped', 'unsupported') or v.get('data', {}).get('truncated')
                  or v.get('data', {}).get('excerpt_truncated') or v.get('data', {}).get('line_limit_reached')
                  or (v.get('status') == 'missing' and k in required)]
    if incomplete:
        add('incomplete_collection', 'Часть проверок не завершена или ограничена.', incomplete,
            'Открыть evidence: причина, rc и флаги ограничения. При необходимости сузить --limit '
            'и интервал, увеличить лимиты или повторить сбор с нужными правами.', kind='coverage')
    add('external_correlation_required', 'Mapping Dorado и владение томом через API OpenStack не проверены.', [],
        'Сверить UUID/WWID/WWPN/Host LUN ID с Dorado и attachments/операциями OpenStack. '
        'Отсутствие ошибок в выборке не означает исправность или разрешение на cleanup.', kind='limitation')
    return findings


def collect(options):
    start = utcnow()
    report = {'schema_version': 1, 'host': socket.gethostname(), 'started_at': start,
              'options': options, 'evidence': {}, 'limitations': [
                  'Снимок не атомарный; устройства/логи могли измениться во время сбора.',
                  'Не проверены API OpenStack, Dorado mapping/audit, fabric zoning и все потребители тома.',
                  'Нет запросов к multipathd socket: effective config, checker states и ALUA priorities не собраны.',
                  'Журналы — ограниченная выборка; file logs не фильтруются по времени, timezone берётся из их строк.',
                  'Маскирование секретов эвристическое. Проверить bundle перед передачей третьим лицам.',
              ]}
    evidence = report['evidence']
    def add(key, item):
        evidence[key] = redact(item)
    if platform.system() != 'Linux':
        add('platform', {'status': 'unsupported', 'data': {'system': platform.system()}})
        report.update(finished_at=utcnow(), findings=analyze(report))
        return report
    runner = Runner(options.get('command_timeout', 10), options.get('max_output_bytes', 262144),
                    options.get('command_budget', 180))
    max_devices = options.get('max_devices', 2048)
    log_bytes = options.get('log_tail_bytes', 1048576)
    log_lines = options.get('log_lines', 2000)
    identifiers = [options.get(k, '') for k in ('wwid', 'volume_id', 'request_id')]
    since = options.get('since') or (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1)).isoformat()
    until = options.get('until') or utcnow()
    journal_since = dt.datetime.fromisoformat(since.replace('Z', '+00:00')).astimezone(
        dt.timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f UTC')
    journal_until = dt.datetime.fromisoformat(until.replace('Z', '+00:00')).astimezone(
        dt.timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f UTC')
    report['log_window'] = {'since': since, 'until': until, 'kernel_boot': options.get('boot', 0)}
    add('identity', {'status': 'ok', 'data': {'hostname': socket.gethostname(), 'uname': list(platform.uname()),
                                           'euid': os.geteuid(), 'utc': start}})
    add('os_release', read_file('/etc/os-release'))
    add('topology', {'status': 'ok', 'data': collect_topology(max_devices=max_devices)})
    procs = collect_processes()
    add('processes', {'status': 'ok', 'data': procs})
    add('config:host', read_file('/etc/multipath.conf'))
    for base, pattern, prefix in (('/etc/multipath/conf.d', '*.conf', 'host_fragment'),
                                  ('/etc/udev/rules.d', '*multipath*', 'udev_rule'),
                                  ('/usr/lib/udev/rules.d', '*multipath*', 'udev_rule')):
        paths = sorted(Path(base).glob(pattern))
        add('files:' + prefix + ':' + base, {'status': 'ok', 'data': {
            'paths': [str(p) for p in paths[:50]], 'truncated': len(paths) > 50}})
        for p in paths[:50]:
            add(prefix + ':' + str(p), read_file(p))
    commands = {
        'lsblk': ['lsblk', '-J', '-o', 'NAME,KNAME,TYPE,PKNAME,HCTL,WWN,SERIAL,SIZE,MOUNTPOINT'],
        'dm_info': ['dmsetup', 'info', '-c', '-o', 'name,uuid,open,major,minor'],
        'dm_tree': ['dmsetup', 'ls', '--tree'],
        'findmnt': ['findmnt', '-rn', '-o', 'SOURCE,TARGET,FSTYPE'],
        'swap': ['swapon', '--show', '--output', 'NAME,TYPE,SIZE,USED'],
        'udev_version': ['udevadm', '--version'],
        'systemd': ['systemctl', 'show', 'multipathd.service', 'multipathd.socket', 'systemd-udevd.service',
                    '-p', 'Id', '-p', 'ActiveState', '-p', 'SubState', '-p', 'MainPID', '-p', 'UnitFileState'],
        'kernel': ['journalctl', '-k', '--boot', str(options.get('boot', 0)), '--utc', '--since', journal_since,
                   '--until', journal_until, '-n', str(log_lines), '-o', 'short-iso-precise', '--no-pager'],
        'service_journal': ['journalctl', '-u', 'multipathd.service', '-u', 'systemd-udevd.service',
                            '--utc', '--since', journal_since, '--until', journal_until, '-n', str(log_lines),
                            '-o', 'short-iso-precise', '--no-pager'],
    }
    for key, argv in commands.items():
        result = runner.run(argv)
        if key in ('kernel', 'service_journal'):
            result['line_limit_reached'] = len(result['stdout'].splitlines()) >= log_lines
        add(key, {'status': result['status'], 'data': result})
    pkg_argv = (['rpm', '-q', 'device-mapper-multipath', 'device-mapper-multipath-libs', 'systemd-udev',
                 'sg3_utils', 'lsscsi'] if shutil.which('rpm') else
                ['dpkg-query', '-W', '-f=${Package} ${Version}\n', 'multipath-tools', 'udev', 'sg3-utils', 'lsscsi'])
    result = runner.run(pkg_argv)
    add('host_packages', {'status': result['status'], 'data': result})
    # Fixed service names can be overridden explicitly for suffixed Kolla containers.
    containers = options.get('containers', ['multipathd', 'nova_compute', 'cinder_volume',
                                          'cinder_backup', 'glance_api', 'nova_libvirt'])
    kolla_dir = Path(options.get('node_config_directory', '/etc/kolla'))
    for name in containers:
        add('config:staged:' + name, read_file(kolla_dir / name / 'multipath.conf'))
        config = read_file(kolla_dir / name / 'config.json')
        if config['status'] == 'ok' and config['data']['complete']:
            try:
                spec = json.loads(config['data']['text'])
                files = [{'source': f.get('source'), 'dest': f.get('dest')}
                         for f in spec.get('config_files', [])
                         if 'multipath' in str(f.get('dest', ''))]
                add('kolla_config:' + name, {'status': 'ok', 'data': {'multipath_files': files}})
            except (ValueError, TypeError, AttributeError):
                add('kolla_config:' + name, {'status': 'error', 'data': {'reason': 'invalid_config_json'}})
        else:
            add('kolla_config:' + name, {'status': config['status'] if config['status'] != 'ok' else 'error',
                                       'data': {'reason': 'unavailable_or_truncated'}})
    runtimes = ['podman', 'docker'] if options.get('runtime', 'auto') == 'auto' else [options['runtime']]
    for runtime in runtimes:
        if runtime == 'none':
            add('runtime:none', {'status': 'skipped', 'data': {'reason': 'disabled_by_operator'}})
            continue
        if not shutil.which(runtime):
            add('runtime:' + runtime, {'status': 'missing', 'data': {'reason': 'binary_not_found'}})
            continue
        if runtime == 'docker':
            ownership = docker_socket_owner(procs['dockerd'])
            add('docker_socket_owner', {'status': 'ok' if ownership['verified'] else 'skipped', 'data': ownership})
            if not ownership['verified']:
                add('runtime:docker', {'status': 'skipped', 'data': ownership})
                continue
        prefix = [runtime, '--remote=false'] if runtime == 'podman' else [runtime, '--host', 'unix:///var/run/docker.sock']
        result = runner.run(prefix + ['ps', '-a', '--format', '{{.Names}}'])
        add('runtime:' + runtime, {'status': result['status'], 'data': result})
        if result['status'] != 'ok':
            continue
        present = set(result['stdout'].splitlines())
        for name in containers:
            key = runtime + ':' + name
            if name not in present:
                add('container:' + key, {'status': 'missing', 'data': {'reason': 'name_not_listed'}})
                continue
            inspect = runner.run(prefix + ['inspect', name])
            # Never retain raw inspect (Env, labels, credentials). Project in memory.
            if inspect['status'] != 'ok' or inspect['truncated']:
                add('container:' + key, {'status': 'error', 'data': {'reason': 'inspect_failed_or_truncated',
                                                                                'rc': inspect['rc']}})
                continue
            try:
                obj = json.loads(inspect['stdout'])[0]
                state = obj.get('State', {})
                projected = {'name': name, 'runtime': runtime, 'image': obj.get('Config', {}).get('Image'),
                             'state': {k: state.get(k) for k in ('Status', 'Running', 'Pid', 'StartedAt', 'FinishedAt')},
                             'mounts': [{k: m.get(k) for k in ('Source', 'Destination', 'Type', 'RW')}
                                        for m in obj.get('Mounts', [])]}
            except (ValueError, IndexError, TypeError, AttributeError):
                add('container:' + key, {'status': 'error', 'data': {'reason': 'invalid_inspect'}})
                continue
            add('container:' + key, {'status': 'ok', 'data': projected})
            if not state.get('Running'):
                add('config:' + key, {'status': 'skipped', 'data': {'reason': 'container_not_running'}})
                continue
            exec_prefix = prefix + ['exec', '-u', '0', '-e', 'LC_ALL=C', name]
            result = runner.run(exec_prefix + ['cat', '/etc/multipath.conf'])
            status = result['status']
            if status == 'error' and 'No such file or directory' in result['stderr']:
                status = 'missing'
            config_data = {'text': result['stdout'], 'stderr': result['stderr'], 'rc': result['rc'],
                           'complete': status == 'ok' and not result['truncated'], 'truncated': result['truncated'],
                           'sha256': hashlib.sha256(result['stdout'].encode()).hexdigest()
                           if status == 'ok' and not result['truncated'] else None}
            add('config:' + key, {'status': status, 'data': config_data})
            # No multipath executable is launched even for version probing.
            version_script = (
                "import json\n"
                "try:\n from importlib import metadata\n"
                "except ImportError:\n import importlib_metadata as metadata\n"
                "versions={}\n"
                "for name in ('os-brick','cinder','nova','glance-store','glance'):\n"
                " try: versions[name]=metadata.version(name)\n"
                " except metadata.PackageNotFoundError: versions[name]=None\n"
                "print(json.dumps(versions))\n")
            version = runner.run(exec_prefix + ['/var/lib/kolla/venv/bin/python', '-B', '-c', version_script])
            if version['status'] == 'error' and version['rc'] in (126, 127):
                version = runner.run(exec_prefix + ['python3', '-B', '-c', version_script])
            add('versions:' + key, {'status': version['status'], 'data': version})
            # Only whitelisted INI keys survive in artifacts; never dump whole service configs.
            for service, path in (('nova', '/etc/nova/nova.conf'), ('cinder', '/etc/cinder/cinder.conf'),
                                  ('glance', '/etc/glance/glance-api.conf')):
                if service not in name:
                    continue
                result = runner.run(exec_prefix + ['cat', path])
                selected = {'rc': result['rc'], 'truncated': result['truncated'], 'path': path}
                status = result['status']
                if status == 'ok' and not result['truncated']:
                    try:
                        selected['settings'] = config_projection(result['stdout'])
                    except configparser.Error:
                        status = 'error'
                        selected['reason'] = 'ini_parse_failed'
                elif status == 'ok':
                    status = 'error'
                add('service_settings:' + key, {'status': status, 'data': selected})
            # Container stdout may be empty with Kolla file logging; collect both with explicit limits.
            result = runner.run(prefix + ['logs', '--since', since, '--until', until, '--tail', str(log_lines), name])
            log = excerpt(result['stdout'] + '\n' + result['stderr'], identifiers, log_lines)
            log.update(rc=result['rc'], truncated=result['truncated'], source='container_logs')
            add('log:' + key, {'status': result['status'], 'data': log})
    log_dir = Path(options.get('log_directory', '/var/log/kolla'))
    files = []
    for service in ('nova', 'cinder', 'glance', 'multipathd'):
        base = log_dir / service
        if base.is_dir():
            files.extend(p for p in sorted(base.glob('*')) if p.is_file() and
                         (p.name.endswith('.log') or p.name.endswith('.log.1')))
    file_limit = options.get('max_log_files', 40)
    add('log_files', {'status': 'ok' if log_dir.is_dir() else 'missing', 'data': {
        'paths': [str(p) for p in files[:file_limit]], 'truncated': len(files) > file_limit,
        'selection': 'Only immediate service directories, *.log and *.log.1; compressed rotations excluded.'}})
    for p in files[:file_limit]:
        result = read_file(p, log_bytes, tail=True)
        if result['status'] == 'ok':
            data = result['data']
            log = excerpt(data['text'], identifiers, log_lines)
            log.update(path=str(p), truncated=data['truncated'], time_filter_applied=False)
            result['data'] = log
        add('log:file:' + str(p), result)
    add('daemon_queries', {'status': 'skipped', 'data': {'reason':
        'No multipath/multipathd/virsh socket queries: avoid socket activation. See README for manual follow-up.'}})
    report.update(finished_at=utcnow(), findings=analyze(report))
    return report
