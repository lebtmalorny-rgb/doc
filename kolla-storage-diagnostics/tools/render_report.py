#!/usr/bin/env python3
"""Render a controller-local bundle; never connects to hosts or arrays."""
import collections
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import sys


def write_private(path, text):
    # chmod before writing also handles a previously permissive existing file.
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as stream:
        stream.write(text)


def md(value):
    return str(value).replace('|', '\\|').replace('\n', ' ').replace('<', '&lt;').replace('>', '&gt;')


def render(root):
    root = Path(root).resolve()
    manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    records = {}
    warnings = []
    for path in sorted((root / 'records').glob('*.json')):
        try:
            record = json.loads(path.read_text(encoding='utf-8'))
            if record.get('host') in manifest['hosts']:
                records[record['host']] = record
        except (ValueError, OSError, AttributeError):
            warnings.append('Unreadable record: ' + path.name)
    hosts_dir = root / 'hosts'
    hosts_dir.mkdir(mode=0o700, exist_ok=True)
    hosts_dir.chmod(0o700)
    summary = {'schema_version': 1, 'generated_at': dt.datetime.now(dt.timezone.utc).isoformat(),
               'hosts': {}, 'warnings': warnings, 'health_verdict': 'not_determined'}
    index = ['# Диагностика FC/multipath Kolla', '',
             'Сводка наблюдений, не заключение об исправности. Нулевое число найденных ошибок '
             'не разрешает удаление устройств.', '',
             '| Узел inventory | Сбор | Evidence ok / всего | Выводы | Отчёт |',
             '|---|---|---:|---:|---|']
    for host in manifest['hosts']:
        record = records.get(host, {'host': host, 'status': 'missing_record', 'report': {}})
        report = record.get('report') or {}
        key = hashlib.sha256(host.encode()).hexdigest()
        evidence = report.get('evidence', {})
        findings = report.get('findings', [])
        counts = dict(collections.Counter(v.get('status', 'unknown') for v in evidence.values()))
        summary['hosts'][host] = {'status': record['status'], 'evidence_statuses': counts,
                                  'finding_codes': [f['code'] for f in findings],
                                  'report': 'hosts/' + key + '.md'}
        index.append('| %s | %s | %s / %s | %s | [открыть](hosts/%s.md) |' %
                     (md(host), record['status'], counts.get('ok', 0), len(evidence), len(findings), key))
        lines = ['# ' + md(host), '', '**Состояние сбора:** ' + record['status'], '',
                 'Это снимок доступных данных, не доказательство отсутствия неисправностей.', '',
                 '[JSON с исходными данными](%s.json)' % key, '']
        if not report:
            lines += [record.get('transport_note') or 'Результат не получен; проверить связь, become, Python и вывод Ansible.', '']
        lines += ['## Время и область', '', '```json', json.dumps({k: report.get(k) for k in
                  ('started_at', 'finished_at', 'log_window', 'options')}, ensure_ascii=False, indent=2), '```', '',
                  '## Наблюдения и следующие проверки', '']
        for f in findings:
            lines += ['### ' + md(f['code']) + ' (' + md(f['kind']) + ')', '', md(f['title']), '',
                      md(f['next_step']), '', 'Evidence: ' + ', '.join('`' + md(r) + '`' for r in f['evidence']), '']
        if not findings:
            lines += ['Классификация недоступна или наблюдения отсутствуют; это не статус OK.', '']
        topology = evidence.get('topology', {}).get('data', {})
        lines += ['## Текущая связь устройств и FC-портов', '',
                  '| Устройство | H:C:T:L | WWID / DM UUID | Состояние | Initiator WWPN | Target WWPN | Slaves / holders |',
                  '|---|---|---|---|---|---|---|']
        for b in topology.get('block', []):
            lines.append('| ' + ' | '.join(md(v or '') for v in (
                b['name'], b.get('hctl'), b.get('wwid') or b.get('dm_uuid'), b.get('state'),
                b.get('initiator_wwpn'), b.get('target_wwpn'),
                ','.join(b.get('slaves', [])) + ' / ' + ','.join(b.get('holders', [])))) + ' |')
        lines += ['', '## Доступность evidence', '', '| ID | Статус | Ограничение / причина |', '|---|---|---|']
        for name, item in evidence.items():
            data = item.get('data', {})
            reason = data.get('reason') or data.get('error') or ''
            if data.get('truncated') or data.get('excerpt_truncated'):
                reason += ' truncated'
            lines.append('| %s | %s | %s |' % (md(name), item.get('status'), md(reason)))
        lines += ['', '## Границы результата', ''] + ['- ' + md(s) for s in report.get('limitations', [])]
        lines += ['', 'Полные собранные фрагменты находятся в JSON, поле `report.evidence`. '
                  'Отчёт не выполняет исправлений и не доказывает возможность cleanup.', '']
        write_private(hosts_dir / (key + '.md'), '\n'.join(lines))
        write_private(hosts_dir / (key + '.json'), json.dumps(record, ensure_ascii=False, indent=2) + '\n')
    index += ['', '## Как разбирать', '',
              '1. Начать с узла, на котором появилась ошибка; открыть его отчёт и evidence JSON.',
              '2. Разбирать config delivery и SCSI 25/00 отдельно; связывать их только через конкретный том и время.',
              '3. Для SCSI сверить H:C:T:L → WWID → initiator/target WWPN → Host LUN ID и mapping Dorado.',
              '4. До любых изменений установить владельца тома через OpenStack, QEMU и операции Cinder/Glance.',
              '', 'Доступность сбора и исправность хоста — разные вещи. '
              'Запросы к daemon socket, API OpenStack и СХД не выполнялись.', '']
    if warnings:
        index += ['## Ошибки чтения bundle', ''] + ['- ' + md(w) for w in warnings] + ['']
    write_private(root / 'summary.json', json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    write_private(root / 'index.md', '\n'.join(index))
    return summary


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('usage: render_report.py RUN_DIRECTORY')
    result = render(sys.argv[1])
    counts = dict(collections.Counter(v['status'] for v in result['hosts'].values()))
    print(str(Path(sys.argv[1]).resolve() / 'index.md'))
    print('Collection coverage: ' + json.dumps(counts, ensure_ascii=False))
