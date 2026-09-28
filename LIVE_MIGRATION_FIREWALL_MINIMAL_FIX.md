# Минимальные правки firewall для live migration в OpenStack Epoxy 2025.1

Дата: 28.09.2026. База: `kolla-ansible-pvs_1.0.0_23.09.zip`, коммит из комментария ZIP `0f697f232e7e139e720a104b4379ccac7e84139d`.

## Краткий вывод

В этом форке каталог host firewall разрешает управляющие соединения libvirt, но не передачу состояния ВМ через динамические TCP-порты QEMU. Генератор завершает policy `kolla-host-input` правилом `drop`. При действующей policy этот пробел способен заблокировать live migration.

**Если адреса API и migration совпадают, минимальная правка — один новый поток в одном YAML-файле. Если migration использует другую сеть, нужны два файла: каталог потоков и проекция адресов firewall.**

| Условия | Что править | Ожидаемый эффект |
|---|---|---|
| API и migration используют одни адреса; стандартный диапазон libvirt | `ansible/roles/host-firewall/vars/catalog.yml`, вариант A | Разрешить QEMU migration между compute |
| Migration использует отдельные адреса | Тот же каталог и `ansible/action_plugins/kolla_firewall_model.py`, вариант B | Разрешить потоки на фактических migration-адресах |
| Установлен другой диапазон или переопределены адреса/порты | Сначала сверить действующие конфиги | Подставить реальные значения, а не предполагать defaults |

Правки ниже устраняют конкретный пробел каталога. Они не доказывают, что именно firewall вызвал зарегистрированный сбой, и не являются полной ревизией всех сетевых потоков облака.

## 1. Что подтверждено исходниками и диагностикой

В исходном `ansible/roles/host-firewall/vars/catalog.yml`, блок `nova-libvirt` около строки 507:

- разрешены `16509/TCP` и, при `libvirt_tls=true`, `16514/TCP`;
- оба потока используют `network: api`;
- в блоке `nova-ssh` разрешён `8022/TCP`, также на сети `api`;
- диапазона QEMU migration нет.

В `ansible/module_utils/kolla_firewall_plan.py`, функция `rules_from_report()`, последним правилом добавляется `rule priority="30000" drop`.

В `ansible/roles/nova-cell/templates/libvirtd.conf.j2` задано `listen_addr = "{{ migration_interface_address }}"`. В `templates/nova.conf.d/libvirt.conf.j2` адрес входящей миграции — `migration_interface_address` либо `migration_hostname` при TLS. Однако `ActionModule.project()` в `ansible/action_plugins/kolla_firewall_model.py` передаёт генератору только адреса сети `api`.

Из предоставленного `debug.docx`: предварительные проверки миграции завершились успешно; в `06:04:38` запрос `jobStats()` получил ошибку:

```text
Timed out during operation: cannot acquire state change lock
(held by monitor=remoteDispatchDomainMigratePerform3Params)
```

В `06:05:08` отмена миграции также не смогла получить блокировку. Это подтверждает зависшую операцию libvirt, но не её первопричину. В документе нет действующих firewall rules или трассы заблокированного соединения. Приведённые ошибки RabbitMQ и MySQL относятся к более позднему времени.

## 2. Условия выбора минимального варианта

Перед правкой проверить на обоих compute фактические `live_migration_inbound_addr`, `listen_addr`, диапазон `migration_port_min/max`, TLS и маршруты. Команды ниже предназначены для чтения; имена контейнеров взять из `podman ps` или `docker ps`.

```bash
sudo podman ps --format '{{.Names}}'

# Подставить фактические имена контейнеров.
NOVA_CONTAINER=nova_compute
LIBVIRT_CONTAINER=nova_libvirt

sudo podman exec "$NOVA_CONTAINER" grep -E \
  '^[[:space:]]*(connection_uri|live_migration_[a-z_]+)[[:space:]]*=' \
  /etc/nova/nova.conf

sudo podman exec "$LIBVIRT_CONTAINER" grep -E \
  '^[[:space:]]*(listen_addr|listen_tcp|listen_tls|tcp_port|tls_port|migration_address|migration_host|migration_port_min|migration_port_max)[[:space:]]*=' \
  /etc/libvirt/libvirtd.conf /etc/libvirt/qemu.conf

sudo firewall-cmd --state
sudo firewall-cmd --version
sudo firewall-cmd --info-policy=kolla-host-input
sudo firewall-cmd --permanent --info-policy=kolla-host-input
```

Для Docker заменить `podman` на `docker`. Если строки диапазона отсутствуют, действуют defaults установленной сборки libvirt; отсутствие строк не означает отсутствие migration-портов.

**О диапазоне.** В диагностике указана сборка libvirt `11.10.0` от поставщика ОС. В upstream libvirt `v11.10.0` задан диапазон **49152–49215/TCP**: константы `QEMU_MIGRATION_PORT_MIN/MAX` в [qemu_conf.c](https://github.com/libvirt/libvirt/blob/v11.10.0/src/qemu/qemu_conf.c#L74) и пример [qemu.conf.in](https://github.com/libvirt/libvirt/blob/v11.10.0/src/qemu/qemu.conf.in#L961). В [руководстве Nova 2025.1](https://docs.openstack.org/nova/2025.1/admin/configuring-migrations.html) приведён более широкий диапазон `49152–49261`. Это разные границы: номер версии из лога не доказывает отсутствие патчей поставщика.

Ниже использован диапазон upstream `49152-49215`. Перед применением подтвердить, что установленный пакет сохраняет эти defaults, либо заменить диапазон в правиле на реально настроенный. Для покрытия диапазона из руководства Nova можно использовать `49152-49261`; остальные части правки остаются теми же. Сам `qemu.conf` ради этой правки менять не требуется.

Вариант A подходит, только если адреса обоих compute в модели `api` совпадают с адресами, реально используемыми для миграции, а `ip route get <migration-IP-соседа>` выбирает ожидаемый исходный адрес. Равенство имён интерфейсов само по себе недостаточно при нескольких адресах на интерфейсе. При TLS дополнительно проверить разрешение `migration_hostname` на обоих узлах. Для туннелированной миграции канал передачи данных устроен иначе; её действующий режим тоже надо учитывать.

## 3. Вариант A — один файл при общей сети

На deployment-узле в **исходниках используемого форка** открыть:

```text
ansible/roles/host-firewall/vars/catalog.yml
```

В `host_firewall_catalog.services.nova-libvirt.flows`, после `nova-libvirt-tls` и перед блоком `nova-ssh`, добавить:

```yaml
        - id: nova-live-migration-data
          protocol: tcp
          port_range: "49152-49215"
          destination_group: compute
          network: api
          source_groups: [compute]
```

Существующие потоки `16509`, `16514` и `8022` оставить. Новый поток добавляется на каждом compute с адресами источников из группы `compute`: это позволяет миграцию в обоих направлениях. Не добавлять условие `libvirt_tls` к потоку данных: TLS управляющего соединения не заменяет native migration transport.

В этой реализации к каждому потоку также добавляются `host_firewall_operator_sources` либо обнаруженный deployment-адрес. Поэтому итоговые разрешения — compute и существующие operator-источники; широкие operator-CIDR необходимо учитывать при просмотре отчёта. Параметр `host_firewall_client_sources` к новому внутреннему потоку не применяется.

Это весь минимальный diff для общей сети. Поддержка `port_range` уже есть в модели и компиляторе правил.

## 4. Вариант B — два файла при отдельной сети migration

Этот вариант заменяет A. Если поток из A уже добавлен, изменить его `network` на `migration`, а не создавать второй поток с тем же `id`.

### 4.1. Каталог потоков

В `ansible/roles/host-firewall/vars/catalog.yml` заменить целиком блоки `nova-libvirt` и `nova-ssh` следующим фрагментом. Порты предполагают defaults форка; при переопределённых `nova_libvirt_port` или `nova_ssh_port` указать соответствующие значения.

```yaml
    nova-libvirt:
      enable_flag: enable_nova_libvirt_container
      coverage: complete
      source_evidence: 0809 ansible/roles/nova-cell/defaults/main.yml
      flows:
        - id: nova-libvirt-control
          protocol: tcp
          port: 16509
          destination_group: compute
          network: migration
          source_groups: [compute]
        - id: nova-libvirt-tls
          protocol: tcp
          port: 16514
          required_conditions: [libvirt_tls]
          destination_group: compute
          network: migration
          source_groups: [compute]
        - id: nova-live-migration-data
          protocol: tcp
          port_range: "49152-49215"
          destination_group: compute
          network: migration
          source_groups: [compute]
    nova-ssh:
      enable_flag: enable_nova_ssh
      coverage: complete
      source_evidence: 0809 ansible/roles/nova-cell/defaults/main.yml
      flows:
        - id: nova-ssh-migration
          protocol: tcp
          port: 8022
          destination_group: compute
          network: api
          source_groups: [compute]
        - id: nova-ssh-migration-network
          protocol: tcp
          port: 8022
          destination_group: compute
          network: migration
          source_groups: [compute]
```

Libvirt-потоки здесь описывают compute→compute; исходное разрешение всей группы `control` для libvirt заменяется этой связью. Управляющий доступ с deployment/operator сохраняется через механизм operator-источников. Если libvirt реально используют другие клиенты с controllers, отдельно описать их реальные исходные адреса: автоматического выбора API-адреса источника при destination в другой сети модель не делает.

Для SSH сохранён API-поток и добавлен migration-поток, поскольку `ansible/roles/nova-cell/templates/sshd_config.j2` при разных адресах слушает обе сети. Это не переключает Nova на SSH transport: только согласует разрешения с существующим listener.

### 4.2. Адреса в модели firewall

В `ansible/action_plugins/kolla_firewall_model.py`, метод `ActionModule.project()`, после существующего блока:

```python
        if address is None:
            unresolved.append('api_interface_address')
```

добавить следующий код **до комментария `# Prefer an explicit per-host Ansible port`**:

```python
        network_addresses = {'api': address}
        if host in groups.get('compute', []):
            migration_raw = values.get('migration_interface_address')
            migration_explicit = 'migration_interface_address' in values and not (
                isinstance(migration_raw, str) and re.fullmatch(
                    r"\{\{\s*(['\"])migration\1\s*\|\s*kolla_address\s*\}\}",
                    migration_raw)
            )
            migration_override = (
                resolve('migration_interface_address')
                if migration_explicit else None)
            migration_address = (
                None if migration_explicit and migration_override is None
                else self.observed_address(
                    observation,
                    resolve('migration_interface'),
                    resolve('migration_address_family'),
                    migration_override,
                    vips)
            )
            if migration_address is None:
                unresolved.append('migration_interface_address')
            network_addresses['migration'] = migration_address
```

В возвращаемом словаре этого же метода заменить ровно одну строку:

```python
            'network_addresses': {host: {'api': address}},
```

на:

```python
            'network_addresses': {host: network_addresses},
```

Код использует уже собранные адреса интерфейсов. IPv4/IPv6, неоднозначный выбор адреса, явный override и исключение VIP обрабатываются существующим `observed_address()`. При неопределённом migration-адресе формируется блокер; подстановка API-адреса вместо него не выполняется. Migration-адрес собирается только для compute, поэтому отдельный migration-интерфейс на controllers этим фрагментом не требуется.

Одной замены `network: api` на `network: migration` в YAML недостаточно: без изменения Python-проекции в отчёте появится `MISSING_ADDRESS`.

## 5. Где находятся параметры и куда доставить правку

| Место | Назначение |
|---|---|
| `/etc/kolla/globals.yml`, `globals.d`, inventory/group_vars/host_vars | Значения конкретного окружения; проверить `migration_interface`, семейство адресов, TLS и host-specific overrides |
| `ansible/group_vars/all.yml` | Defaults форка: `migration_interface: "{{ api_interface }}"`, `migration_address_family: "{{ api_address_family }}"`, адрес через `kolla_address` |
| `ansible/roles/nova-cell/defaults/main.yml` | Defaults `nova_libvirt_port`, `nova_ssh_port`, `migration_hostname` |
| `ansible/roles/host-firewall/vars/catalog.yml` | Фактическая матрица потоков, которую загружает firewall-role; сюда относится правка A/B |
| `ansible/action_plugins/kolla_firewall_model.py` | Проекция адресов в firewall-модель; менять только для B |
| `/etc/kolla/nova-compute/nova.conf`, `/etc/kolla/nova-libvirt/` | Сгенерированные конфиги на compute при стандартном `node_config_directory`; проверить, но не использовать как постоянное место этой правки |
| `/etc/firewalld/policies/kolla-host-input.xml` | Результат применения policy; вручную не подменять вместо исходного каталога |

Изменение распакованного ZIP само по себе не меняет установленный Kolla-Ansible. Доставить изменённые файлы в **тот экземпляр форка, откуда запускается CLI**: через принятый процесс установки форка либо обновление его рабочего checkout при editable-install. Перед запуском проверить `command -v kolla-ansible` и путь выбранного playbook в выводе CLI; `host-firewall.yml`, его role и action plugins должны относиться к исправленной поставке.

Для правки firewall не требуется менять Nova, пересобирать образы, настраивать иной migration transport или перезапускать libvirt. Это справедливо, если действующие адреса и диапазон уже корректны и меняются только правила доступа.

## 6. Применение только firewall и проверка результата

### 6.1. Сначала сформировать отчёт

На deployment-узле, из исправленного установленного форка, использовать штатный inventory целиком. Подставить свои пути:

```bash
kolla-ansible host-firewall -i /path/to/multinode \
  --configdir /etc/kolla --mode report \
  -e '{"host_firewall_auto": false, "host_firewall_flag_policy": "strict"}'
```

Проверить `collection_complete`, все `blockers` и `warnings`, а на каждом compute — `candidate_flows`:

- присутствует `nova-live-migration-data` с выбранным диапазоном;
- destination совпадает с фактическим входящим адресом миграции;
- sources содержат адреса всех возможных compute-источников и только ожидаемые дополнительные operator-источники;
- для B управляющий порт libvirt и дополнительный SSH-поток используют сеть `migration`;
- нет `MISSING_ADDRESS`, `UNRESOLVED_VARIABLE`, несоответствий семейств адресов.

Не ограничивать отчёт произвольно парой узлов: текущая проекция получает адреса только выбранных hosts, а каталог ссылается на inventory-группы целиком. После изменения набора hosts или переменных нужен новый отчёт и новый `plan_id`.

### 6.2. Применить после проверки отчёта

Следующий шаг **изменяет firewall**. Он относится к уже установленной и подготовленной policy `kolla-host-input`. Если policy отсутствует, это отдельная процедура первоначальной настройки, а не минимальное исправление работающей policy.

В отдельном операторском YAML-файле задать:

```yaml
host_firewall_auto: false
host_firewall_flag_policy: strict
host_firewall_plan_id: "REPLACE_WITH_64_HEX_FROM_FRESH_REPORT"
host_firewall_serial: 1
host_firewall_rollback_timeout: 300
host_firewall_verification_checks:
  - id: existing-service
    type: tcp
    host: "REPLACE_WITH_REAL_REACHABLE_SERVICE_IP"
    port: 16509
```

Это **шаблон, не готовый файл запуска**: заменить `plan_id`, адрес и порт на действующий сервис, достижимый с deployment-узла; при TLS порт libvirt обычно `16514`. Можно использовать существующие утверждённые service checks. Динамический QEMU migration-порт нельзя выбирать как постоянно работающий проверочный endpoint: вне миграции listener может отсутствовать. Для нескольких проверок допустимо до 16 entries. Не добавлять `host_firewall_initialize` для уже существующей policy.

```bash
kolla-ansible host-firewall -i /path/to/multinode \
  --configdir /etc/kolla --mode apply \
  -e @/path/to/host-firewall-apply.yml
```

Inventory, переменные адресов, flags и operator/client sources должны совпадать с отчётом. При `FRESH_REPORT_MISMATCH` заново получить отчёт; при `REPORT_HAS_BLOCKERS` устранить диагностированные причины. Штатный apply проверяет свежий SSH и указанные service checks, сохраняет transaction ID и откатывает собственную policy при ошибке. Его admission и адаптер в этом архиве рассчитаны на Ansible 2.18.x, firewalld 1.3.4 и backend nftables; другая версия требует отдельной проверки совместимости.

**Особенность именно архива от 23.09:** `enable_pvs_firewalld=yes` включает автоматическое применение при deploy/reconfigure. В `_auto_apply()` файла `ansible/action_plugins/kolla_firewall_admission.py` блокеры отчёта заменяются пустым списком, а обязательная проверка ограничивается свежим SSH. Кроме того, `site.yml` останавливает firewalld на время deploy/reconfigure. Поэтому общий `reconfigure` не использовать как способ точечно проверить эту правку; приведённые команды явно задают `host_firewall_auto: false`.

### 6.3. Проверить действующие правила и миграцию

На обоих compute сравнить runtime и permanent:

```bash
sudo firewall-cmd --info-policy=kolla-host-input
sudo firewall-cmd --permanent --info-policy=kolla-host-input
sudo nft list ruleset
```

Нужны rich rules `accept` для выбранного диапазона и правильных адресов до завершающего `drop`. Внешние ACL и другие nftables rules также могут блокировать поток. Добавление порта только в зону `public` не заменяет правку policy: `kolla-host-input` имеет priority `-500` и выполняется до зон. [Порядок firewalld policies](https://firewalld.org/documentation/man-pages/firewalld.policy.html).

Проверка результата — согласованная миграция исправной тестовой ВМ между обоими compute и обратно: статус миграции `completed`, новый host, состояние ВМ `ACTIVE`, отсутствие незавершённого task state и работоспособность гостя. Успешный TCP connect к `16509/16514` либо успешные предварительные события Nova этого не доказывают. В Nova обработчик `live_migration()` передаёт работу фоновому executor; см. [Nova stable/2025.1](https://github.com/openstack/nova/blob/stable/2025.1/nova/compute/manager.py).

Если операция снова зависнет, нужны `libvirtd.log` и QEMU-лог с обоих узлов за интервал самой попытки, а также сетевые соединения в этот момент. `SYN-SENT` и повторные SYN без ответа при существующем listener поддерживают гипотезу фильтрации/потери трафика, но ещё не локализуют конкретный firewall. Отсутствие listener вне миграции нормально. Для ВМ с неудачной отменой сначала установить фактическое состояние домена на обоих hosts; сброс статуса в Nova не завершает зависшую операцию libvirt.

## 7. Границы минимального исправления

`qemu.conf.j2`, `libvirtd.conf.j2`, Nova-конфиг, `rules_from_report()` и транзакционный механизм для описанной правки менять не нужно. Увеличение таймаутов не открывает закрытые порты. `libvirt_tls` также не является заменой разрешений для отдельного потока QEMU.

Если `enable_nova_libvirt_container=false`, добавление потока в секцию с этим enable_flag не сработает: нужно отдельно описать host-managed libvirt. Примеры выше предназначены для контейнерного libvirt этого форка и не покрывают произвольные custom-порты, NAT между compute или иные схемы выбора исходного адреса.

Правка не устраняет ошибки RabbitMQ/MySQL из диагностики и не превращает весь каталог в доказанно полный. Надпись `coverage: complete` в существующем каталоге сама по себе не проверяет наличие всех необходимых потоков.

## 8. Источники и локальная проверка

SHA-256 исходного ZIP:

```text
39ac2c83db8c13454fd3b73e2d3ba3d0473ad9f2e6808442c69f594d0c2379e2
```

Пути в этом документе относятся к корню архива `kolla-ansible-pvs_1.0.0`. Архив, исходные логи и `debug.docx` в публикацию не включены. Общая справка: [Firewall](FIREWALL_ADMIN_GUIDE.md); она описывает более ранний архив от 21.09, поэтому особенности автоматического apply здесь проверены отдельно по архиву от 23.09.

Фрагменты A/B извлечены из этого Markdown и проверены локально на исходной модели и компиляторе форка: **14 сценариев прошли**. Проверены отсутствие потока в исходном каталоге, генерация правил A/B с TLS и без него, IPv6 migration при IPv4 API, общая сеть для B, отсутствующий/неоднозначный адрес, null/unresolved override, ненаблюдаемый адрес, VIP и явный выбор одного из нескольких адресов. Также проверены YAML, уникальность flow IDs, компиляция дополненного Python и синтаксис shell-примеров.

Это автономная проверка функций: Ansible ActionBase и templating заменены тестовыми заглушками, остальные входы — синтетические наблюдения и разрешённые значения переменных. Полный Ansible playbook, установка патча, изменение firewall и живая миграция на стенде не выполнялись. Python/YAML-фрагменты опубликованы как инструкция; исходный форк в этой работе не изменён.
