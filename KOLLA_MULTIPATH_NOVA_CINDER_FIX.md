# Kolla-Ansible: исправление доставки multipath.conf и проверка FC-detach

Рекомендации обновлены 12.10.2026 с учётом
[расширенного исследования FC/multipath](openstack_dorado_multipath_investigation.md).

## Что делать сейчас

**Первый фикс — доставка и обновление `multipath.conf` в Nova/Cinder.
Основная правка: четыре файла Kolla-Ansible.** Она устраняет подтверждённое
отсутствие конфигурации в контейнере; причину всех SCSI-ошибок ещё нужно подтвердить.

1. **Проверить источник конфигурации.** Использовать общий либо host-specific
   файл Ansible. Проверить `skip_kpartx yes`, учитывая SAN-boot и нужные разделы
   хоста, если они есть. Пути и пояснения — в **разделе 2**.
2. **Внести четыре изменения.** В ролях `nova-cell` и `cinder` добавить задачу
   доставки файла и запись в `config.json`, устанавливающую `/etc/multipath.conf`.
   Список файлов — в **разделе 1**, готовые вставки — в **разделах 3–5**.
   Если FC-тома подключает также `cinder_backup`, учесть **раздел 6**.
3. **Применить на пилотном наборе узлов в согласованное окно.** Убрать прежний
   прямой bind в `/etc/multipath.conf` у переводимых контейнеров. Выполнить
   `prechecks` и `reconfigure` для `multipathd`, Nova и Cinder по **разделу 8**.
   Сохранить существующее размещение единственного управляющего демона.
4. **Проверить результат по разделу 9.** Сравнить содержимое файлов на одном
   узле, эффективные настройки демона и фактический multipath-путь тестового
   тома. Проверить его подключение и отключение, затем повторное применение
   конфигурации без изменений.

**Первый этап принят, когда:** файл доступен всем нужным клиентам, демон
использует ожидаемую политику, тестовый attach/detach проходит, а повторное
применение не вызывает лишних перезапусков. Идемпотентность объяснена в **разделе 7**.

**os-brick и Huawei сейчас не менять.** К **разделу 10** переходить, если после
первого фикса остаётся ошибка detach: сначала сопоставить журналы и установленный
код, затем решать вопрос об отдельном патче.

**Статус:** ниже приведены рекомендации; исходники и инфраструктура не изменены.
Архив os-brick и артефакты его проб в текущей папке отсутствуют; соответствующие
выводы взяты из исследования, повторно здесь не воспроизводились.

## 1. Какие файлы менять

Все пути в таблице указаны относительно корня **той копии Kolla-Ansible,
из которой действительно выполняется развёртывание**. Изменение распакованного
архива само по себе не обновляет установленную копию в virtualenv.

| Файл | Изменение |
|---|---|
| `ansible/roles/nova-cell/tasks/config.yml` | Сформировать файл в каталоге `nova-compute` на целевом узле |
| `ansible/roles/nova-cell/templates/nova-compute.json.j2` | Объявить установку файла в `/etc/multipath.conf` контейнера |
| `ansible/roles/cinder/tasks/config.yml` | Сформировать файл в каталоге `cinder-volume` на целевом узле |
| `ansible/roles/cinder/templates/cinder-volume.json.j2` | Объявить установку файла в `/etc/multipath.conf` контейнера |

Роль для `nova_compute` называется **`nova-cell`**, а не `nova`.

Каталоги `{{ node_config_directory }}/nova-compute/` и
`{{ node_config_directory }}/cinder-volume/` уже смонтированы в
`{{ container_config_directory }}` соответствующих контейнеров. Поэтому для
предлагаемой реализации новые записи в `*_default_volumes` не требуются.

## 2. Единый источник конфигурации

Сохранить порядок поиска из существующей роли `multipathd`:

1. `{{ node_custom_config }}/multipath/{{ inventory_hostname }}/multipath.conf`;
2. `{{ node_custom_config }}/multipath.conf`;
3. штатный `ansible/roles/multipathd/templates/multipath.conf.j2`.

При стандартных путях пользовательский общий файл располагается на узле
развёртывания в `/etc/kolla/config/multipath.conf`, а файл для `compute03` —
в `/etc/kolla/config/multipath/compute03/multipath.conf`.
Используется именно имя из inventory.

Путь `/etc/kolla/config/multipath/multipath.conf` без имени узла в данном форке
в этот список не входит.

Каждая роль сама рендерит выбранный источник на нужный узел. Не следует
копировать готовый файл из `/etc/kolla/multipathd/` через `remote_src`: тогда
доставка зависела бы от предыдущего запуска другой роли и могла бы использовать
старое содержимое при запуске только с тегом `nova` или `cinder`.

Ниже ссылка через `role_path` использует существующий шаблон роли `multipathd`.
Создавать его отдельные копии для Nova и Cinder не нужно.

### Кто меняет содержимое и где работает multipath

DM-multipath работает в ядре хоста; контейнер Kolla запускает управляющий
`multipathd` с доступом к устройствам этого хоста. Само размещение демона
в контейнере не создаёт отдельные multipath-устройства.

В локальном multipathd.json.j2 (`kolla-ansible-pvs/ansible/roles/multipathd/templates/multipathd.json.j2`)
задано копирование из `{{ container_config_directory }}/multipath.conf`
в `/etc/multipath.conf`. Исходный каталог смонтирован `ro`. Поэтому Ansible
управляет исходником на хосте, `kolla_set_configs` создаёт внутреннюю копию,
а демон её читает. Изменение этой внутренней копии не возвращается на хост
и не меняет конфиги Nova/Cinder. Даже если они bind-монтируют
`/etc/kolla/multipathd/multipath.conf`, это источник копирования, а не внутренний
`/etc/multipath.conf` демона.

В собственной схеме с настоящим bind одного файлового объекта запись в этот
объект через доступный `rw` mount действительно видна всем его читателям,
включая контейнеры с `ro` mount. Это отличается от атомарной замены файла
по имени, описанной в разделе 5. В обоих случаях видимость байтов и применение
настроек уже работающим демоном проверяются отдельно.

### Пользовательский файл заменяет шаблон целиком

`with_first_found` выбирает один источник; слияния с defaults нет. В локальном
штатном шаблоне уже есть:

```text
defaults {
   user_friendly_names no
   find_multipaths yes
   skip_kpartx yes
}
```

При использовании собственного профиля Dorado проверить, не потерялся ли
`skip_kpartx yes`. В Kolla он добавлен для предотвращения автоматических
partition mappings, способных удерживать карту при detach os-brick.
[Релизное примечание LP#2078973](https://docs.openstack.org/releasenotes/kolla-ansible/2024.2.html).

Это фрагмент штатной политики, а не полный конфиг Dorado. Для хоста с SAN-boot,
LVM или другими нужными разделами на multipath сначала определить область
применения к гостевым LUN. Проверить эффективные значения и udev/kpartx на самом
хосте. Уже существующие partition-карты от изменения файла не исчезают;
держатели могут быть законными, например dm-crypt, LVM или QEMU.

Единый источник означает согласованную политику для потребителей одного хоста,
а не общий для всего кластера файл состояния WWID/bindings. Их фактические пути
и сохранение при пересоздании контейнеров проверяются отдельно. Для подбора
ALUA/таймаутов нужны версия Dorado, Host Access Mode, HyperMetro и применимый
vendor guide; универсальный профиль здесь не предлагается.

## 3. Nova: задача доставки файла

В `ansible/roles/nova-cell/tasks/config.yml` после задачи
`Ensuring config directories exist`, перед следующим `include_tasks`, добавить:

```yaml
- name: Copying over multipath.conf for nova-compute
  vars:
    service: "{{ nova_cell_services['nova-compute'] }}"
  become: true
  template:
    src: "{{ item }}"
    dest: "{{ node_config_directory }}/nova-compute/multipath.conf"
    owner: "{{ config_owner_user }}"
    group: "{{ config_owner_group }}"
    mode: "0660"
  with_first_found:
    - "{{ node_custom_config }}/multipath/{{ inventory_hostname }}/multipath.conf"
    - "{{ node_custom_config }}/multipath.conf"
    - "{{ role_path }}/../multipathd/templates/multipath.conf.j2"
  when:
    - enable_multipathd | bool
    - service | service_enabled_and_mapped_to_host
```

При стандартных путях результат на compute-узле:
`/etc/kolla/nova-compute/multipath.conf`.

## 4. Cinder: задача доставки файла

В `ansible/roles/cinder/tasks/config.yml` после задачи
`Ensuring config directories exist`, перед `external_huawei.yml`, добавить:

```yaml
- name: Copying over multipath.conf for cinder-volume
  vars:
    service: "{{ cinder_services['cinder-volume'] }}"
  become: true
  template:
    src: "{{ item }}"
    dest: "{{ node_config_directory }}/cinder-volume/multipath.conf"
    owner: "{{ config_owner_user }}"
    group: "{{ config_owner_group }}"
    mode: "0660"
  with_first_found:
    - "{{ node_custom_config }}/multipath/{{ inventory_hostname }}/multipath.conf"
    - "{{ node_custom_config }}/multipath.conf"
    - "{{ role_path }}/../multipathd/templates/multipath.conf.j2"
  when:
    - enable_multipathd | bool
    - service | service_enabled_and_mapped_to_host
```

При стандартных путях результат на узле `cinder-volume`:
`/etc/kolla/cinder-volume/multipath.conf`.

## 5. Оба контейнера: установка файла через config.json

В каждом из двух файлов:

- `ansible/roles/nova-cell/templates/nova-compute.json.j2`;
- `ansible/roles/cinder/templates/cinder-volume.json.j2`;

добавить новый условный объект **первым элементом** массива `config_files`.

Было — начало массива:

```jinja2
    "config_files": [
        {
```

Стало — заменить этот фрагмент на:

```jinja2
    "config_files": [
{% if enable_multipathd | bool %}
        {
            "source": "{{ container_config_directory }}/multipath.conf",
            "dest": "/etc/multipath.conf",
            "owner": "root",
            "perm": "0644"
        },
{% endif %}
        {
```

После последней строки продолжить существующий объект `nova.conf` или
`cinder.conf` без изменений. Запятая после нового объекта обязательна:
существующие элементы массива идут следом. Добавлять `optional: true` не нужно:
при включённом multipath отсутствие доставленного файла должно быть ошибкой.

Получается цепочка для каждого сервиса:

```text
источник на узле развёртывания
  → template на целевой узел: /etc/kolla/<service>/multipath.conf
  → существующее монтирование каталога конфигурации в контейнер
  → kolla_set_configs: /etc/multipath.conf внутри контейнера
```

Если ранее в `nova_compute_extra_volumes` или `cinder_volume_extra_volumes`
добавляли прямое монтирование в `/etc/multipath.conf`, перед применением этой
реализации убрать именно эту запись, сохранив остальные дополнительные тома.
Один путь не должен одновременно быть bind mount и назначением копирования
`kolla_set_configs`: попытка заменить смонтированный файл может завершиться
ошибкой.

Дополнительно single-file bind может продолжить показывать старый inode после
атомарной замены источника Ansible. Совпадение `Source` в `podman inspect`
не доказывает совпадение байтов. Это риск последующих обновлений, а не
доказанная причина исходного отсутствия файла.

Доставка через уже смонтированный **каталог** и управляемый `config_files`
включает файл в штатное сравнение Kolla. Сохранение прямого файлового bind
потребовало бы отдельного обновления mounts всех потребителей при изменениях.
Флаги `:shared`, `:z` и `:Z` эту задачу не решают. Подробное обоснование —
в разделах 4–5 расширенного исследования.

## 6. Когда включать cinder_backup

Если `cinder_backup` сам подключает FC/iSCSI-тома через os-brick, ему также
нужна конфигурация:

1. В `cinder/tasks/config.yml` добавить вторую задачу из раздела 4, заменив
   `cinder-volume` на `cinder-backup` в имени задачи, выборе сервиса и `dest`.
2. В `cinder/templates/cinder-backup.json.j2` вставить тот же объект из раздела 5.

Условие `service_enabled_and_mapped_to_host` оставлять: оно исключает выключенный
сервис и узлы, на которых его нет. Контейнеры Cinder API и Scheduler в эту правку
не входят.

## 7. Почему это идемпотентно

| Сценарий | Ожидаемое поведение этой правки |
|---|---|
| Первое применение при `enable_multipathd: "yes"` | Создать файлы, обновить `config.json`, применить конфигурацию контейнеров |
| Повторное применение без изменений | Задачи `template` возвращают `ok`; конфигурация совпадает; перезапуск по причине этой правки не требуется |
| Изменилось содержимое выбранного `multipath.conf` | Обновить файл и применить новую конфигурацию затронутых контейнеров |
| Внутри контейнера файл удалён или изменён вручную | Штатная проверка обнаруживает расхождение и инициирует восстановление при `reconfigure` |
| Multipath выключен с самого начала | Новые задачи пропущены, новый объект отсутствует в JSON |

Обоснование по коду форка:

- `ansible/roles/nova-cell/tasks/deploy.yml` и `ansible/roles/cinder/tasks/deploy.yml`
  вызывают `config.yml`, затем `check-containers.yml` и обработчики;
- обе роли используют этот же порядок при `reconfigure`;
- в `ansible/module_utils/kolla_podman_worker.py` методы `compare_container()`
  и `compare_config()` учитывают `/usr/local/bin/kolla_set_configs --check`
  от root: код `0` означает совпадение, `1` — изменение, другой код — ошибку;
- для Docker тот же контракт реализован в `kolla_container_worker.py` и
  `kolla_docker_worker.py`; движок устанавливается по фактическому развёртыванию;
- `ansible/roles/service-check-containers/tasks/main.yml` уведомляет обработчики
  для контейнеров с обнаруженными изменениями;
- стандартный `config_strategy` в `ansible/group_vars/all.yml` — `COPY_ALWAYS`:
  при изменении только конфигурации используется перезапуск. Для `COPY_ONCE`
  обработчик форка предусматривает пересоздание контейнера.

В upstream Kolla проверка сравнивает наличие, содержимое, права и владельца
заявленных файлов. Реализация внутри используемого образа должна соответствовать
этому контракту. [Исходник Kolla 2025.1](https://raw.githubusercontent.com/openstack/kolla/stable/2025.1/docker/base/set_configs.py).

**Идемпотентность не означает отсутствие первого перезапуска.** Она также не
гарантирует `changed=0` у всего плейбука: другие задачи или независимые изменения
могут законно давать `changed` и вызывать перезапуски.

Не добавлять безусловный `podman restart` / `docker restart`, `changed_when: true` или отдельный
обработчик с перезапуском на каждом запуске. Использовать существующую проверку
конфигурации, а не дублировать её.

В Podman `compare_volumes()` сравнивает пути и режимы mounts, а не содержимое
произвольного `extra_volume`. Поэтому утверждение об обнаружении изменения
файла относится именно к предложенной записи в `config_files`. После изменения
общего источника применение должно охватывать `multipathd` и всех фактических
клиентов: запуск только тега `nova` может обновить Nova, оставив демон на
старой политике. Совпадение файлов ещё не доказывает перечитывание демоном.

Переключение `enable_multipathd` с `yes` на `no` — отдельная операция вывода
multipath из эксплуатации, а не проверка повторного применения. Эта инструкция
не обещает удаление старых файлов из всех каталогов и не предусматривает
автоматическую очистку рабочих multipath-устройств.

## 8. Применение после внесения правок

Проверить перед применением:

- Исполняемая установка Kolla-Ansible содержит изменённые роли и шаблоны.
- Зафиксированы движок контейнеров, image IDs/digests, версия установленного
  Kolla, multipath-tools и os-brick; найден один действующий демон и проверены
  host service/socket-units до запросов его клиентов (раздел 9).
- В `/etc/kolla/globals.yml` задано `enable_multipathd: "yes"`.
- Все соответствующие compute/storage-узлы входят в группу `multipathd`.
  Штатный `ansible/inventory/multinode` включает туда группы `compute` и `storage`;
  фактический inventory может отличаться.
- Пользовательский `multipath.conf` лежит в одном из путей раздела 2.
  Если оба файла отсутствуют, используется штатный шаблон, а не настройки Dorado
  из какого-либо другого каталога.
- Прямой bind mount в `/etc/multipath.conf`, если он был добавлен ранее, исключён
  из дополнительных томов для контейнеров, переводимых на эту реализацию.
- Проверены политика `skip_kpartx`, SAN-boot и владельцы существующих holders;
  при пересоздании сохраняется нужное состояние WWID/bindings этого хоста.

Далее в согласованное окно выполнить из рабочего окружения развёртывания,
подставив путь к своему inventory:

```bash
kolla-ansible prechecks -i /path/to/inventory --tags multipathd,nova,cinder
kolla-ansible reconfigure -i /path/to/inventory --tags multipathd,nova,cinder
```

Это команды применения, они могут перезапустить соответствующие контейнеры.
Теги ограничивают сервисы, но не выбирают один узел. Для пилотного применения
нужно отдельно определить допустимый набор узлов и зависимости Nova cells;
не копировать произвольный `--limit compute03` без этой проверки.

Включение `enable_multipathd` уже выставляет Nova параметр
`[libvirt] volume_use_multipath = true` через
`nova-cell/templates/nova.conf.d/libvirt.conf.j2`.
Для image-transfer в Cinder отдельно проверить `use_multipath_for_image_xfer`
и `enforce_multipath_for_image_xfer` в секции FC-бэкенда либо
`[backend_defaults]`: доставка файла сама по себе их не включает. В локальном
Cinder оба значения по умолчанию — `False`. Если для локального image-transfer
требуется multipath, после проверки готовности демона и клиентов запланировать
отдельное изменение политики в существующей секции нужного FC-бэкенда:

```ini
use_multipath_for_image_xfer = true
enforce_multipath_for_image_xfer = true
```

Это меняет поведение Cinder при недоступности multipath и требует проверки
image-to-volume и volume-to-image. `enforce` не заменяет проверку фактического
пути: исследование описывает возврат одиночного пути в отдельной функции
os-brick даже при доступном демоне; полный connect этим не проверен.
Не добавлять `enforce_multipath_io_with_iscsi`, `os_brick_retry_attempts` или
`os_brick_scsi_scan_delay` без подтверждения регистрации и использования
параметров в установленном коде. Настройки ожидания карты
`[os_brick] wait_mpath_device_*` не исправляют незавершённый detach.

## 9. Проверка на целевых узлах

Команды ниже приведены для **Podman**, указанного в расширенном исследовании,
и стандартного `node_config_directory`. Для Docker заменить `podman` на
`docker` после проверки фактического движка.
Выполнять команды сервиса только на узлах, где он развёрнут; использовать права,
достаточные для чтения `/etc/kolla` и работы с контейнерным движком.

### До опроса демона

На том же хосте, где проверяется том:

```bash
hostname -f
date --iso-8601=seconds
podman ps --format '{{.Names}} {{.Image}}'
pgrep -a -x multipathd
systemctl show multipathd.service multipathd.socket \
  -p Id -p ActiveState -p SubState -p MainPID -p ExecStart
ss -xlpn | grep -Ei 'multipath|/org/kernel/linux/storage' || true
```

Установить, какой процесс управляет картами и какой socket ему принадлежит.
Отсутствие host unit допустимо для Kolla. Активный systemd socket-unit может
запустить host daemon при обращении клиента, поэтому до дальнейших запросов
исключить конкурирующее управление. Не запускать второй демон как способ
устранить недостающий конфиг.

Проверить `podman inspect <container> --format '{{json .Mounts}}'` и фактический
network namespace. Общий `/run` недостаточен для сборок с абстрактным Unix-сокетом
(в исследовании это проверено для multipath-tools 0.9.4). Локальный Podman worker
задаёт host networking, но работающие контейнеры могут отличаться.

### Compute

```bash
test -f /etc/kolla/nova-compute/multipath.conf
sha256sum /etc/kolla/multipathd/multipath.conf /etc/kolla/nova-compute/multipath.conf
podman exec -u root nova_compute sha256sum /etc/multipath.conf
podman exec -u root multipathd sha256sum /etc/multipath.conf
podman exec -u root nova_compute /usr/local/bin/kolla_set_configs --check
podman exec -u root multipathd /usr/local/bin/kolla_set_configs --check
podman exec -u root nova_compute multipathd show status
podman exec -u root nova_compute multipath -t
podman exec -u root multipathd multipathd show config
podman exec -u root multipathd multipathd show maps topology
```

### Cinder volume

```bash
test -f /etc/kolla/cinder-volume/multipath.conf
sha256sum /etc/kolla/multipathd/multipath.conf /etc/kolla/cinder-volume/multipath.conf
podman exec -u root cinder_volume sha256sum /etc/multipath.conf
podman exec -u root multipathd sha256sum /etc/multipath.conf
podman exec -u root cinder_volume /usr/local/bin/kolla_set_configs --check
podman exec -u root multipathd /usr/local/bin/kolla_set_configs --check
podman exec -u root cinder_volume multipathd show status
podman exec -u root cinder_volume multipath -t
podman exec -u root multipathd multipathd show config
podman exec -u root multipathd multipathd show maps topology
```

Ожидается совпадение хешей **в пределах одного узла**, отсутствие сообщения
о недостающем `/etc/multipath.conf`, успешный запрос статуса демона и код `0`
у `kolla_set_configs --check`. Эта команда проверяет всю конфигурацию
контейнера: её ошибка может относиться к другому файлу.

При участии `cinder_backup` повторить для него. Если host-side утилиты участвуют
в обработке устройств, проверить также их конфигурацию, пакеты и udev-правила;
четыре изменения выше не доставляют `/etc/multipath.conf` на сам хост.
Разные inode у управляемых копий нормальны. Сравнивать нужно ожидаемые байты,
а затем эффективную политику локального `multipath -t` и демона
`multipathd show config`: это разные источники. Учитывать hardware defaults,
дополнительные конфиги и версии пакетов; одинаковые хеши одного файла не
гарантируют одинаковую политику.

`multipathd reconfigure` — операция применения с возможной перезагрузкой карт,
не команда просмотра. Успех `exec -u root` также не проверяет рабочий путь
privsep/rootwrap сервиса: его подтверждают операция и журналы без ошибок доступа.

Конфигурации разных узлов могут различаться, если используются host-specific
файлы. Пустой вывод `multipath -ll` без подключённых томов не подтверждает
работоспособность FC-подключения.

### Реальный путь одного тома

Связать UUID тома, WWID, host и attachment с block-device source ВМ в libvirt
либо с локальным устройством image-transfer в Cinder. Проследить symlink и всю
цепочку device-mapper, включая dm-crypt при шифровании. Для установленного
устройства проверить slaves и holders:

```bash
lsblk -o NAME,TYPE,SIZE,PKNAME,HCTL,WWN,MOUNTPOINT
dmsetup ls --tree
dmsetup info -c
# dm-N — placeholder: заменить картой исследуемого WWID.
cat /sys/block/dm-N/dm/uuid
ls -l /sys/block/dm-N/slaves /sys/block/dm-N/holders
```

Статус `in-use`, флаг `enforce` и здоровая карта другого узла не заменяют эту
проверку. Все сравнения относятся к одному и тому же узлу и тому же WWID.

### Два последовательных запуска

После первого успешного применения сохранить ID и время старта контейнеров:

```bash
podman inspect --format '{{.Id}} {{.State.StartedAt}}' multipathd
podman inspect --format '{{.Id}} {{.State.StartedAt}}' nova_compute
podman inspect --format '{{.Id}} {{.State.StartedAt}}' cinder_volume
```

Каждую команду выполнять на соответствующем узле. Без изменения файлов,
переменных и образов повторить тот же `reconfigure`, затем снова получить
ID и `StartedAt`.

Критерии для этой правки:

- новые задачи доставки файла — `ok`, а не `changed`;
- хеши конфигурации остаются прежними;
- `kolla_set_configs --check` возвращает `0`;
- ID и время старта проверяемых контейнеров не меняются, если нет других причин
  для перезапуска.

Дополнительно на тестовом окружении проверить обновление содержимого выбранного
источника, например добавлением комментария: первый запуск должен доставить
новый файл во все нужные контейнеры, следующий — не давать повторных изменений.
Комментарий проверяет доставку и сравнение байтов. Отдельное контролируемое
изменение политики должно отразиться в конфигурации демона и локальных клиентов;
приёмка только по хешам недостаточна.

## 10. Если ошибка detach остаётся после первого фикса

### 10.1. Когда рассматривать патч os-brick

Раздел 8 расширенного исследования описывает следующий механизм: FC-метод
`_remove_devices` получает `force`, но не передаёт его в
`remove_scsi_device(device_path, flush=flush)`. Если конкретному пути требуется
flush и он завершается ошибкой, низкоуровневый метод с `force=False` по умолчанию
не доходит до sysfs delete. Внешний перехват ошибки не продолжает прерванный
метод. Это относится к ветке с `flush=True`; при штатном dm-multipath отдельные
sd-пути обычно не требуют индивидуального flush.

В исследовании указан SHA-256 проверенного `fibre_channel.py`:
`4effea20b90c3f4de0de86739388a9c880db80dc18c3ffc71a92c1ef93c1f80f`.
Для решения о патче сначала зафиксировать версию, путь и хеш модуля внутри
**обоих** используемых образов (`nova_compute`, `cinder_volume`), сравнить
`_remove_devices`, `requires_flush`, `remove_scsi_device` и реальные аргументы
операции. Команда получения fingerprint приведена в разделе 11.5 исследования.
Совпадение одного файла не подтверждает весь пакет; различие хеша требует diff,
а не автоматического вывода об отсутствии дефекта.

Далее сопоставить по host, UUID, WWID, request ID и времени с часовым поясом:
начало disconnect → ошибка flush → запрос/отсутствие удаления конкретного пути
→ terminate/unmap → последующие ошибки SCSI. В локальном Cinder
`_detach_volume` действительно вызывает disconnect перед terminate_connection;
при `force` обработка может продолжиться после ошибки. Это подтверждает
возможность цепочки, но не её наличие в исходном инциденте и не причину flush.

**Кандидат на минимальную правку при подтверждённом совпадении кода** —
передача уже полученного `force=force` в `remove_scsi_device`, после проверки
сигнатуры установленной версии. Не заменять его на безусловное `force=True`
и не менять `ignore_errors` ради сокрытия ошибки. До включения в образ нужны
регрессионные тесты полного затронутого вызова, включая обработчики исключений:

| Сценарий | Ожидаемый контракт |
|---|---|
| Успешный flush | Штатная очистка выбранного пути сохраняется |
| Ошибка flush, `force=False` | Ошибка не превращается в успешное принудительное удаление |
| Ошибка flush, `force=True` | Запрос удаления разрешённого к отключению пути достигается; ошибки учитываются согласно контракту |
| `ignore_errors=False/True` | Меняется передача ошибок вызывающему коду, а не самовольно выбранный набор устройств |
| `flush=False`, multipath и соседний том | Не появляется лишний flush; очистка карты и пути других потребителей не повреждаются |

Восемь проб из исследования выполнялись с заглушками ОС и без полного
стека/декораторов; их нельзя выдавать за эту приёмку. Готовый патч os-brick
в текущий документ не включён.

Обновление «просто до 6.11.1» не является доказанным решением этого FC-сценария:
упомянутое в release notes исправление orphaned devices относится к iSCSI,
а FC-запись — к производительности disconnect.
[Релизные примечания os-brick 6.11.1](https://docs.openstack.org/releasenotes/os-brick/2025.1.html).

### 10.2. Проверка Huawei и граница диагноза

В локальном Huawei FC-драйвере при наличии оставшихся LUN в соответствующей
LUN Group очистка инициаторов не выполняется; при значении `left_lunnum <= 0`
может выполняться. Значение начинается с `-1` и может сохраниться, если группа
не найдена. Поэтому успешный `remove_fc_from_host` сам по себе не доказывает
ни ошибочное отключение, ни отсутствие других потребителей Host.

Перед изменением драйвера сопоставить Host/Host Group/LUN Group/Mapping View,
WWPN, ручные mapping, использование Host другими backend, HyperMetro и
оставшиеся attachments, включая multiattach. Исследование отдельно отмечает
разные узлы на скриншотах и разрыв времени между SCSI-ошибками и показанным REST
detach; объединять их в доказанную последовательность нельзя.

Не подменять устранение причины увеличением таймаутов. `no_path_retry 15` —
число повторов, не 15 секунд; `queue_if_no_path` само по себе не доказывает
бесконечного ожидания. Причину `Logical unit not supported` проверяют для
конкретного LUN и его mapping, а не трактуют как несовместимость модели Dorado.

### 10.3. Стендовая приёмка перед раскаткой

| Проверка на выделенных тестовых томах | Критерий |
|---|---|
| Первое применение, повтор без изменений, затем изменение политики | Файлы согласованы у всех потребителей; демон использует ожидаемую политику; повтор не вызывает лишних рестартов |
| Attach/detach одного тома | Проверен фактический multipath-путь; после полного отключения без других потребителей нет нежелательных устройств |
| Detach одного из двух томов при I/O второго | Данные второго корректны, его пути и mapping сохранены |
| Отключение последнего тома | Локальная очистка согласована со снятием mapping и ожидаемой очисткой инициаторов |
| Image-to-volume и volume-to-image на узле Cinder | Проверены multipath-путь локального подключения, данные и последующая очистка |
| Контролируемая потеря одного FC-пути и восстановление | I/O и целостность данных сохраняются; путь возвращается в ожидаемое состояние |

Запись и контрольные суммы — только на выделенных тестовых данных. Существующие
multiattach-подключения учитываются до очистки: отсутствие всех устройств не
может быть критерием, пока остаётся законный потребитель.

Правка доставки устраняет подтверждённый разрыв конфигурации; весь FC-инцидент
считается устранённым только после проверки соответствующего сценария.
Не выполнять вслепую `multipath -F`, массовое удаление `sdX`,
`dmsetup remove -f`, kpartx cleanup, force-delete attachments и общий FC-rescan.
Патчи Huawei/Nova/os-brick остаются отдельными изменениями с собственной
проверкой, а не частью четырёх изменений доставки.

## 11. Что проверено при подготовке инструкции

При обновлении рекомендаций локально повторно проверены:

- разбор двух YAML-задач и их вставка в существующие списки задач;
- пути общего шаблона, порядок выбора источника и условия выполнения;
- рендер полных JSON-шаблонов Nova, Cinder volume и опционального Cinder backup:
  72 сочетания значений флага и дополнительных настроек;
- наличие ровно одной записи для `/etc/multipath.conf` при включённом флаге,
  её отсутствие при выключенном и сохранение остальных JSON-объектов;
- синтаксис шести блоков Bash и существование локальных ссылок;
- локальные Podman comparison/lifecycle, штатный `skip_kpartx`, параметры
  image-transfer, порядок Cinder disconnect/terminate и ветвление Huawei cleanup;
- соответствие 5615 обычных файлов распакованных исходников двум ZIP-архивам:
  исходники не изменены.

Это статическая проверка примеров, а не запуск ролей Ansible на стенде.
Доставка в реальные контейнеры, отсутствие лишнего перезапуска при повторном
`reconfigure`, эффективная политика, FC attach/detach и поведение при отказе
пути пока не проверены. Восемь изолированных проб os-brick описаны в исследовании
и в рамках этого обновления не запускались. Само расширенное исследование
сохранено без изменений.

## Источники и база проверки

Пути к исходникам ниже относятся к предоставленным ZIP-архивам. Архивы
и распакованные исходники в репозиторий документации не включены.

- [Расширенное исследование](openstack_dorado_multipath_investigation.md), прежде всего разделы 4–8 и 10–12.
- [Краткая сводка](openstack_dorado_fc_summary.md), синхронизированная с этими рекомендациями.
- Доставка конфигурации multipathd (`kolla-ansible-pvs/ansible/roles/multipathd/tasks/config.yml`).
- Штатная политика multipath (`kolla-ansible-pvs/ansible/roles/multipathd/templates/multipath.conf.j2`).
- Монтирования Nova (`kolla-ansible-pvs/ansible/roles/nova-cell/defaults/main.yml`) и Cinder (`kolla-ansible-pvs/ansible/roles/cinder/defaults/main.yml`).
- Сравнение конфигурации и lifecycle Podman (`kolla-ansible-pvs/ansible/module_utils/kolla_podman_worker.py`).
- Сравнение конфигурации Docker (`kolla-ansible-pvs/ansible/module_utils/kolla_docker_worker.py`).
- Штатное уведомление обработчиков (`kolla-ansible-pvs/ansible/roles/service-check-containers/tasks/main.yml`).
- Параметры multipath в исходниках Cinder (`cinder-pvs/cinder/volume/driver.py`).
- Локальный Huawei FC-драйвер (`cinder-pvs/cinder/volume/drivers/huawei/huawei_driver.py`).

SHA-256 исходного архива `kolla-ansible-pvs.zip`:
`d951a3f31131efc70257883ce33620818db851ff40afbf21b63e3fd0616daec4`.

SHA-256 исходного архива `cinder-pvs.zip`:
`a635f0e994c786c27c729d07e14eeaa8c92a887652f2cb69daca808d8754eaed`.
