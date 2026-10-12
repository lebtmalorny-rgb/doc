# Kolla-Ansible: доставка multipath.conf в Nova и Cinder

## Краткий вывод

В предоставленном форке `kolla-ansible-pvs.zip` роль `multipathd` формирует
`multipath.conf` только для контейнера `multipathd`. Контейнеры `nova_compute`
и `cinder_volume` не получают этот файл штатными задачами и шаблонами форка.
Это соответствует ошибке из исследования:

```text
/etc/multipath.conf does not exist, blacklisting all devices.
```

Нужно добавить доставку файла через существующие каталоги конфигурации сервисов
и `config_files` в их `config.json`. Основная правка затрагивает четыре файла.

**Изменение рассчитано на идемпотентное применение:** после успешного первого
применения повторный запуск с теми же исходными файлами и переменными не должен
менять конфигурацию или вызывать перезапуск из-за этой правки. Это следует из
механизма сравнения конфигурации в форке; два запуска на реальном стенде ещё
нужны для подтверждения поведения конкретных образов.

Инструкция подготовлена по предоставленным исходникам. Правки ниже в исходники
не внесены, команды применения на инфраструктуре не выполнялись.

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
- `ansible/module_utils/kolla_container_worker.py`, `compare_container()`,
  учитывает результат `compare_config()`;
- `ansible/module_utils/kolla_docker_worker.py`, `compare_config()`, запускает
  `/usr/local/bin/kolla_set_configs --check` от root: код `0` означает совпадение,
  `1` — изменение;
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

Не добавлять безусловный `docker restart`, `changed_when: true` или отдельный
обработчик с перезапуском на каждом запуске. Использовать существующую проверку
конфигурации, а не дублировать её.

Переключение `enable_multipathd` с `yes` на `no` — отдельная операция вывода
multipath из эксплуатации, а не проверка повторного применения. Эта инструкция
не обещает удаление старых файлов из всех каталогов и не предусматривает
автоматическую очистку рабочих multipath-устройств.

## 8. Применение после внесения правок

Проверить перед применением:

- Исполняемая установка Kolla-Ansible содержит изменённые роли и шаблоны.
- В `/etc/kolla/globals.yml` задано `enable_multipathd: "yes"`.
- Все соответствующие compute/storage-узлы входят в группу `multipathd`.
  Штатный `ansible/inventory/multinode` включает туда группы `compute` и `storage`;
  фактический inventory может отличаться.
- Пользовательский `multipath.conf` лежит в одном из путей раздела 2.
  Если оба файла отсутствуют, используется штатный шаблон, а не настройки Dorado
  из какого-либо другого каталога.
- Прямой bind mount в `/etc/multipath.conf`, если он был добавлен ранее, исключён
  из дополнительных томов для контейнеров, переводимых на эту реализацию.

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
Для image-transfer в Cinder отдельно проверить настройку
`use_multipath_for_image_xfer` в секции FC-бэкенда: доставка файла сама по себе
её не включает. В предоставленном Cinder значение по умолчанию — `False`.
Менять её в составе исправления доставки не требуется.

## 9. Проверка на целевых узлах

Команды ниже приведены для Docker и стандартного `node_config_directory`.
Выполнять команды сервиса только на узлах, где он развёрнут; использовать права,
достаточные для чтения `/etc/kolla` и работы с Docker.

### Compute

```bash
test -f /etc/kolla/nova-compute/multipath.conf
sha256sum /etc/kolla/multipathd/multipath.conf /etc/kolla/nova-compute/multipath.conf
docker exec -u root nova_compute sha256sum /etc/multipath.conf
docker exec -u root multipathd sha256sum /etc/multipath.conf
docker exec -u root nova_compute /usr/local/bin/kolla_set_configs --check
docker exec -u root nova_compute multipathd show status
docker exec -u root nova_compute multipath -ll
```

### Cinder volume

```bash
test -f /etc/kolla/cinder-volume/multipath.conf
sha256sum /etc/kolla/multipathd/multipath.conf /etc/kolla/cinder-volume/multipath.conf
docker exec -u root cinder_volume sha256sum /etc/multipath.conf
docker exec -u root multipathd sha256sum /etc/multipath.conf
docker exec -u root cinder_volume /usr/local/bin/kolla_set_configs --check
docker exec -u root cinder_volume multipathd show status
docker exec -u root cinder_volume multipath -ll
```

Ожидается совпадение хешей **в пределах одного узла**, отсутствие сообщения
о недостающем `/etc/multipath.conf`, успешный запрос статуса демона и код `0`
у `kolla_set_configs --check`. Последняя команда проверяет всю конфигурацию
контейнера: её ошибка может относиться к другому файлу.

Конфигурации разных узлов могут различаться, если используются host-specific
файлы. Пустой вывод `multipath -ll` без подключённых томов не подтверждает
работоспособность FC-подключения.

### Два последовательных запуска

После первого успешного применения сохранить ID и время старта контейнеров:

```bash
docker inspect --format '{{.Id}} {{.State.StartedAt}}' nova_compute
docker inspect --format '{{.Id}} {{.State.StartedAt}}' cinder_volume
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

## 10. Граница результата

Правка устраняет отсутствие `multipath.conf` в контейнерах. Она не доказывает,
что ошибки `Logical unit not supported` и `I/O error` вызваны именно этим.
После исправления доставки на тестовых томах отдельно проверить attach/detach
и сопоставить WWID, пути Linux и mapping на Dorado.

В этой инструкции нет команд удаления SCSI-путей или multipath-карт.
Патчи драйвера Huawei, Nova и os-brick не входят в изменение доставки файла.

## 11. Что проверено при подготовке инструкции

Локально проверены:

- разбор двух YAML-задач и их вставка в существующие списки задач;
- пути общего шаблона, порядок выбора источника и условия выполнения;
- рендер полных JSON-шаблонов Nova, Cinder volume и опционального Cinder backup:
  36 сочетаний значений флага и дополнительных настроек;
- наличие ровно одной записи для `/etc/multipath.conf` при включённом флаге,
  её отсутствие при выключенном и сохранение остальных JSON-объектов;
- синтаксис четырёх блоков Bash и существование локальных ссылок;
- соответствие 5615 обычных файлов распакованных исходников двум ZIP-архивам:
  исходники не изменены.

Это статическая проверка примеров, а не запуск ролей Ansible на стенде.
Доставка в реальные контейнеры, отсутствие лишнего перезапуска при повторном
`reconfigure` и FC attach/detach пока не проверены.

## Источники и база проверки

Пути ниже относятся к предоставленным ZIP-архивам. Архивы и распакованные
исходники в репозиторий документации не включены.

- Исходное исследование: `openstack_dorado_fc_summary.md` (предоставлено локально, в эту публикацию не включено).
- Доставка конфигурации multipathd: `kolla-ansible-pvs/ansible/roles/multipathd/tasks/config.yml`.
- Монтирования Nova: `kolla-ansible-pvs/ansible/roles/nova-cell/defaults/main.yml`; Cinder: `kolla-ansible-pvs/ansible/roles/cinder/defaults/main.yml`.
- Сравнение конфигурации Docker: `kolla-ansible-pvs/ansible/module_utils/kolla_docker_worker.py`.
- Штатное уведомление обработчиков: `kolla-ansible-pvs/ansible/roles/service-check-containers/tasks/main.yml`.
- Параметры multipath в исходниках Cinder: `cinder-pvs/cinder/volume/driver.py`.

SHA-256 исходного архива `kolla-ansible-pvs.zip`:
`d951a3f31131efc70257883ce33620818db851ff40afbf21b63e3fd0616daec4`.

SHA-256 исходного архива `cinder-pvs.zip`:
`a635f0e994c786c27c729d07e14eeaa8c92a887652f2cb69daca808d8754eaed`.
