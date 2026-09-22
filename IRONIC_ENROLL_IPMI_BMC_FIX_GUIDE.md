# Ironic enroll: исправления IPMI/BMC и инструкция по проверке

Дата: 22 сентября 2026 года.

## 1. Краткий вывод и границы документа

В архиве `kolla-ansible-enroll-ironic-patch-3.zip` драйвер IPMI сопоставлен правильно: `driver=ipmi`, `power_interface=ipmitool`, `management_interface=ipmitool`. Главная ошибка находится дальше: при построении `driver_info` роль не добавляет `ipmi_password`, хотя уже прочитала пароль из переменных или Vault.

Дополнительно необходимо согласовать имена переменных логина, проверять драйвер существующей ноды, убрать универсальный Redfish System ID и обеспечить корректную проверку сертификата BMC. Значение `ipmi+redfish` сейчас выбирает Redfish по приоритету; проверки возможностей оборудования и автоматического перехода на IPMI нет.

Это инструкция для внесения изменений. Описанные исправления **не применены к исходникам или работающему стенду**. Проверены исходники и локальные сценарии с заглушками OpenStack/BMC. Успешное подключение к реальному BMC, версии библиотек работающего conductor и состояние его контейнера не проверялись.

Основание анализа:

| Параметр | Значение |
|---|---|
| Архив | `kolla-ansible-enroll-ironic-patch-3.zip` |
| SHA-256 | `12403a06d810cbdfe560bc104472f6fe3b1f38b572f9c9e59212329ab6a37db3` |
| Комментарий ZIP | `5db3c8eed90d69a85e3761ff7f55cb72d7fde94f` — идентификатор из архива, не проверенный remote HEAD |
| Каталог анализа | `sources/kolla-ansible-enroll-ironic-patch-3` |
| Локальная проверка исходного архива | 22 выбранных теста: 19 прошли, 3 завершились ошибками проверок |
| Среда этой проверки | Python 3.13.3, ansible-core 2.18.2, API и CLI OpenStack заменены заглушками |

Все пути далее указаны относительно корня **этого архива**. Номера строк относятся к исходной версии и после правок изменятся. Имена `bmc_pilot`, `compute-pilot`, адрес `192.0.2.12` и домен `bmc-pilot.example.net` — примеры; перед выполнением команд их заменяют значениями стенда.

Навигация: [карта исправлений](#2-что-и-где-исправлять), [IPMI-пароль](#3-исправить-передачу-ipmi-пароля), [логины](#4-согласовать-логины-bmc), [драйверы](#5-выбор-драйвера-и-поддерживаемые-типы), [существующие ноды](#6-существующие-ноды-исключить-ложное-успешное-переключение), [Redfish и CA](#7-redfish-system-id-и-сертификат-bmc), [тесты](#9-локальные-проверки-перед-применением), [применение на стенде](#10-проверка-и-применение-на-стенде).

## 2. Что и где исправлять

| Приоритет | Проблема | Файл и исходные строки | Требуемое изменение |
|---|---|---|---|
| P1 | IPMI-пароль отсутствует в запросе | `ansible/roles/ironic_enroll/tasks/enroll.yml:31–37` | Добавить `ipmi_password` из уже разрешённого словаря паролей |
| P1 | Логин зависит от способа задания inventory | `ansible/ironic-enroll-inventory.yml:21–22`; `ansible/roles/ironic_enroll/tasks/validate.yml:26–35` | Единый внутренний ключ, поддержка старых имён, одинаковые правила для globals и статического inventory |
| P1 | Повторный enroll сохраняет прежний driver/interfaces | `ansible/roles/ironic_enroll/tasks/enroll.yml:177–178` | До обновления проверять соответствие существующей ноды выбранному драйверу и профилю |
| P1 для Redfish | Указан CA-файл, отсутствующий в штатной конфигурации контейнера | `ansible/roles/ironic_enroll/defaults/main.yml:15–16`; `tasks/prepare.yml:14–31`; `tasks/enroll.yml:13–15` | Системное доверие по умолчанию; для собственного CA — явная доставка и mount на всех conductor |
| P2 | Фиксированный Redfish System ID | `ansible/roles/ironic_enroll/defaults/main.yml:19` | Убрать привязку по умолчанию к `System.Embedded.1` |
| P2 | Заявлены vendor-драйверы, не включённые в conductor | `ansible/roles/ironic_enroll/defaults/main.yml:23–61`; `ansible/roles/ironic/templates/ironic.conf.j2:28–30` | Для текущего профиля ограничить поддержку `ipmi` и `redfish` |
| P2 | Отчёт показывает желаемый, а не фактический драйвер | `ansible/roles/ironic_enroll/tasks/verify.yml:28–40` | Читать итоговую ноду из API и выводить её фактические поля |
| P2 | Тесты не проверяют наличие IPMI-пароля | `kolla_ansible/tests/unit/test_ironic_enroll_scaling.py` | Проверять содержимое IPMI `driver_info`, а не только успешный вызов mock-модуля |

Порядок работы: пароль и логин → согласование драйверов → защита существующих нод → Redfish → тесты → одна пилотная нода → остальные BMC.

## 3. Исправить передачу IPMI-пароля

### 3.1. Причина

В `tasks/resolve_passwords.yml` уже создаётся `ironic_enroll_bmc_passwords.ipmi`:

- при `enable_config_vault=true` — из transient-значения `vault_ironic_bmc_ipmi_password`;
- иначе — из `ironic_bmc_ipmi_password`.

Но IPMI-ветка `tasks/enroll.yml` этот ключ не использует. В локальном прогоне для IPMI-ноды получены только `ipmi_address`, `ipmi_username`, `ipmi_priv_level`. Пароль отсутствовал, хотя тестовый inventory его задавал.

Ironic допускает отсутствие IPMI-пароля как параметра, поэтому ошибка может проявиться не при создании записи, а при обращении к BMC, требующему аутентификацию. Контракт драйвера описан в [документации IPMI для Ironic 2025.1](https://docs.openstack.org/ironic/2025.1/admin/drivers/ipmitool.html).

### 3.2. Правка

В `ansible/roles/ironic_enroll/tasks/enroll.yml`, внутри задачи `Compose driver_info for the current BMC host`, заменить IPMI-ветку на:

```jinja2
{% if 'ipmi' in (host_cfg.type | default('')) %}
  {% set _ = di.update({
    'ipmi_address': host_cfg.address,
    'ipmi_username': host_cfg.ironic_enroll_bmc_username_global | default('admin'),
    'ipmi_password': ironic_enroll_bmc_passwords.get('ipmi', ''),
    'ipmi_priv_level': 'ADMINISTRATOR'
  }) %}
{% endif %}
```

Сохранить `no_log: true`, нормализацию `_driver_info` в native mapping и маскирование паролей в обработчике ошибки. Не подставлять в `driver_info` строку `vault://...`: Ironic должен получить значение, уже разрешённое bootstrap-механизмом.

В этом минимальном исправлении пустой пароль остаётся допустимым для совместимости с драйвером. Для стенда с обязательной парольной аутентификацией добавить отдельную проверку непустого значения до обращения к API; её ошибка должна содержать имя BMC и имя отсутствующей переменной, без значения секрета.

### 3.3. Регрессионный тест

В класс `TestIronicEnrollScaling` файла `kolla_ansible/tests/unit/test_ironic_enroll_scaling.py` добавить метод. Он использует существующий fixture: `compute-b` — IPMI, `compute-c` — `ipmi+redfish`, тестовый пароль — `ipmi-secret`.

```python
    def test_ipmi_password_is_forwarded_to_driver_info(self):
        result, _nodes, _managed, records = self._run_enrollment()
        self.assertEqual(0, result.returncode)
        by_name = {record['name']: record for record in records}
        for node_name in ('compute-b', 'compute-c'):
            with self.subTest(node=node_name):
                info = by_name[node_name]['driver_info']
                self.assertEqual('ipmi-secret', info['ipmi_password'])
                self.assertEqual('ADMINISTRATOR', info['ipmi_priv_level'])
```

До правки тест должен падать на отсутствующем ключе; после — проходить. Проверка `compute-c` соответствует текущему поведению роли: она передаёт данные обоих объявленных протоколов, хотя выбирает один драйвер. Если отдельно вводится передача только параметров выбранного драйвера, изменить этот тест и выбор необходимых Vault-секретов согласованно.

## 4. Согласовать логины BMC

### 4.1. Контракт переменных

Использовать следующий контракт:

| Переменная | Назначение |
|---|---|
| `ironic_enroll_bmc_username` | Основной общий логин BMC |
| `ironic_bmc_username` | Совместимость со старой общей/host-переменной |
| `ironic_enroll_bmc_username_global` | Существующий внутренний ключ нормализованной записи; допускается явное задание для BMC |
| `ironic_bmc_username_global` | Совместимость со старым явным ключом BMC |

Название внутреннего ключа содержит `global`, но роль хранит его в записи каждого BMC. Не использовать его как основание для потери индивидуальных значений.

Правило: явный внутренний ключ BMC → старый явный ключ BMC → основной логин → старый логин → `admin`. В `ironic_bmc_hosts` индивидуальный логин задавать через `ironic_enroll_bmc_username_global`; общий — рядом с `ironic_bmc_hosts`.

### 4.2. Defaults

В `ansible/roles/ironic_enroll/defaults/main.yml` заменить строку логина:

```yaml
ironic_enroll_bmc_username: "{{ ironic_bmc_username | default('admin') }}"
```

Это сохраняет старую настройку при отсутствии нового общего имени.

### 4.3. Добавление BMC из globals

В задаче `Add missing BMC endpoints from globals` файла `ansible/ironic-enroll-inventory.yml` заменить выражение логина:

```yaml
ironic_enroll_bmc_username_global: >-
  {{ item.value.ironic_enroll_bmc_username_global
     | default(item.value.ironic_bmc_username_global)
     | default(ironic_enroll_bmc_username
               | default(ironic_bmc_username | default('admin'))) }}
```

Здесь fallback прописан целиком: на первом localhost-play defaults роли ещё могут быть недоступны. Сохранить условие `item.key not in groups.get('bmc', [])`: существующий явный inventory не должен перезаписываться globals.

### 4.4. Статический inventory и нормализация

В `ansible/roles/ironic_enroll/tasks/validate.yml` заменить текущий блок `if/elif`, копирующий логин, следующим фрагментом внутри Jinja-выражения `ironic_bmc_resolved`:

```jinja2
{%- set _ = bmc.update({
  'ironic_enroll_bmc_username_global':
    hostvars[item].ironic_enroll_bmc_username_global
    | default(hostvars[item].ironic_bmc_username_global)
    | default(hostvars[item].ironic_enroll_bmc_username)
    | default(hostvars[item].ironic_bmc_username)
    | default(ironic_enroll_bmc_username)
}) -%}
```

Остальной allowlist полей сохранить. Возвращать `hostvars[item] | combine(...)` нельзя: это вновь начнёт вычислять посторонние переменные Kolla и вернёт прежнюю рекурсию `hostvars`.

После правки добавить в проверку минимальных полей условие:

```yaml
- >-
  (ironic_bmc_resolved[item].ironic_enroll_bmc_username_global
   | default('') | string | trim | length) > 0
```

### 4.5. Изменение тестов

В `test_ironic_enroll_inventory.py` проверку **сгенерированного** `hostvars.bmc_new.ironic_bmc_username_global` заменить на `hostvars.bmc_new.ironic_enroll_bmc_username_global`. Ожидаемое значение оставить `global-user`: это проверяет совместимость со старым `ironic_bmc_username`.

Проверку исходного `hostvars.bmc_existing.ironic_bmc_username_global == 'explicit-user'` сохранить: существующий host не должен изменяться.

В `test_ironic_enroll_validation.py` заменить имя ключа **результата нормализации** на `resolved.ironic_enroll_bmc_username_global`, сохранив ожидаемое значение `operator` и проверку отсутствия вычисления посторонних hostvars.

Дополнительно проверить: новый общий логин; старый общий логин; каждый из двух явных host-ключей; оба общих имени одновременно; отсутствующий логин; пустой логин. Явный host-ключ должен выигрывать, новый общий — выигрывать у старого общего, отсутствие обоих — давать `admin`, пустая строка — понятную ошибку.

## 5. Выбор драйвера и поддерживаемые типы

### 5.1. Сохранить правильные имена IPMI

В `ansible/roles/ironic/templates/ironic.conf.j2` уже правильно заданы:

```ini
enabled_hardware_types = ipmi,redfish
enabled_power_interfaces = ipmitool,redfish
enabled_management_interfaces = ipmitool,redfish
```

Не заменять `ipmitool` на `ipmi` в списках interfaces. Имена hardware type и interface различаются.

### 5.2. Ограничить текущий профиль реально настроенными драйверами

В `ansible/roles/ironic_enroll/defaults/main.yml` для текущего BMC-only профиля оставить:

```yaml
ironic_supported_bmc_types:
  redfish:
    driver: redfish
    power_interface: redfish
    management_interface: redfish
    password_var: ironic_bmc_redfish_password
  ipmi:
    driver: ipmi
    power_interface: ipmitool
    management_interface: ipmitool
    password_var: ironic_bmc_ipmi_password

ironic_driver_priority:
  - redfish
  - ipmi
```

Это согласует enroll со штатным conductor, сохраняя текущий приоритет. Поддержка `ilo5`, `drac5`, `xclarity`, `irmc` требует отдельной проверки конкретной версии Ironic, пакетов образа, hardware types, interfaces и полей `driver_info`. Простое добавление названий в `enabled_hardware_types` не является достаточной правкой.

Перед ограничением проверить inventory: если vendor-типы уже используются с собственными overrides conductor, их нельзя молча переименовывать или отключать. Для такого развёртывания сначала отдельно подтвердить поддерживаемый профиль.

### 5.3. Нормализовать тип и проверять токены

В словаре `bmc` в начале `tasks/validate.yml` заменить выражение для `type`:

```jinja2
'type': ((hostvars[item].type | default('') | lower).split('+')
         | map('trim') | join('+')),
```

В assertion убрать длинную проверку вхождения подстрок `redfish/ipmi/ilo5/...`. Вместо неё, сохранив проверки адреса и непустого типа, добавить:

```yaml
- >-
  (ironic_bmc_resolved[item].type.split('+')
   | difference(ironic_supported_bmc_types.keys() | list)
   | length) == 0
```

Текст ошибки должен перечислять допустимые типы из `ironic_supported_bmc_types`, а не из прежнего фиксированного списка. Так `IPMI` нормализуется, а `ipmi_typo`, `ipmi+unknown` и `ipmi+` отклоняются до OpenStack API.

### 5.4. Как выбирать протокол оператору

Для IPMI-only BMC или BMC с неполным Redfish задавать `type: ipmi`. Для проверенного Redfish — `type: redfish`. Составной тип сохраняется для совместимости, но означает **выбор по приоритету**, а не резервирование.

Изменение общего `ironic_driver_priority` влияет на все составные записи. Для одной ноды предпочтительнее изменить её `type`. Для уже существующей ноды этого недостаточно: действуют ограничения следующего раздела.

## 6. Существующие ноды: исключить ложное успешное переключение

### 6.1. Текущее поведение

`updateable_attributes: [driver_info]` разрешает обновлять только реквизиты подключения. Это соответствует [контракту openstack.cloud.resource](https://docs.ansible.com/projects/ansible/latest/collections/openstack/cloud/resource_module.html). Поля `driver`, `power_interface`, `management_interface`, `network_interface` и `extra` при повторном enroll автоматически не приводятся к значениям из `attributes`.

Поэтому нода, созданная с Redfish, не станет IPMI-нодой после изменения inventory. Если она уже `manageable`, текущая проверка может завершиться успешно и показать желаемый драйвер вместо фактического.

### 6.2. Проверка перед обновлением

В `ansible/roles/ironic_enroll/tasks/enroll.yml` после проверки владельца существующей ноды и **до** `Create or reconcile the Ironic node...` добавить:

```yaml
- name: Reject existing nodes with a different enrollment profile
  ansible.builtin.assert:
    that:
      - >-
        ironic_enroll_existing_node[profile_field.key]
        | default('') == profile_field.value
    fail_msg: >-
      Existing Node {{ ironic_bmc_resolved[inventory_hostname]
      .ironic_bmc_resolved_attached_host }} has incompatible
      {{ profile_field.key }}. Expected {{ profile_field.value }};
      actual {{ ironic_enroll_existing_node[profile_field.key]
      | default('undefined') }}. Explicit migration is required.
  loop:
    - key: driver
      value: "{{ ironic_bmc_resolved[inventory_hostname].ironic_bmc_resolved_driver }}"
    - key: power_interface
      value: "{{ ironic_bmc_resolved[inventory_hostname].ironic_bmc_resolved_power_interface }}"
    - key: management_interface
      value: "{{ ironic_bmc_resolved[inventory_hostname].ironic_bmc_resolved_management_interface }}"
    - key: network_interface
      value: noop
    - key: inspect_interface
      value: no-inspect
  loop_control:
    loop_var: profile_field
    label: "{{ profile_field.key }}"
  when: ironic_enroll_existing_node | length > 0
```

Сохранить существующие ограничения по provision state и `extra.managed_by=ansible`. Не добавлять driver/interfaces в `updateable_attributes` без отдельной процедуры миграции. Маркер `managed_by=ansible` тоже не является разрешением на автоматическую смену протокола.

Ноды в `verifying` проверять после завершения текущего перехода: не менять реквизиты подключения одновременно с выполняющимся `manage`. Гонку, когда другой процесс уже перевёл ноду в `verifying/manageable`, продолжать обрабатывать отдельно от изменения конфигурации.

### 6.3. Проверка и отчёт после enroll

В `tasks/verify.yml` после ожидания `manageable` добавить чтение фактической записи:

```yaml
- name: Read the final Ironic node record
  openstack.cloud.baremetal_node_info:
    cloud: "{{ ironic_enroll_cloud }}"
    interface: "{{ ironic_enroll_api_interface }}"
    name: "{{ ironic_bmc_resolved[inventory_hostname].ironic_bmc_resolved_attached_host }}"
  register: ironic_enroll_verified_result
  changed_when: false
  no_log: true

- name: Require exactly one final Ironic node
  ansible.builtin.assert:
    that:
      - ironic_enroll_verified_result.nodes | default([]) | length == 1
    fail_msg: "Expected exactly one Ironic node after enrollment."

- name: Select the final Ironic node
  ansible.builtin.set_fact:
    ironic_enroll_verified_node: "{{ ironic_enroll_verified_result.nodes | first }}"
  no_log: true

- name: Validate the actual final driver and state
  ansible.builtin.assert:
    that:
      - ironic_enroll_verified_node.provision_state == 'manageable'
      - >-
        ironic_enroll_verified_node.driver ==
        ironic_bmc_resolved[inventory_hostname].ironic_bmc_resolved_driver
      - >-
        ironic_enroll_verified_node.power_interface ==
        ironic_bmc_resolved[inventory_hostname].ironic_bmc_resolved_power_interface
      - >-
        ironic_enroll_verified_node.management_interface ==
        ironic_bmc_resolved[inventory_hostname].ironic_bmc_resolved_management_interface
      - ironic_enroll_verified_node.network_interface == 'noop'
      - ironic_enroll_verified_node.inspect_interface == 'no-inspect'
    fail_msg: "The final Ironic node does not match the enrollment profile."
```

В существующей задаче `Report enrollment result...` выводить `driver`, `power_interface`, `management_interface`, `provision_state` из `ironic_enroll_verified_node`. Поле из inventory назвать `requested_bmc_type`, чтобы не выдавать его за подтверждённую аппаратную характеристику.

Эта проверка подтверждает запись в API, но не доказывает свежий доступ к BMC. `manageable` и кэшированный `power_state` сами по себе недостаточны после изменения логина/пароля; проверка подключения описана в разделе 10.

### 6.4. Если реально нужно перевести существующую ноду с Redfish на IPMI

Это отдельное изменение состояния, а не обычный повторный enroll:

1. Зафиксировать UUID, имя, состояние, фактические interfaces, `extra`, связь с HA/PowerOps и текущие реквизиты в принятом защищённом хранилище. Не выгружать открытые пароли в общий отчёт.
2. Убедиться, что нода не `active/available`, не участвует в незавершённой операции, не имеет назначенного instance/allocation и допускает изменение по правилам данной версии Ironic. Состояние `verifying` сначала должно завершиться.
3. На conductor проверить IPMI-аутентификацию чтением `chassis power status` и доступность hardware type `ipmi`.
4. Подготовить согласованное изменение driver, power/management interfaces и необходимых `driver_info`. Проверить, что остальные interfaces совместимы с новым hardware type. Не полагаться на один `type: ipmi` в inventory.
5. Выполнить миграцию по регламенту стенда, сохранив UUID, затем сверить фактическую запись и доступ к BMC. Автоматическое удаление/пересоздание ноды в эту инструкцию не входит: это может разорвать внешние ссылки.
6. Только после согласования фактического профиля повторить исправленный enroll.

Универсальная команда переключения здесь намеренно не задана: неизвестны текущие interfaces, потребители ноды и версия работающего API. Для безопасного повторного enroll достаточно проверки несовпадения из раздела 6.2.

## 7. Redfish: System ID и сертификат BMC

### 7.1. Убрать обязательный vendor-specific System ID

В `ansible/roles/ironic_enroll/defaults/main.yml` заменить:

```yaml
ironic_enroll_default_redfish_system_id: ""
```

В `tasks/enroll.yml` упростить вычисление `sid`, убрав ссылку на старую резервную переменную:

```jinja2
{% set sid = host_cfg.redfish_system_id
     | default(ironic_enroll_default_redfish_system_id) %}
{% if sid | length > 0 %}
  {% set _ = di.update({'redfish_system_id': sid}) %}
{% endif %}
```

Для BMC с единственным ComputerSystem Ironic может выбрать его автоматически. Если систем несколько, передать явный `redfish_system_id`, полученный из `/redfish/v1/Systems`; нельзя всегда подставлять `System.Embedded.1`. Это следует из [контракта Redfish driver](https://docs.openstack.org/ironic/2025.1/admin/drivers/redfish.html).

### 7.2. По умолчанию использовать системное доверие

Добавить в defaults роли:

```yaml
ironic_enroll_redfish_verify_ca: true
ironic_enroll_copy_bmc_ca: false
ironic_enroll_bmc_ca_source: "{{ node_config }}/certificates/bmc-ca.pem"
```

В `tasks/enroll.yml` заменить вычисление `redfish_verify_ca`:

```jinja2
{% set redfish_verify_ca = host_cfg.redfish_verify_ca
     if host_cfg.redfish_verify_ca is defined
     else ironic_enroll_redfish_verify_ca %}
```

Явное host-значение `false` сохраняется как boolean; не применять здесь `default(..., true)`, который затрёт `false`. Для нормального рабочего профиля использовать системный trust store или собственный CA. Отключение проверки сертификата не исправляет доставку CA.

Системное доверие работает только если CA BMC уже доверен внутри образа/container trust store. HTTPS-адрес должен соответствовать SAN сертификата. Наличие внутреннего DNS-имени само по себе не устанавливает доверие.

### 7.3. Собственный CA: копирование и bind mount

Для собственного CA остаются два разных пути:

| Место | Переменная | Пример |
|---|---|---|
| Deployment host: исходный файл | `ironic_enroll_bmc_ca_source` | `/etc/kolla/certificates/bmc-ca.pem` |
| Каждый conductor host: файл для mount | `ironic_enroll_bmc_ca_host_path` | `/etc/kolla/certificates/bmc-ca.pem` |
| Container: путь, передаваемый Ironic | `ironic_enroll_bmc_ca_container_path` | `/etc/ironic/bmc-ca.pem` |

В defaults роли заменить host path на `{{ node_config_directory }}/certificates/bmc-ca.pem`. `node_config` относится к каталогу конфигурации на deployment host, `node_config_directory` — к каталогу на управляемых узлах; при нестандартном `--configdir` они могут различаться.

В `tasks/prepare.yml`:

1. У обеих существующих задач установить `when: ironic_enroll_copy_bmc_ca | bool`.
2. У задачи copy убрать `failed_when: false` и lookup `first_found`.
3. Использовать `src: "{{ ironic_enroll_bmc_ca_source }}"` и существующий `dest: "{{ ironic_enroll_bmc_ca_host_path }}"`.
4. Сохранить `become: true`, `run_once: true` и цикл по conductor. Если CA явно включён, отсутствие исходного файла или ошибка копирования должны прерывать подготовку.

Для этого варианта в `globals.yml` или существующем подходящем файле `globals.d/*.yml` задать:

```yaml
ironic_enroll_copy_bmc_ca: true
ironic_enroll_bmc_ca_source: "{{ node_config }}/certificates/bmc-ca.pem"
ironic_enroll_bmc_ca_host_path: "{{ node_config_directory }}/certificates/bmc-ca.pem"
ironic_enroll_bmc_ca_container_path: /etc/ironic/bmc-ca.pem
ironic_enroll_redfish_verify_ca: /etc/ironic/bmc-ca.pem

ironic_conductor_extra_volumes: >-
  {{ ironic_extra_volumes + [
    ironic_enroll_bmc_ca_host_path ~ ':' ~
    ironic_enroll_bmc_ca_container_path ~ ':ro'
  ] }}
```

Если `ironic_conductor_extra_volumes` уже задан, дополнить его существующие элементы. Нельзя потерять mounts Vault или другие обязательные volumes. Не дублировать этот ключ в нескольких globals-файлах с разными значениями.

Этот вариант использует прямой read-only bind mount и не требует добавлять тот же файл ещё и в `ironic-conductor.json.j2`. Проверить существующий шаблон и volumes всё равно необходимо: в исходном архиве штатного mount/copy в `/etc/ironic/bmc-ca.pem` нет.

До первого enroll с собственным CA подготовить файл на всех conductor, затем применить mount. Для отдельной подготовки можно создать в корне исправленного checkout файл `prepare-ironic-bmc-ca.yml`:

```yaml
---
- name: Prepare custom BMC CA before conductor reconfiguration
  hosts: localhost
  gather_facts: false
  vars_files:
    - ansible/group_vars/all.yml
  tasks:
    - name: Copy the explicitly configured BMC CA
      ansible.builtin.include_role:
        name: ironic_enroll
        tasks_from: prepare
```

Запуск из checkout с установленными зависимостями и реальным inventory:

```bash
export ANSIBLE_ROLES_PATH="$PWD/ansible/roles"
ansible-playbook -i /srv/kolla/inventory \
  -e @/etc/kolla/globals.yml \
  -e @/etc/kolla/globals.d/ironic-bmc.yml \
  prepare-ironic-bmc-ca.yml
```

Пути здесь — пример. Прямой `ansible-playbook` сам не загружает все `globals.d`: передать реально используемые файлы в том же порядке, что Kolla CLI. Если `globals.d/ironic-bmc.yml` отсутствует, убрать этот аргумент; при нестандартном configdir передать `CONFIG_DIR` и фактические пути. Подготовка копирует CA на hosts, но ещё не изменяет запущенный контейнер.

Далее применяется `reconfigure --tags ironic` из раздела 10. Новые mounts требуют пересоздания/перезапуска контейнера; это отдельный этап изменения работающего сервиса. Роль enroll сама такой mount не добавляет.

Для каждого conductor проверить после reconfigure:

```bash
docker exec --user ironic ironic_conductor \
  test -r /etc/ironic/bmc-ca.pem
docker inspect ironic_conductor --format '{{json .Mounts}}'
```

Для Podman заменить executable. При ротации CA повторять доставку на все conductor и проверять, что контейнер видит новую версию; bind mount отдельного файла после атомарной замены файла на host может требовать пересоздания контейнера.

## 8. Inventory и параметры IPMI

Пример globals после исправления логина:

```yaml
ironic_enroll_bmc_username: operator
ironic_bmc_hosts:
  bmc_pilot:
    address: 192.0.2.12
    type: ipmi
    attached_host: compute-pilot
    ironic_enroll_bmc_username_global: operator
```

Пароль задаётся отдельно от этой записи:

- Vault mode: существующий bootstrap-механизм должен получить **реальное значение** `vault_ironic_bmc_ipmi_password`;
- non-Vault mode: задать `ironic_bmc_ipmi_password` через принятый защищённый файл переменных; он должен быть загружен в playbook.

Добавление нового `bmc_password` или `password` внутрь `ironic_bmc_hosts` не поможет: такие поля роль не читает. Текущая схема содержит один пароль на тип BMC. Поддержка разных паролей для двух IPMI-устройств требует отдельного изменения разрешения секретов; данный документ её не объявляет реализованной.

В текущем коде привилегия фиксирована как `ADMINISTRATOR`; порт, cipher suite и версия IPMI не передаются из inventory. Если стенду нужны нестандартные значения, добавить их согласованно в три места:

1. `ironic-enroll-inventory.yml`: передать `ipmi_port`, `ipmi_protocol_version`, `ipmi_cipher_suite`, `ipmi_priv_level` из записи globals через `default(omit)`.
2. `tasks/validate.yml`: явно скопировать эти поля в allowlist и проверить тип/допустимые значения.
3. `tasks/enroll.yml`: перенести явно заданные параметры в `driver_info`; для `ipmi_priv_level` использовать host-значение с fallback `ADMINISTRATOR`.

Это условное расширение, а не обязательная правка для всех BMC. Не менять cipher suite или privilege level без проверки поддержки устройством и установленным ipmitool. Имена параметров и ограничения перечислены в [руководстве IPMI driver](https://docs.openstack.org/ironic/2025.1/admin/drivers/ipmitool.html).

## 9. Локальные проверки перед применением

### 9.1. Что уже проверено в исходном архиве

Из 22 выбранных offline-тестов 19 прошли. Падения:

| Тест | Причина |
|---|---|
| `test_globals_add_only_missing_bmc_hosts` | Тест ожидает старый ключ логина; код создаёт новый. Кроме расхождения имён, прежний общий логин не используется в add_host |
| `test_validation_does_not_resolve_unrelated_host_variables` | Задачи нормализации выполняются, но assertion результата обращается к прежнему ключу логина |
| `test_driver_info_is_native_mapping_with_expected_redfish_values` | Тест ожидает отсутствие System ID у составного типа, defaults добавляет `System.Embedded.1` |

Таким образом, второе падение не доказывает возврат рекурсии `hostvars`: оно происходит на последующей проверке имени ключа. Удалять этот тест нельзя.

Четыре теста `test_ironic_enroll_command.py` в этот локальный запуск не входили: в использованном Python-окружении отсутствовали CLI-зависимости. Это не полный тестовый прогон проекта и не подтверждение работоспособности BMC.

Первый запуск из рабочего пути с двоеточиями дал дополнительные ошибки поиска роли: Ansible разделяет `ANSIBLE_ROLES_PATH` по `:`. Приведённый результат 19/22 получен после повторного запуска из копии без двоеточий. Для воспроизведения использовать, например, `/srv/src/kolla-ansible-enroll-review`.

### 9.2. Запуск тестов

Использовать виртуальное окружение проекта с `requirements.txt`, `test-requirements.txt` и установленным пакетом Kolla. При необходимости воспроизводить окружение по ограничениям `2025.1`, указанным в `tox.ini`; не обновлять зависимости рабочего deployment-окружения ради этого теста.

Из корня checkout:

```bash
python -m unittest discover \
  -s kolla_ansible/tests/unit \
  -p 'test_ironic_enroll_*.py' -v
```

Если тестируется минимальная среда без CLI-зависимостей, воспроизвести именно исходную выбранную группу:

```bash
python -m unittest \
  kolla_ansible.tests.unit.test_ironic_enroll_environment \
  kolla_ansible.tests.unit.test_ironic_enroll_inventory \
  kolla_ansible.tests.unit.test_ironic_enroll_passwords \
  kolla_ansible.tests.unit.test_ironic_enroll_scaling \
  kolla_ansible.tests.unit.test_ironic_enroll_validation -v
```

Для sandbox/ограниченного пользователя задать `ANSIBLE_LOCAL_TEMP`, `ANSIBLE_REMOTE_TEMP` и `ANSIBLE_LOG_PATH` в доступном временном каталоге. Для проверки snippets достаточно локальных тестовых реквизитов; реальные пароли и адреса туда не добавлять.

### 9.3. Что дополнительно покрыть

| Сценарий | Ожидаемый результат |
|---|---|
| Новый IPMI BMC, direct password | В запросе есть правильные address, username, password; выбран `ipmi/ipmitool/ipmitool` |
| Новый IPMI BMC, Vault password | В запрос попало transient-значение, а не имя ключа и не URI секрета |
| Новый и старый логин, globals и static inventory | Выполняется приоритет из раздела 4, явный inventory не перезаписан |
| `IPMI`, `ipmi`, `ipmi+redfish`, ошибочные типы | Нормализация и выбор предсказуемы; неизвестный токен отклонён |
| Существующий `manageable` IPMI с тем же профилем | Реквизиты обновляются, повторный `manage` не вызывается |
| Существующий Redfish, requested IPMI | Ошибка до изменения `driver_info`, старую ноду роль не переводит автоматически |
| `active/available`, чужой `managed_by` | Существующие проверки запрещают обновление |
| Один Redfish ComputerSystem без ID | `redfish_system_id` не передаётся; нет навязанного `System.Embedded.1` |
| Явные System ID, CA-path и boolean false | Значения сохраняются с правильными типами |
| Собственный CA включён, файл отсутствует | Подготовка завершается ошибкой, а не продолжает enroll |
| Собственный CA не включён | Подготовка не требует пользовательского CA-файла |
| API вернул другой драйвер после операции | Итоговая проверка отклоняет результат; отчёт не выдаёт requested driver за actual |
| Ошибка SDK/resource | В сообщении остаётся полезная причина, тестовые пароли заменены на `[REDACTED]` |

После добавления проверок существующих нод расширить mock `baremetal_node_info` в `test_ironic_enroll_scaling.py`: сейчас он возвращает только имя, state и `extra`. Mock должен хранить и возвращать driver/interfaces созданной записи, иначе новые проверки будут падать из-за неполной заглушки.

Тест `test_tagged_enrollment_runs_conductor_preparation_tasks` после введения `ironic_enroll_copy_bmc_ca` должен явно включать эту переменную и создавать временный CA-файл. Сохранить отдельный сценарий выключенной подготовки. После смены defaults System ID существующее ожидание `assertNotIn('redfish_system_id', ...)` должно проходить без ослабления теста.

## 10. Проверка и применение на стенде

### 10.1. Проверить, откуда реально запускается Kolla

Правки в распакованном архиве не влияют на отдельно установленный пакет. В активном deployment-окружении выполнить:

```bash
command -v kolla-ansible
kolla-ansible --version
python -c 'from kolla_ansible import utils; print(utils.get_data_files_path("ansible", "enroll-ironic.yml"))'
kolla-ansible enroll-ironic --help
```

`python` должен относиться к тому же virtualenv, что `kolla-ansible`. Установить исправленную сборку принятым способом и проверить именно фактические файлы роли. В ZIP нет гарантии git metadata: не рассчитывать на `pip install -e .` из голого архива без проверки принятой в проекте сборки/version metadata.

Исправления `ironic_enroll` выполняются на deployment host. Замена его YAML-задач сама по себе не требует пересборки образа conductor. Изменение включённых драйверов, trust store образа или mounts — отдельные изменения контейнера.

### 10.2. Прочитать состояние Ironic

В том же административном окружении, где доступен `clouds.yaml`:

```bash
export OS_CLIENT_CONFIG_FILE=/etc/kolla/clouds.yaml
export OS_CLOUD=kolla-admin
export OS_INTERFACE=internal
export OS_SYSTEM_SCOPE=
IRONIC_NODE=compute-pilot

openstack baremetal driver list
openstack baremetal node show "$IRONIC_NODE" -f yaml \
  -c uuid -c name -c driver -c power_interface -c management_interface \
  -c network_interface -c inspect_interface -c provision_state \
  -c target_provision_state -c power_state -c last_error -c extra
```

Если нода ещё не создана, `node show` ожидаемо вернёт Not Found; это не повод создавать её отдельной командой в обход роли. `last_error` может содержать подробности подключения: перед передачей вывода третьим лицам проверить его на секреты.

Список драйверов API показывает доступность в deployment; дополнительно проверить runtime config всех conductor, которые могут обслуживать эту ноду. Наличие драйвера в одном conductor не доказывает однородность остальных.

На каждом соответствующем conductor host:

```bash
docker exec ironic_conductor sh -c \
  'grep -E "^(enabled_hardware_types|enabled_power_interfaces|enabled_management_interfaces|enabled_network_interfaces) *=" /etc/ironic/ironic.conf'
docker exec ironic_conductor ipmitool -V
```

### 10.3. Проверить BMC без изменения питания

Проверку выполнять из сети/контейнера conductor, а не только с ноутбука или deployment host. Для IPMI открыть shell в контейнере:

```bash
docker exec -it --user ironic ironic_conductor bash
```

В открытом shell выполнить:

```bash
BMC_ADDRESS=192.0.2.12
BMC_USER=operator
ipmitool -I lanplus -H "$BMC_ADDRESS" -U "$BMC_USER" \
  -L ADMINISTRATOR -a chassis power status
```

`-a` запрашивает пароль интерактивно. Для нестандартного порта/протокола/привилегии использовать согласованные параметры устройства. Ожидается `Chassis Power is on` или `off`. Этот запрос читает состояние питания. `ping` и проверка TCP-порта не подтверждают работу IPMI: обычный IPMI over LAN использует UDP.

Для Redfish получить список систем из того же сетевого контекста:

```bash
BMC_URL=https://bmc-pilot.example.net
BMC_USER=operator
curl --fail --silent --show-error \
  --cacert /etc/ironic/bmc-ca.pem --user "$BMC_USER" \
  "$BMC_URL/redfish/v1/Systems"
```

При системном доверии убрать `--cacert`; curl запросит пароль интерактивно. Проверить `Members[].@odata.id`, затем GET конкретной системы. Успешный curl подтверждает HTTP/TLS, но не полную совместимость ответа с установленным Sushy. При ошибке разбора ComputerSystem проверить версию Sushy именно в работающем образе:

```bash
docker exec ironic_conductor python -c \
  'from importlib.metadata import version; print(version("sushy"))'
```

Не считать изменение Dockerfile или build recipe доказательством обновления уже запущенного контейнера.

### 10.4. Применить настройки conductor, если они действительно менялись

Для исправления только пароля/логина в роли этот этап не нужен. Если изменены mounts CA или конфигурация conductor, сначала обеспечить исходные файлы на hosts, затем в согласованное окно выполнить:

```bash
kolla-ansible reconfigure -i /srv/kolla/inventory --tags ironic
```

Команда изменяет конфигурацию и может перезапускать сервисы Ironic. Проверить mounts, читаемость CA и фактические enabled interfaces после её завершения. Не включать этот этап в обычный диагностический запуск.

### 10.5. Выполнить enroll одной пилотной ноды

После успешных локальных тестов, проверки реквизитов и фактического профиля ноды:

```bash
kolla-ansible enroll-ironic -i /srv/kolla/inventory \
  --limit 'localhost,bmc_pilot'
```

`bmc_pilot` — имя BMC в Ansible, `compute-pilot` — имя ноды в Ironic; они не взаимозаменяемы. `localhost` нужен для построения runtime inventory и Vault bootstrap. Эта команда создаёт/обновляет запись и может запускать `manage`; она не является read-only проверкой.

Ограничение `--limit` не обязательно ограничивает делегированные задачи: текущая подготовка CA проходит по всем `groups['ironic-conductor']`. Vault scope также вычисляется по BMC inventory. При пилотном запуске учитывать этот охват; для полной изоляции использовать отдельный пилотный набор globals/inventory с необходимыми conductor.

Для составных типов bootstrap запрашивает секреты всех объявленных токенов, даже когда выбран один драйвер. Поэтому для IPMI-пилота задавать `type: ipmi`, а не оставлять `ipmi+redfish` в надежде на автоматический fallback.

После enroll повторить `node show` из раздела 10.2 и выполнить:

```bash
openstack baremetal node validate "$IRONIC_NODE"
```

Для BMC-only профиля отдельно оценивать `power` и `management`; ошибки deploy/boot из-за отсутствующих параметров развёртывания ОС не равны ошибке IPMI. `node validate` проверяет interfaces, но не заменяет свежую проверку подключения к BMC. Формат команд приведён в [справочнике python-ironicclient](https://docs.openstack.org/python-ironicclient/latest/cli/osc/v1/index.html).

Повторить enroll той же пилотной ноды: UUID должен сохраниться, driver/interfaces — остаться правильными, `manageable` — сохраниться, повторный `manage` для уже manageable ноды — не вызываться. Затем расширять запуск на остальные BMC.

## 11. Критерии готовности и действия при ошибке

Исправление можно считать проверенным на выбранном стенде, когда одновременно выполнено следующее:

- [ ] Проверена фактически установленная версия роли, а не только распакованный архив.
- [ ] Локальные тесты покрывают пароль, логин, выбор драйвера и несовпадающий существующий профиль.
- [ ] IPMI-пароль передаётся в `driver_info`, значения секретов не выводятся в обычный лог.
- [ ] Прямое чтение состояния BMC из контекста conductor проходит с теми же параметрами.
- [ ] Фактические driver/interfaces соответствуют выбранному протоколу.
- [ ] Для Redfish подтверждены System ID и trust store/CA на всех нужных conductor.
- [ ] Пилотная нода достигает `manageable`; повторный enroll сохраняет UUID и выбранный профиль.
- [ ] Ошибка профиля существующей ноды обнаруживается до изменения её `driver_info`.

Если проверка не проходит, остановить расширение на остальные BMC и определить слой ошибки:

| Симптом | Что проверить первым |
|---|---|
| Прямой ipmitool не проходит | Маршрут/ACL UDP, BMC user/password, LAN/IPMI enable, privilege, protocol/cipher |
| Прямой ipmitool проходит, enroll не проходит | Фактический `driver_info`, выбранный драйвер, ошибка Ironic, используемый conductor |
| После `type: ipmi` фактически остался Redfish | Ограничение обновляемых полей; нужна проверка/отдельная миграция существующей записи |
| Ошибка CA path | Наличие mount, права пользователя ironic, версия файла внутри контейнера |
| Redfish resource Not Found | Реальный `Members[].@odata.id`, отсутствие навязанного vendor System ID |
| Ошибка разбора Redfish/Sushy | Полный ComputerSystem payload и версия клиента в работающем контейнере |
| Unsupported driver/interface | Runtime config conductor, образ и список hardware types/interfaces |

Откат файла роли не отменяет уже сделанные изменения в Ironic API. Возврат driver_info/логина/пароля выполнять по зафиксированной предыдущей конфигурации и принятому порядку работы с секретами. Возврат mounts/config conductor также требует применения прежней конфигурации и последующей проверки контейнера. Ноду автоматически не удалять, питание для диагностики не переключать.

## 12. Что сохранить из уже исправленного кода

Сохранить allowlist BMC-полей вместо копирования всех `hostvars`; преобразование `_resolved` и `_driver_info` в mapping; `OS_SYSTEM_SCOPE: ""` в enrollment-play; обработку конкурентного перехода в `verifying/manageable`; ограничения для `active/available` и чужих нод; маскирование паролей; выполнение подготовки conductor отдельно от serial batches BMC.

Именно эти элементы уже устраняют прежние проблемы роли. Их не требуется заменять ради исправления передачи IPMI-пароля.
