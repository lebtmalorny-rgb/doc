# Glance и FC/iSCSI multipath: применимость, исправления и проверка

Дата проверки: **13.10.2026**. Основа: предоставленный `kolla-ansible-pvs.zip`
из ветки `stable/2025.1` и исходники upstream `glance_store` той же ветки.
Это инструкция по предлагаемым изменениям. Код форка и инфраструктура не изменены.

## Что делать

**Включать Glance в исправление нужно, если он сам читает или записывает образы
в Cinder store на FC/iSCSI с multipath.** Сам факт наличия Cinder в облаке
этого не доказывает.

1. Установить фактический store нужных образов и протокол его Cinder backend.
2. Проверить на каждом обслуживающем Glance-узле SAN-доступ, устройства,
   единственный управляющий `multipathd` и права контейнера.
3. Добавить управляемую доставку `multipath.conf` в `glance_api` — раздел 5.
   Если FC-доступ контейнера ещё не настроен, также выполнить раздел 6.
4. Включить клиентский multipath в секции нужного Glance store — раздел 7.
5. Применить на пилотном наборе узлов и проверить загрузку/скачивание образа,
   очистку подключения и повторный `reconfigure` — разделы 8–9.

Подробности общего фикса Nova/Cinder остаются в
[основной инструкции](KOLLA_MULTIPATH_NOVA_CINDER_FIX.md).

**Готовые upstream-правки для Glance есть, но они закрывают отдельные части:**
№961235 — привилегии и доступ к устройствам; №978863 — конфигурацию Cinder store.
Готовый отдельный патч доставки `multipath.conf` в Glance поиском не подтверждён.
Статусы, ограничения переноса и ссылки — в разделе 11.

## 1. Когда это та же проблема

| Сценарий | Кто подключает блочное устройство | Нужен `multipath.conf` внутри Glance |
|---|---|---|
| Glance хранит образы в локальном каталоге или NFS | Glance работает с файлами | Для этого сценария — нет |
| Glance использует собственный RBD, S3 или Swift store | Glance использует соответствующий клиент | DM-multipath для этого сценария не нужен |
| Cinder скачивает образ из обычного Glance store по HTTP | Том назначения подключает Cinder | Из-за этой операции — нет |
| Glance Cinder store хранит образ в FC/iSCSI-томе | `glance_store` вызывает os-brick на Glance-узле | Да, при использовании multipath |
| Glance Cinder store использует NFS/RBD backend | Зависит от соответствующего коннектора | Нельзя автоматически переносить требования FC/iSCSI |

Если каталог Glance расположен на файловой системе поверх SAN-LUN, смонтированной
хостом, multipath требуется на хосте. Glance, получающий готовый каталог,
не становится из-за этого клиентом os-brick.

Не каждая операция с Cinder store обязательно читает данные через Glance:
клонирование на СХД и другие оптимизированные пути могут обходить передачу данных.
Поэтому быстрый запуск ВМ из образа сам по себе не проверяет этот сценарий.

## 2. Как работает Cinder store в Glance

Для обычного чтения/записи образа в Cinder store последовательность такая:

```text
glance_api -> glance_store -> Cinder API: создать/обновить attachment
glance_store -> os-brick НА GLANCE-УЗЛЕ: подключить FC/iSCSI-том
glance_store -> прочитать/записать данные -> os-brick: отключить устройство
glance_store -> Cinder API: завершить очистку attachment
```

Это видно в upstream-методе `_open_cinder_volume()`: он получает свойства
локального коннектора, вызывает `attachment_update`, затем `connect_volume`,
читает/пишет устройство и выполняет disconnect. Для `multiattach` используется
отдельный менеджер состояния подключений. [Исходник `glance_store`](https://github.com/openstack/glance_store/blob/stable/2025.1/glance_store/_drivers/cinder/store.py).

Следовательно, исправление только `cinder_volume` не обеспечивает готовность
`glance_api`: это разные процессы, контейнеры, а нередко и разные хосты.
На одном хосте DM-устройства общие, но файлы конфигурации контейнеров раздельные.

## 3. Что обнаружено в вашем форке

Пути ниже указаны относительно распакованного `kolla-ansible-pvs/`.

| Место | Что следует из исходников |
|---|---|
| `ansible/roles/glance/tasks/config.yml` | Задачи доставки `multipath.conf` нет |
| `ansible/roles/glance/templates/glance-api.json.j2` | Записи `/etc/multipath.conf` в `config_files` нет |
| `ansible/roles/glance/defaults/main.yml`, `glance_backends` | Store типа `cinder` добавляется при `enable_cinder` |
| Там же, `glance_default_backend` | По умолчанию выбирается VMware, RBD, S3 или file; наличие Cinder store не означает его выбор |
| Там же, `glance-api.privileged` | Зависит от `enable_cinder` и флагов iSCSI/Ceph; отдельного условия для FC нет |
| Там же, `glance_api_default_volumes` | Host `/dev` и `iscsi_info` автоматически подключаются при Cinder iSCSI |
| `ansible/inventory/multinode` | Glance находится на `control`, а `multipathd` и `iscsid` — на `compute`/`storage`; фактическое пересечение нужно проверить |
| `ansible/group_vars/all.yml`, `glance_api_hosts` | При локальном file store возможен выбор только первого Glance-узла |

**Подтверждён пробел в стандартной роли, но не состояние работающего контейнера.**
Пользовательские mounts, образы и overrides могли уже доставить файл и права.
Точная установленная версия `glance_store` также пока не проверена:
архива Glance/glance_store среди предоставленных исходников нет.

## 4. Проверки до изменения конфигурации

Команды приведены для Podman и стандартных имён контейнеров. Для Docker заменить
`podman` на `docker`. Выполнять на реальном Glance-узле с соответствующими правами.

### 4.1. Какие stores настроены

Команда выводит только параметры выбора хранилища и multipath, без паролей:

```bash
podman exec -i -u root glance_api python3 - <<'PY'
import configparser
from importlib import metadata

cfg = configparser.ConfigParser(interpolation=None, strict=False)
loaded = cfg.read('/etc/glance/glance-api.conf')
if not loaded:
    raise SystemExit('glance-api.conf not read')
backends = cfg.defaults().get('enabled_backends', '')
print('enabled_backends =', backends or '<not set>')
print('default_backend =', cfg.get('glance_store', 'default_backend', fallback='<not set>'))
for item in backends.split(','):
    store, separator, driver = item.strip().partition(':')
    if separator and driver.strip() == 'cinder':
        print('Cinder store:', store)
        for option in ('cinder_volume_type', 'cinder_use_multipath', 'cinder_enforce_multipath'):
            print(' ', option, '=', cfg.get(store, option, fallback='<not set>'))
for package in ('glance', 'glance_store', 'os-brick'):
    try:
        print(package, metadata.version(package))
    except metadata.PackageNotFoundError:
        print(package, '<metadata not found>')
PY
```

Это чтение одного файла, а не доказательство эффективной конфигурации процесса.
Если используются дополнительные `--config-file`/`--config-dir`, учесть их
порядок и overrides. `<not set>` не означает `true`: в проверенном upstream
оба multipath-параметра Glance имеют default `False`.

Затем определить store конкретного образа: `stores`/location, где они доступны
по политике API, либо записи Glance и соответствующий image-volume в Cinder.
Для multi-store backend по умолчанию недостаточен: образ может находиться
в другом store. По volume type и Cinder backend установить реальный протокол.

### 4.2. Устройства, демон и конфигурация

```bash
hostname -f
podman ps --format '{{.Names}} {{.Image}}'
podman inspect --format '{{.HostConfig.Privileged}}' glance_api
podman inspect --format '{{json .Mounts}}' glance_api
pgrep -a -x multipathd
systemctl is-active multipathd.service multipathd.socket
podman exec -u root glance_api ls -ld /dev/mapper /sys/class/fc_host
podman exec -u root glance_api ls -l /etc/multipath.conf
```

Неактивный host systemd unit при работающем контейнерном демоне сам по себе
не ошибка. Сначала определить владельца демона и состояние socket activation;
не запускать второй host `multipathd` ради проверки. Наличие каталогов `/dev`
и `/sys` ещё не доказывает доступ к нужным LUN и WWPN.

После подтверждения единственного демона проверить:

```bash
podman exec -u root glance_api multipath -t
podman exec -u root glance_api multipathd show status
podman exec -u root multipathd multipathd show config
```

Первое показывает локальную политику утилиты; второе проверяет достижимость
демона из контейнера; третье — действующую политику управляющего демона.
Если демон размещён на хосте, последнюю команду выполнять через установленный
порядок обращения к нему. Здесь намеренно нет rescan, flush или удаления карт.
Проверка от root не заменяет успешную работу Glance через rootwrap/privsep.

Для FC нужны подключение Glance-хоста к fabric, WWPN/zoning и доступ к нужным
LUN. Для iSCSI — рабочий инициатор, сеть и `iscsid`. При размещении Glance
на отдельных controllers нельзя считать наличие этих компонентов на compute
или cinder-volume достаточным.

## 5. Предлагаемый фикс доставки: три файла роли Glance

Ниже — локальная адаптация штатного механизма Kolla, **не уже принятый
upstream-патч Glance**. Новая переменная позволяет включить доставку явно,
после подтверждения применимости. Она не существует в исходном форке.

### 5.1. `ansible/roles/glance/defaults/main.yml`

Добавить на верхнем уровне:

```yaml
glance_cinder_multipath_enabled: false
```

### 5.2. `ansible/roles/glance/tasks/config.yml`

После `Ensuring config directories exist`, перед первым `include_tasks`, добавить:

```yaml
- name: Validate Glance Cinder multipath prerequisites
  vars:
    service: "{{ glance_services['glance-api'] }}"
  assert:
    that:
      - enable_cinder | bool
      - enable_multipathd | bool
      - inventory_hostname in groups['multipathd']
    fail_msg: "Glance Cinder multipath requires Cinder, multipathd and host membership in multipathd."
  when:
    - glance_cinder_multipath_enabled | bool
    - service | service_enabled_and_mapped_to_host

- name: Copying over multipath.conf for glance-api
  vars:
    service: "{{ glance_services['glance-api'] }}"
  become: true
  template:
    src: "{{ item }}"
    dest: "{{ node_config_directory }}/glance-api/multipath.conf"
    owner: "{{ config_owner_user }}"
    group: "{{ config_owner_group }}"
    mode: "0660"
  with_first_found:
    - "{{ node_custom_config }}/multipath/{{ inventory_hostname }}/multipath.conf"
    - "{{ node_custom_config }}/multipath.conf"
    - "{{ role_path }}/../multipathd/templates/multipath.conf.j2"
  when:
    - glance_cinder_multipath_enabled | bool
    - service | service_enabled_and_mapped_to_host
```

Этот вариант рассчитан на существующее управление демоном ролью Kolla.
Если демон намеренно управляется вне Kolla, не включать второй ради прохождения
assert: условия адаптируются под подтверждённый способ управления.
Assert проверяет декларативные предпосылки, не фактическую готовность SAN.

При стандартных путях источником будет общий
`/etc/kolla/config/multipath.conf` либо
`/etc/kolla/config/multipath/<inventory_hostname>/multipath.conf` на deploy-узле.
Это тот же порядок, что у роли `multipathd`; готовый файл появится в
`/etc/kolla/glance-api/multipath.conf` на Glance-узле.

### 5.3. `ansible/roles/glance/templates/glance-api.json.j2`

Сразу после строки `"config_files": [` и перед первым существующим объектом вставить:

```jinja2
        {% if glance_cinder_multipath_enabled | bool %}
        {
            "source": "{{ container_config_directory }}/multipath.conf",
            "dest": "/etc/multipath.conf",
            "owner": "root",
            "perm": "0644"
        },
        {% endif %}
```

Каталог конфигурации Glance уже смонтирован в контейнер. `kolla_set_configs`
установит внутренний файл; дополнительный bind в `/etc/multipath.conf` не нужен.
Если такой bind уже есть, убрать его у переводимого контейнера: одновременная
запись Kolla в смонтированный файл может конфликтовать с копированием.

На deploy-узле после внесения этих правок включить новую переменную в нужной
области inventory либо `globals.yml`:

```yaml
glance_cinder_multipath_enabled: true
```

Этот флаг доставляет файл. Он не выбирает Cinder store, не включает его клиентский
multipath и не выдаёт контейнеру доступ к SAN. Остальные условия — ниже.
Для host-specific overrides проверить совпадение источника у всех потребителей
одного хоста. `skip_kpartx yes` выбирать с учётом SAN-boot и нужных разделов.

## 6. Отдельно обеспечить доступ Glance к FC-устройствам

В текущем upstream предусмотрены `enable_cinder_backend_privileged` и
`glance_api_privileged`: они управляют privileged-режимом и bind `/dev`.
Готовая принятая правка переключателя —
[Gerrit №961235](https://review.opendev.org/c/openstack/kolla-ansible/+/961235),
commit `935cb52e3832b7fdd7911d3ebda6ac077595da3d`.
[Документация](https://docs.openstack.org/kolla-ansible/latest/reference/shared-services/glance-guide.html#cinder-backends-requiring-privileged-containers),
[реализация](https://github.com/openstack/kolla-ansible/blob/master/ansible/roles/glance/defaults/main.yml).

**В вашем архиве этих переменных нет.** Одно добавление
`enable_cinder_backend_privileged: true` в globals без изменения роли ничего
не исправит. `git apply --check` части №961235, меняющей роль, на вашем архиве
завершается ошибкой несовпадения контекста: upstream-патч опирается на более
новую структуру defaults с уже существующим `glance_api_privileged`.
Если проверки раздела 4 выявили отсутствие доступа для FC, адаптировать
соответствующий механизм в `glance/defaults/main.yml`:

- ввести параметры выбора privileged-режима с сохранением действующих defaults;
- использовать вычисленное значение в `glance_services['glance-api'].privileged`;
- по нему же подключать `/dev:/dev` в `glance_api_default_volumes`;
- включить режим для фактических Glance-хостов с Cinder FC store.

Не переносить весь современный файл defaults поверх форка: в upstream есть
другие изменения и переменные backend, которых в вашей версии может не быть.
Не включать iSCSI лишь для обхода условия доступа к FC. Настройку привилегий,
устройств, rootwrap/privsep и сокета демона принимать по результату подключения
через Glance. Универсального требования смонтировать весь `/run` здесь нет.

Проверить inventory: Glance-хосты должны входить в группу управляемого
`multipathd`; для iSCSI также нужны соответствующая группа и условия роли `iscsi`.
Менять размещение демона и контейнерные namespaces без проверки причин не нужно.

## 7. Включить multipath в Glance store

В существующий override `/etc/kolla/config/glance/glance-api.conf` добавить
параметры в секцию **имени нужного store**. Например, при
`enabled_backends = ... , cinder:cinder` секция называется `[cinder]`:

```ini
[cinder]
cinder_use_multipath = true
cinder_enforce_multipath = true
```

Если store объявлен как `images_san:cinder`, секция должна быть `[images_san]`.
Не заменять весь список `enabled_backends` или существующую конфигурацию
аутентификации ради этих двух параметров.

Если Cinder store ещё не имеет рабочих service credentials и endpoint,
есть отдельный принятый [патч №978863](https://review.opendev.org/c/openstack/kolla-ansible/+/978863),
добавляющий секцию `[cinder]` в шаблон Glance. Его изменение шаблона проходит
`git apply --check` на предоставленном форке. Перед переносом проверить
`cinder_catalog_info`: upstream использует `block-storage::internalURL`,
который должен соответствовать фактическому service type в Keystone вашего облака.
Успешное наложение текста патча не доказывает работоспособность backend.

`cinder_use_multipath` передаёт выбор multipath коннектору os-brick.
`cinder_enforce_multipath` использовать, когда операция должна завершаться
ошибкой при недоступном демоне, вместо допуска fallback. Он не доказывает
число активных путей или фактическую работу через DM-карту — это проверяется
на подключённом тестовом томе. Оба default равны `False` в проверенном
[upstream `glance_store`](https://github.com/openstack/glance_store/blob/stable/2025.1/glance_store/_drivers/cinder/store.py).

Не путать с `use_multipath_for_image_xfer` и `enforce_multipath_for_image_xfer`
в `cinder.conf`: те управляют локальными подключениями **Cinder**, а эти —
подключениями **Glance**. `enable_multipathd` сам по себе параметры Glance не задаёт.

## 8. Применение и поведение reconfigure

Сначала зафиксировать исходную конфигурацию, mounts, image ID, версии
`glance_store`/os-brick и состояние тестовых подключений. Изменения применять
через ту установленную копию Kolla-Ansible, которая выполняет deployment.
Правки распакованного архива сами по себе её не обновляют.

После подготовки на согласованном пилотном наборе узлов:

```bash
kolla-ansible prechecks -i /path/to/inventory --tags glance,multipathd
kolla-ansible reconfigure -i /path/to/inventory --tags glance,multipathd
```

Это команды применения. Теги ограничивают сервисы, но не количество узлов.
Если меняется общий `multipath.conf`, охватить также Nova/Cinder и других
потребителей на затронутых хостах; не оставлять их на разных версиях политики.
Для добавления iSCSI-компонентов отдельно включить соответствующую роль.

| Изменение | Ожидаемое поведение при `COPY_ALWAYS` |
|---|---|
| Первый файл или изменение его содержимого | Перезапуск затронутого `glance_api` после обнаружения различий |
| Изменение mounts или privileged-режима | Пересоздание контейнера |
| Повторный запуск без изменений | Перезапуск из-за данного фикса не требуется |
| Изменение конфигурации самого `multipathd` | Применение через обработчик его роли; бесшовный reload не гарантируется |

При `COPY_ONCE` обработчик предусматривает пересоздание. Обоснование:
`glance/tasks/reconfigure.yml` импортирует `deploy.yml`, который выполняет
config → check-containers → handlers; проверка учитывает
`kolla_set_configs --check`. Это статический вывод из кода, не проведённый
двукратный запуск на стенде.

Рестарт Glance может прервать активную передачу образа. Наличие других API
не гарантирует продолжение уже открытого потока. Планировать окно/дренирование
с учётом реальной схемы Glance и выполняющихся операций.

## 9. Приёмка на тестовых образах и томах

После применения на одном и том же Glance-хосте:

```bash
sha256sum /etc/kolla/glance-api/multipath.conf /etc/kolla/multipathd/multipath.conf
podman exec -u root glance_api sha256sum /etc/multipath.conf
podman exec -u root multipathd sha256sum /etc/multipath.conf
podman exec -u root glance_api /usr/local/bin/kolla_set_configs --check
podman inspect --format '{{.Id}} {{.State.StartedAt}}' glance_api
```

Сравнивать содержимое на одном хосте: разные хосты могут иметь законные
host-specific настройки. Проверить также `multipath -t` и действующую политику
демона; одинаковые байты файла не гарантируют одинаковые defaults разных
версий multipath-tools или отсутствие дополнительных конфигов.

| Тест | Что подтвердить |
|---|---|
| Загрузка нового образа именно в Cinder store | Выбран ожидаемый store, Glance подключил нужный LUN по multipath, операция завершена |
| Скачивание этого образа | Совпала контрольная сумма; по журналам проверен путь Cinder store, а не только выдача из cache |
| Фактический путь | По WWID найден нужный DM multipath map и его пути; при шифровании прослежена вся цепочка устройств |
| Завершение чтения/записи | Attachment и локальные подключения очищены с учётом оставшихся потребителей |
| Отключение одного тестового тома при I/O другого | У второго сохранились данные, пути и mapping |
| Повторный `reconfigure` без изменений | Хеши, ID и StartedAt Glance не изменились при отсутствии других причин рестарта |
| Изменение комментария в конфиге и повтор | Первый запуск доставил новые байты; следующий не перезапускает контейнер из-за них |

Для проверки реального чтения исключить попадание только в Glance cache:
использовать отдельный некэшированный тестовый образ/контролируемый API и
сопоставить запрос с журналами attach/read/detach. Рабочий cache массово не чистить.

Параллельное чтение одного image-volume — дополнительный сценарий:
нужны поддерживаемые driver/backend и volume type с `multiattach`.
Multipath и active-active Cinder этого не заменяют.
[Требования Glance к multiattach](https://docs.openstack.org/glance/2025.1/configuration/configuring.html#configuring-multi-attach-volume-type).

## 10. Относится ли сюда исследованный дефект os-brick

Потенциально да, если Glance выполняет FC-detach с соответствующей версией
os-brick. Upstream `BaseBrickConnectorInterface.disconnect_volume()` передаёт
`force=True` в os-brick; следовательно, описанную непередачу `force` глубже
в `remove_scsi_device` нужно проверять и в образе Glance.
[Исходник коннектора](https://github.com/openstack/glance_store/blob/stable/2025.1/glance_store/_drivers/cinder/base.py).

Это не доказательство такого сбоя на вашем Glance. Условия остаются прежними:
конкретному пути требуется flush, flush завершается ошибкой, затем нужно
проследить локальное удаление и снятие mapping. Нужны версия/хеш установленного
модуля и связанные по времени, host, volume UUID и WWID журналы одной операции.
Не применять безусловный force cleanup или изменения Huawei-драйвера только
потому, что Glance тоже использует os-brick.

## 11. Что есть в community и что проверено здесь

| Задача Glance | Готовое upstream-изменение | Статус на 13.10.2026 и применимость |
|---|---|---|
| Управляемый privileged-режим и доступ к host `/dev` | [№961235](https://review.opendev.org/c/openstack/kolla-ansible/+/961235), commit `935cb52e3832b7fdd7911d3ebda6ac077595da3d` | `MERGED` в master 29.07.2026; требуется адаптация к вашему форку |
| Service credentials и endpoint для Cinder store | [№978863](https://review.opendev.org/c/openstack/kolla-ansible/+/978863), commit `068ed612966b5534519572011bcb8067b6d38d3b` | `MERGED` в master 31.03.2026; изменение шаблона проходит проверку наложения |
| Доставка `multipath.conf` через роль и `config_files` | Отдельный актуальный патч Glance поиском не подтверждён | В разделе 5 предложена локальная адаптация; готовность на стенде не заявляется |

У №961235 найден [backport для stable/2025.1 №1002710](https://review.opendev.org/c/openstack/kolla-ansible/+/1002710)
со статусом `ABANDONED`. В комментарии указано, что backport был создан из-за
ошибки в понимании объёма задачи; это не технический отказ от исходного решения.
Принятие в master не следует выдавать за наличие принятого backport в Epoxy.

- Для Nova принят фикс доставки конфигурации; для Cinder существует открытый
  [патч №987732](https://review.opendev.org/c/openstack/kolla-ansible/+/987732).
  Он меняет роль **Cinder**, а не Glance: применение этого патча Glance не исправляет.
- В проверенном upstream `master` шаблон
  [`glance-api.json.j2`](https://github.com/openstack/kolla-ansible/blob/master/ansible/roles/glance/templates/glance-api.json.j2)
  также не содержит доставки `multipath.conf`.
- Проверены Gerrit-запросы `glance multipath`, `glance privileged` и
  `glance cinder` в проекте Kolla-Ansible, содержимое двух найденных принятых
  патчей и текущий JSON-шаблон Glance. По `glance multipath` найден старый
  abandoned change №714999; отдельного актуального патча доставки Glance
  этим поиском не подтверждено. Это граница поиска, не утверждение,
  что никто в community никогда не делал подобного.
- Upstream-механизм privileged-доступа из раздела 6 решает другую часть
  подготовки контейнера и не подменяет доставку `multipath.conf`.

Локальная база: commit ZIP Kolla `e4f914ce3225395feb75231ac921144d461963f7`,
SHA-256 `d951a3f31131efc70257883ce33620818db851ff40afbf21b63e3fd0616daec4`.
Upstream `glance_store/stable/2025.1` использован как справочник поведения;
соответствие пакету внутри вашего `glance_api` ещё нужно установить.

При подготовке документа проверены три YAML-блока, вставка двух задач,
12 вариантов рендера полного JSON с сохранением прежних записей, синтаксис
пяти Bash-блоков и вложенного Python, INI и локальные ссылки. Все 30 файлов
локальной роли Glance совпали с архивом. Дополнительно выполнен только
`git apply --check --include=ansible/*` для двух upstream-патчей; он не меняет файлы.
Deployment, перезапуски, доступ к СХД и функциональная приёмка не выполнялись.
