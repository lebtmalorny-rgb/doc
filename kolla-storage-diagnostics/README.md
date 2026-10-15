# Диагностика FC/multipath, Dorado V6 и томов в Kolla

На входе — существующий inventory Kolla-Ansible. На выходе — локальный каталог
с Markdown и JSON по выбранным узлам. Комплект помогает разделить проблемы
доставки `multipath.conf`, состояния FC/SCSI/DM и attach/detach Nova/Cinder/Glance.
Применим к контейнерному Linux DM Multipath в PVS/ITkey/Kolla; не рассчитан
на UltraPath или NVMe-oF.

Сборщик не исправляет конфигурацию и не изменяет устройства. Он не запускает
`multipath`, `multipathd`, `virsh`, rescan, udev trigger, flush, restart/reload,
unmap или очистку attachments. Временные файлы на узлах создаёт только обычный
транспорт Ansible; постоянный диагностический агент не устанавливается.

## Быстрый запуск

Перенести **весь каталог** `kolla-storage-diagnostics` на управляющий узел.
Использовать окружение Ansible, из которого доступен inventory и SSH к узлам.
Зависимости: `ansible-core` на контроллере; Python на Linux-узлах согласно
матрице совместимости установленного Ansible (код сборщика требует Python ≥ 3.8).
Коллекция Kolla и сторонние Python-библиотеки сборщику не нужны.

```bash
cd kolla-storage-diagnostics

# Сначала посмотреть, какие узлы выбраны. Подставить свой inventory.
ansible-playbook -i /etc/kolla/multinode diagnose.yml \
  --limit 'compute03,ctrl01' --list-hosts

# Собрать текущий снимок + последний час journal/container logs.
ansible-playbook -i /etc/kolla/multinode diagnose.yml \
  --limit 'compute03,ctrl01'
```

`become: true` включён: нужны sysfs/proc, журналы, rootful Docker/Podman и
конфиги сервисов. Если sudo требует пароль, добавить `-K`; SSH user/key задать
в inventory или обычными `-u`/`--private-key`. Для режима без повышения прав:
`-e storage_diag_become=false`, но часть evidence будет недоступна.

Можно использовать группы: `--limit 'compute:storage:control'`. **Без `--limit`
выбирается `all`**, включая служебные узлы inventory. Предпочтительнее начинать
с хоста ошибки и узла `cinder_volume`. Параллелизм задаётся обычным `-f 3`.
Все controller tasks находятся в том же play, поэтому не исчезают при `--limit`.
Не применять `--start-at-task`: инициализация manifest обязательна.

Для конкретного инцидента скопировать [examples/incident.yml](examples/incident.yml),
изменить время/UUID/WWID и выполнить:

```bash
ansible-playbook -i /etc/kolla/multinode diagnose.yml \
  --limit 'compute03,ctrl01' -e @examples/incident.yml \
  -e storage_diag_output_base=/srv/diagnostics/dorado
```

Время задаётся ISO-8601 с часовым поясом: `2026-10-14T12:00:00+03:00`
или `2026-10-14T09:00:00Z`. Оно нормализуется в UTC. Без параметров используются
последние 60 минут **по часам каждого хоста**; для межузловой корреляции задавать
одинаковые абсолютные `since`/`until` и проверить синхронизацию часов.
`boot: -1` меняет выбор загрузки для kernel journal, но не делает sysfs-снимок
историческим. Буква `sdX` к этому времени уже могла принадлежать другому LUN.

Значения `wwid`, `volume_id`, `request_id` добавляют **буквальный поиск** в логах.
Они не отфильтровывают остальные устройства и базовые сигналы ошибок: связь
UUID Cinder ↔ WWID ↔ LUN должна устанавливаться по evidence, а не предполагаться.

## Что получится

Последняя задача выводит путь `artifacts/storage-diag-.../index.md` и количество
результатов `ok`, `unreachable`, `collector_failed`, `missing_record`.
`ok` означает «сборщик вернул отчёт», **а не «хост исправен»**.
Внутри него отдельные команды могут завершиться ошибкой, timeout или быть пропущены.

```text
storage-diag-.../
├── index.md              # обзор выбранных узлов и порядок разбора
├── summary.json          # статусы сбора и коды наблюдений
├── manifest.json         # полный список узлов с учётом --limit
├── hosts/
│   ├── <hash>.md         # наблюдения, следующие проверки, таблица путей
│   └── <hash>.json       # evidence, команды/rc, конфиги и фрагменты логов
└── records/<hash>.json   # исходные ответы сборщика
```

Имена файлов — SHA-256 имени inventory; само имя видно в index/JSON. Список
полный: отсутствие ответа от узла сохраняется как пробел диагностики.
Новый запуск создаёт отдельный каталог. Права каталогов `0700`, файлов `0600`.

Просмотреть evidence из JSON, если на контроллере есть `jq`:

```bash
jq '.hosts' /path/to/run/summary.json
jq '.report.findings' /path/to/run/hosts/HASH.json
jq '.report.evidence.kernel' /path/to/run/hosts/HASH.json
jq '.report.evidence.topology.data.block' /path/to/run/hosts/HASH.json
jq '.report.evidence["config:docker:nova_compute"]' /path/to/run/hosts/HASH.json
```

Пересобрать Markdown после переноса bundle без доступа к хостам:

```bash
python3 tools/render_report.py /path/to/run
```

## Какие данные собираются

| Слой | Evidence | Для чего |
|---|---|---|
| Хост | ОС, ядро, UTC, EUID; relevant packages; `systemctl show` | Установить окружение и состояние service/socket |
| Процессы | PID/cgroup/namespaces `multipathd`, `dockerd`; `/dev` FD QEMU | Найти владельца демона и часть потребителей; cmdline/env не читаются |
| SCSI/DM | sysfs: sd/dm, H:C:T:L, WWID, state, slaves/holders, DM UUID | Связать путь и карту; текущий снимок |
| FC | initiator/target WWPN, port state, speed; remote ports | Выделить конкретные порты для проверки fabric/mapping |
| udev | выбранные свойства `/run/udev/data`, правила с multipath в имени | Проверить текущую базу идентификаторов и наличие правил |
| Блочные устройства | `lsblk`, `dmsetup info`, `dmsetup ls --tree`, mounts/swap | Открытые карты и видимые host-потребители |
| Конфиги | host, `/etc/kolla/<container>/multipath.conf`, runtime-копия, SHA-256 | Проверить доставку и различия staged/runtime |
| Kolla | только multipath entries из `config.json`; проекция inspect mounts/state | Показать цепочку доставки; без полного inspect/Env |
| Nova/Cinder/Glance | whitelist storage-настроек из INI; версии Python packages | Проверить multipath flags, backend/store, os-brick |
| Журналы | kernel, multipathd/udevd; container logs; хвосты файлов Kolla | Найти симптомы и последовательности attach/detach |

В режиме `runtime: auto` проверяются установленные Podman и Docker. Docker
используется только после проверки владельца конкретного socket: listening
inode из `/proc/net/unix` должен быть открытым FD существующего `dockerd`,
а файл socket в его `/proc/PID/root` должен совпадать с хостовым. При невозможности
проверки запросы Docker пропускаются. Используется явный локальный socket
`unix:///var/run/docker.sock`: пользовательский удалённый context игнорируется.
Podman вызывается с `--remote=false`. Rootless runtime и нестандартный Docker
socket автоматически не обнаруживаются. Контейнеры выбираются по **точным**
именам из `containers`: для backend suffix изменить список в параметрах.
Остановленный контейнер не запускается; его runtime config не читается через exec.
Проверка владельца — снимок; она не блокирует завершение демона между проверкой
и запросом. При нестабильном runtime можно выбрать `runtime: none`.

Штатный `/etc/kolla/<container>` используется как staged-кандидат. Если в вашем
форке каталог называется иначе, ориентироваться на реальные mounts из inspect:
отсутствие staged-кандидата само по себе не доказывает дефект доставки.
Фрагменты `/etc/multipath/conf.d` собираются на хосте; нестандартные include/
config_dir и container fragments автоматически не разворачиваются.
Для версии пакетов используется Kolla venv, затем `python3`, если venv отсутствует;
неудачный запрос записывается как неполнота.

## Как трактовать наблюдения

| Код | Подтверждает | Следующая проверка |
|---|---|---|
| `client_config_error` | В выборке есть missing config / blacklisting message | Найти автора и runtime config именно этого контейнера |
| `container_config_missing` | В работающем контейнере нет файла | Проверить, нужен ли ему FC/multipath; для Glance — Cinder store |
| `config_delivery_mismatch` | Полные staged и runtime файлы отличаются | Источник override → staging → mount → `config_files`/копирование Kolla |
| `scsi_lun_not_supported` | В журнале есть SCSI `Logical unit not supported` | WWID/WWPN/Host LUN ID, mapping и audit на Dorado |
| `scsi_path_state` / `fc_port_not_online` | Текущий sysfs/FC state отличается от рабочего | Проверить ожидаемые пути, HBA, target, fabric; неиспользуемый порт может быть Offline |
| `multiple_multipathd` | Видны несколько процессов | По cgroup/namespaces выяснить владельцев и возможный конфликт |
| `host_socket_with_container_daemon` | Host socket активен вместе с контейнером | До запросов к сокету выяснить, какой service он может активировать |
| `io_error` / `detach_error` | Найдены соответствующие строки | По тому, host и времени сопоставить локальную очистку и unmap |
| `incomplete_collection` | Есть сбои/пропуски/лимиты | Открыть конкретный evidence и повторить нужную проверку |
| `external_correlation_required` | Есть обязательная внешняя часть диагностики | Сверить Dorado и API OpenStack; всегда присутствует |

Автоматическая классификация — правила поиска симптомов, не экспертное
доказательство первопричины. `Logical unit not supported` (**ASC/ASCQ 25/00**)
и отсутствующий конфиг — разные наблюдения. Нет правила «25/00 → mapping снят».
Варианты: неверный/отсутствующий mapping действующего тома, недоступный LUN
на части путей, либо оставшийся после корректного unmap Linux-путь.
Выбор требует данных самого массива и установленного владельца тома.

Хостовый и клиентский конфиги могут намеренно различаться; минимальный
`defaults {}` в клиентском образе ITkey сам по себе не доказывает проблему.
Сравнение SHA staged/runtime также не показывает, какой конфиг **уже применил**
работающий `multipathd`.

## Что ещё нужно для вывода о причине

1. **Dorado:** LUN WWN/ID, Host/WWPN, Host Group/LUN Group/Mapping View,
   Host LUN ID, target ports и audit за тот же интервал. Inventory Linux
   этих данных не содержит. Сборщик не подключается к DeviceManager/CLI массива.
2. **OpenStack:** `openstack volume show UUID -f yaml`, attachments и все
   потребители при multiattach; сервер/хост; текущие image-transfer/backup/Glance.
   Пустой список VM attachments не доказывает, что том не используется.
3. **Работающий multipathd:** после проверки единственного нужного владельца
   вручную запросить paths/maps/config в его контексте. Автоматических socket
   queries нет: они способны активировать host service. Пример для уже
   проверенного контейнера: `podman exec -u 0 multipathd multipathd show paths`,
   затем `... multipathd show maps topology` и `... multipathd show config`.
   Для Docker заменить runtime. Эти команды не включены в playbook.
4. **Libvirt:** при необходимости вручную `virsh domblklist DOMAIN --details`
   через существующий работающий libvirt, включая inactive config. Коллектор
   избегает libvirt socket activation. Снимок FD QEMU не покрывает выключенные ВМ
   и не гарантирует отсутствие других потребителей.

Порядок исправления выбирать только после корреляции. Руководство из той же
беседы: [Dorado V6: диагностика и исправление](https://github.com/lebtmalorny-rgb/doc/blob/main/DORADO_V6_LOGICAL_UNIT_NOT_SUPPORTED_RUNBOOK.md).
Объяснение уровней: [хост, контейнеры и udev](https://github.com/lebtmalorny-rgb/doc/blob/main/MULTIPATH_DORADO_V6_HOST_CONTAINERS_EXPLAINED.md).

## Ограничения, время и конфиденциальность

- По умолчанию subprocess: 10 секунд на команду, 180 секунд суммарного бюджета
  на хост. После исчерпания новые команды отмечаются `skipped`. Чтения sysfs/proc
  и файлов ограничены объёмом/количеством, но это не жёсткий общий wall-clock timeout.
  SSH timeout задаётся настройками Ansible отдельно.
  После timeout отправляется SIGKILL только группе запущенной диагностической
  команды; ожидание завершения ограничено ещё 0,2 с. `reap_pending: true` означает,
  что процесс не завершился за это время, например из-за uninterruptible I/O.
- `journalctl` и container logs ограничены интервалом и количеством строк;
  stdout/stderr дополнительно ограничены байтами. При достижении лимита часть
  контекста могла не попасть в bundle. Kernel journal по умолчанию текущей загрузки.
- File logs: только непосредственные `/var/log/kolla/{nova,cinder,glance,multipathd}`,
  `*.log` и `*.log.1`, последние 1 MiB каждого файла; до 40 файлов. `.gz` не читаются.
  Из хвоста выбираются сигналы/идентификаторы с контекстом ±2 строки; берутся последние
  2000 строк выборки. **Время для file logs не фильтруется**: форматы/таймзоны различаются.
  Сначала сверять timestamps. Старый инцидент может потребовать отдельной архивной выборки.
- Нет полного копирования service configs, `passwords.yml`, container Env,
  domain XML или `/proc/*/cmdline`. Пароли/токены/credentials в URL маскируются
  эвристически; нестандартные секреты могут остаться. UUID, WWID, WWPN, IP,
  пути и имена хостов сохраняются для корреляции. Bundle считать служебным.
- `--check` отклоняется явно. Наличие файлов, правила udev, sysfs state и SHA
  конфигов не доказывают правильность live attach/detach или политики ALUA.
- Если Ansible не смог получить module report, сохраняется безопасное общее
  описание сбоя; полный exception не копируется из-за риска раскрытия credentials.
  Связь и become можно отдельно проверить обычным `ansible ... -m ping`.
- Ошибки удалённых проверок не прерывают сбор остальных хостов. Exit code 0
  означает завершение оркестрации; проверять `summary.json` и coverage, а не только RC.

## Проверка самого комплекта

```bash
python3 -m unittest discover -s tests -v
python3 tests/integration.py
```

Unit tests проверяют классификацию, whitelist/masking, sysfs-корреляцию,
timeouts/лимиты subprocess и отчёт при отсутствующем узле. Integration test
использует временный fixture module и loopback SSH с закрытым портом: проверяет
`--limit`, недоступный **первый** узел, private modes, check-mode и упаковку
реального Ansible module. Он не подключается к кластеру.

Проверено локально с ansible-core 2.18.2. Состояние production Kolla/Dorado,
конкретные версии Docker/Podman и результат FC attach/detach этим не проверены.

Семантика orchestration: [Ansible error handling](https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks_error_handling.html),
[delegation](https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks_delegation.html).
Runtime CLI: [Podman remote mode](https://docs.podman.io/en/latest/markdown/podman.1.html#remote-r),
[Podman logs](https://docs.podman.io/en/latest/markdown/podman-logs.1.html),
[Docker exec](https://docs.docker.com/reference/cli/docker/container/exec/).
Значение SCSI кода: [T10 ASC/ASCQ](https://www.t10.org/lists/asc-num.txt).
