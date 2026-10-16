# Ошибки создания и подключения томов Huawei Dorado V6

Дата исследования: 16 октября 2026 года. События в архиве: 15 октября 2026 года, примерно 11:29–15:59 по времени строк журналов.

## Краткий вывод

В журналах обнаружены две группы ошибок: Glance периодически не обнаруживает FC-устройство тома, содержащего образ, и Huawei-драйвер Cinder получает конфликты имён при создании объектов подключения на СХД. Для конфликтов имён наиболее вероятна конкуренция нескольких экземпляров `cinder-volume`, обслуживающих один backend Dorado. Наличие нескольких экземпляров подтверждено оператором; отсутствие общей работающей блокировки ещё нужно проверить в конфигурации контейнеров.

Локальный `HuaweiFCDriver 2.0.9` не объявляет поддержку active-active и наследует `SUPPORTS_ACTIVE_ACTIVE = False`. Его блокировки attach/detach зависят от Tooz. Значение по умолчанию `file://$state_path` при отдельных локальных каталогах на разных узлах не обеспечивает взаимное исключение между узлами.

Отдельно подтверждён дефект обработки исключений: после неудачного создания LUN group драйвер пытается удалить связь с `ID=None`. Ошибка отката заменяет исходную ошибку конфликта имени.

Все 97 записанных ответов на `POST /lun` имеют `error.code = 0`. Обе найденные ошибки создания тома из образа заканчиваются успешной повторной попыткой. Поэтому архив подтверждает нестабильность доступа к образам и подключения томов, но не общий отказ создания LUN на Dorado.

Приоритет действий: проверить фактическую топологию `cinder-volume` и общую координацию, выбрать поддерживаемую схему работы backend, затем отдельно проверить FC-доступ из Glance и повторить сценарии. Исправление обработки исключений в драйвере полезно, но само по себе не обеспечивает active-active.

## Материалы и границы выводов

| Материал | Что проверено |
| --- | --- |
| `logs.15.10.tar` | Четыре журнала: `cinder-api.log`, `cinder-volume.log`, `glance-api.log`, `nova-api.log` |
| `dorado-log-investigation/logs.15.10/` | Извлечённые журналы побайтово совпадают с содержимым архива |
| `cinder-pvs/` и `cinder-pvs.zip` | Шесть использованных файлов драйвера, менеджера и координации побайтово совпадают с ZIP |
| `kolla-ansible-pvs/` | Проверены шаблон `cinder.conf` и выбор backend координации; это исходники, а не фактическая конфигурация стенда |
| Ответ оператора | Один backend Dorado обслуживают несколько экземпляров `cinder-volume` |

Пути вида `logs.15.10/…:номер` и `cinder-pvs/…:номер` указывают на строки в исходном архиве журналов и локальных исходниках. Архивы, журналы и исходный код в эту публикацию не включены; номера строк сохранены для проверки по оригинальным материалам.

SHA-256 архива журналов:

```text
6a5dd95565c4c83eaf5a6da8283fd3f9c2618d112d95118ed3511ecb149632d3
```

В начале cinder-volume.log (`logs.15.10/cinder-volume.log:6`) зарегистрированы Cinder `26.2.1`, `HuaweiFCDriver 2.0.9` и host `huawei@huawei_storage`. Стек исключения совпадает с локальным кодом по ключевым строкам `huawei_driver.py:365`, `rest_client.py:464`, `rest_client.py:905` и `coordination.py:239`. Полное соответствие установленного пакета локальному архиву требует сравнения хешей из контейнера.

Узел, с которого собран архив, не указан. В нём нет конфигураций контейнеров, журналов ядра и `multipathd`, аудита Dorado или полного набора журналов всех `cinder-volume`. Это ограничивает установление конкретных участников гонки и причины отсутствия FC-устройства. Подключение к стенду, изменение конфигурации и перезапуск служб не выполнялись.

## Ошибки чтения образа через Glance

Glance использует Cinder store: в метаданных образа указан `stores: blockstore`, а стек чтения проходит через `glance_store._drivers.cinder.store._open_cinder_volume()` и FC-коннектор os-brick.

Образ `6b4afe07-c879-41a6-9fd5-0442ffdf335b`, `cirros-0.6.3-x86_64-disk`, хранится в томе `eb51b633-7612-4b26-a9dc-23def51bc223`. Этот том успешно создан в 12:23:45 — cinder-volume.log, строка 40 (`logs.15.10/cinder-volume.log:40`).

При создании другого тома из этого образа возникает следующая последовательность:

| Время | Событие | Источник |
| --- | --- | --- |
| 12:26:57.953 | Началось создание `27efa7bc-7424-4e37-8f35-335db47e82ad` из образа | `logs.15.10/cinder-volume.log:42` |
| 12:27:02–12:27:06 | os-brick в Glance повторяет поиск FC-устройства | `logs.15.10/glance-api.log:6154` |
| 12:27:08.115 | `Fibre Channel volume device not found` | `logs.15.10/glance-api.log:6167` |
| 12:27:08.118 | `NoFibreChannelVolumeDeviceFound` при доступе к тому образа `eb51b633-…` | `logs.15.10/glance-api.log:6177` |
| 12:27:10.674 | `GET /v2/images/6b4afe07-…/file` возвращает HTTP 500 | `logs.15.10/glance-api.log:6253` |
| 12:27:10.682 | Cinder получает `glanceclient.exc.HTTPInternalServerError` | `logs.15.10/cinder-volume.log:118` |
| 12:27:10.852 | Начинается повторная попытка для того же тома | `logs.15.10/cinder-volume.log:248` |
| 12:27:34.047 | Том успешно создан | `logs.15.10/cinder-volume.log:917` |

Вторая аналогичная цепочка относится к тому `84af0762-60a9-4ff6-8b61-21032adf1294`: ошибка чтения образа в 15:30:08, HTTP 500 в 15:30:11, успешное создание в 15:30:30 — `logs.15.10/glance-api.log:33348`, `logs.15.10/cinder-volume.log:49623`.

Всего в `glance-api.log` зарегистрировано 14 сообщений FC-коннектора `Fibre Channel volume device not found`. Это число срабатываний, а не число окончательно потерянных томов. Часть относится к загрузке новых образов, часть — к чтению существующего образа.

**Подтверждённая причина HTTP 500 в этих двух цепочках:** Glance не смог подключить FC-устройство исходного тома с образом. Причина отсутствия устройства глубже по стеку пока не установлена. Возможны нестабильный mapping, особенности видимости `/dev` и `/sys` в контейнере, FC zoning, состояние HBA, udev или задержка обнаружения LUN. Успешные чтения того же образа показывают, что ошибка непостоянная. Доказательств, что достаточно только доставить `multipath.conf`, в архиве нет.

## Конфликты объектов подключения на Dorado

В 13:53:41 запрос списка mapping view не возвращает `OpenStack_Mapping_View_2347`. Драйвер фиксирует `view_id: None` и пытается создать этот объект. Через примерно 0,6 секунды Dorado отвечает:

```text
POST /mappingview
NAME = OpenStack_Mapping_View_2347
error.code = 1077948993
description = The object name already exists.
```

Исходные строки: чтение списка и view_id=None (`logs.15.10/cinder-volume.log:32539`), отказ POST (`logs.15.10/cinder-volume.log:32579`). Далее падает `initialize_connection`, а Glance не может подключить том `6eb3737b-6054-4be3-a618-bf905adc90c8` для загрузки образа — `logs.15.10/glance-api.log:19102`.

Аналогичный конфликт повторяется в 15:52:32 для `OpenStack_Mapping_View_2465` — `logs.15.10/cinder-volume.log:64322`. В 13:54:29 и 13:54:31 такой же код возвращается при создании host `ctrl01` и LUN group `OpenStack_LunGroup_2349`.

Все ненулевые коды в записанных REST-ответах этого `cinder-volume.log`:

| Операция | Число ответов | Код | Значение |
| --- | --- | --- | --- |
| Создание mapping view | 2 | `1077948993` | Имя уже существует |
| Создание host | 1 | `1077948993` | Имя уже существует; драйвер затем повторно ищет host |
| Создание LUN group | 1 | `1077948993` | Имя уже существует |
| Откат связи LUN group | 1 | `50331651` | Некорректный параметр `ID=None` |

Операции чтения и создания объекта не атомарны. С учётом нескольких экземпляров `cinder-volume` рабочая гипотеза — другой экземпляр успевает создать объект между GET и POST. Для доказательства конкретной гонки нужны журналы остальных экземпляров и аудит Dorado. Сам ответ `already exists` не исключает задержку видимости объектов в REST API или другой источник изменений СХД.

## Что показывает код Cinder

### Поддержка active-active

`HuaweiFCDriver` наследует `HuaweiBaseDriver`, который наследует `VolumeDriver`. В Huawei-коде переопределения `SUPPORTS_ACTIVE_ACTIVE` нет; базовое значение — `False` в `cinder-pvs/cinder/volume/driver.py:424`. Класс и версия FC-драйвера находятся в `cinder-pvs/cinder/volume/drivers/huawei/huawei_driver.py:229`.

В `cinder-pvs/cinder/volume/manager.py:319` проверка имеет вид:

```python
if self.cluster and not self.driver.SUPPORTS_ACTIVE_ACTIVE:
    # Active-Active configuration is not currently supported by driver ...
    raise exception.VolumeDriverException(message=msg)
```

Проверка срабатывает при заданном `cluster`. Запуск нескольких экземпляров без него не превращает драйвер в поддерживающий active-active. В объектах томов первого сбоя журнал содержит `cluster_name=None`, однако фактические параметры всех сервисов необходимо получить из контейнеров.

Общее требование Cinder к active-active — поддержка со стороны драйвера и корректная распределённая координация — также описано в [официальной документации Cinder HA](https://docs.openstack.org/cinder/latest/contributor/high_availability.html#enabling-active-active-on-drivers). Вывод о конкретном HuaweiFCDriver основан на локальном коде; его нельзя автоматически переносить на другие пакеты драйверов Huawei.

### Блокировки и область их действия

Обе операции защищены одним именем блокировки для хоста подключения:

```python
@coordination.synchronized('huawei-mapping-{connector[host]}')
def initialize_connection(self, volume, connector):
    ...
```

Ссылки: initialize_connection (`cinder-pvs/cinder/volume/drivers/huawei/huawei_driver.py:311`), terminate_connection (`cinder-pvs/cinder/volume/drivers/huawei/huawei_driver.py:441`).

Здесь `connector['host']` — хост, к которому подключают том, например контроллер Glance. Это не обязательно хост процесса `cinder-volume`.

Декоратор использует Tooz; значение по умолчанию (`cinder-pvs/cinder/coordination.py:39`) — `file://$state_path`. Если на разных узлах это разные локальные каталоги, одинаковое имя блокировки не синхронизирует процессы между узлами. Наличие декоратора в стеке подтверждает вызов механизма блокировок, но не подтверждает общую область блокировки.

В шаблоне Kolla (`kolla-ansible-pvs/ansible/roles/cinder/templates/cinder.conf.j2:275`) `backend_url` формируется для Redis либо etcd. В group_vars/all.yml:1506 (`kolla-ansible-pvs/ansible/group_vars/all.yml:1506`) выбор зависит от `enable_redis` и `enable_etcd`. При отсутствии выбора значение в шаблоне не записывается. Наличие etcd в инфраструктуре само по себе не доказывает, что Cinder использует его.

Даже общий DLM не заменяет поддержку active-active в драйвере. Установка `SUPPORTS_ACTIVE_ACTIVE=True` вручную или обход проверки менеджера не является исправлением.

### Неатомарное создание mapping и ошибка отката

В `cinder-pvs/cinder/volume/drivers/huawei/rest_client.py:437` `do_mapping()` сначала ищет LUN group и mapping view, затем создаёт отсутствующие объекты. `_create_lungroup()` и `_add_mapping_view()` завершаются исключением при конфликте имени. Повторного поиска объекта после такого конфликта в этих методах нет. Для host аналогичный повторный поиск уже предусмотрен в add_host_with_check() (`cinder-pvs/cinder/volume/drivers/huawei/rest_client.py:656`).

При сбое `_create_lungroup()` переменная `lungroup_id` остаётся `None`. Обработчик исключения в `cinder-pvs/cinder/volume/drivers/huawei/rest_client.py:487` всё равно вызывает `remove_lun_from_lungroup()`.

В журнале это воспроизведено непосредственно:

```text
13:54:31.576  Create lungroup error: 1077948993
DELETE /lungroup/associate?ID=None&ASSOCIATEOBJTYPE=11&ASSOCIATEOBJID=3616
13:54:31.674  Delete associated lun from lungroup error: 50331651
13:54:31.675  Original exception being dropped
```

Источник: `logs.15.10/cinder-volume.log:33043`. Первичный сбой — конфликт имени; сообщение `Delete associated lun from lungroup error` в этом случае вторично.

Detach также меняет общие объекты: при отсутствии оставшихся LUN он удаляет связи, LUN group, host group, при соответствующих условиях host, затем mapping view — `cinder-pvs/cinder/volume/drivers/huawei/huawei_driver.py:477`. Поэтому проверять нужно взаимное исключение attach и detach вместе. Обработка только повторного POST не устраняет возможную гонку с удалением mapping.

## Сопоставление с дополнительным исследованием

Дополнительный документ [OpenStack: связь ошибки Nova, FC/multipath и свойств образа](openstack_volume_incident_summary.md) разбирает скриншоты и фрагменты журналов для тома `e263b30e-0292-46ec-8ca4-ef4e83fed417`. Этот UUID, UUID образа `109d368a-f426-43cf-85d0-7f72f95d1d1e` и оба приведённых там WWID не найдены ни в одном из четырёх журналов `logs.15.10.tar`. Связь этих наблюдений с операциями из настоящего отчёта не установлена.

Версия о недостаточном размере тома остаётся проверяемой для указанного в дополнительном документе эпизода. Две разобранные здесь ошибки создания относятся к другому образу: CirrOS `6b4afe07-c879-41a6-9fd5-0442ffdf335b` имеет `virtual_size = 117440512`, то есть 112 МиБ. Размеры целевых томов — 10 и 2 ГиБ; обе операции позднее проходят с теми же размерами. В `cinder-volume.log` отсутствуют `ImageTooBig` и `ImageUnacceptable`.

В используемом пути Cinder сначала получает образ через `TemporaryImages.fetch()`, затем проверяет его и вызывает создание целевого LUN. Ссылки: `cinder-pvs/cinder/volume/flows/manager/create_volume.py:985` и `cinder-pvs/cinder/volume/flows/manager/create_volume.py:797`. В двух сбойных попытках Glance не смог подключить исходный том с образом до создания целевого LUN. Поэтому общую схему «создать LUN → подключить → скачать образ» из дополнительного исследования нельзя переносить на эти попытки без уточнения пути выполнения.

Из дополнительного исследования полезны разграничение `hw_vif_multiqueue_enabled` и multipath, необходимость сопоставления UUID/WWID и проверка того, является ли удаление путей причиной сбоя либо последующей очисткой. Эти положения дополняют анализ; приоритет проверки конфликтов mapping, координации между `cinder-volume` и FC-доступа из Glance сохраняется.

## Рекомендации по устранению

| Приоритет | Действие | Ожидаемый результат и условие |
| --- | --- | --- |
| 1 | На всех узлах сравнить установленные Huawei-драйверы, `host`, `backend_host`, `cluster`, backend и координацию | Установить число реально работающих обработчиков одного Dorado backend и область блокировок |
| 2 | Для исследованного драйвера выбрать один активный `cinder-volume` на backend либо управляемый active-passive | Исключить одновременное управление общими объектами несколькими активными экземплярами; смена топологии выполняется после проверки текущих операций и HA-механизма |
| 3 | Если требуется active-active, использовать драйвер и версию, для которых этот режим поддержан и проверен поставщиком | Общий DLM, настройки кластера и испытания обязательны; факт использования Dorado V6 не подтверждает поддержку режима в любом Huawei-драйвере |
| 4 | Проверить FC-доступ на каждом узле Glance и внутри `glance_api` | Отделить отсутствие LUN на хосте от отсутствия устройства в контейнере и от проблемы multipath |
| 5 | Исправить обработку конфликтов имён и откат в Huawei-драйвере | Сохранять исходную ошибку, исключить `ID=None`, корректно обрабатывать объект, созданный конкурентом |
| 6 | После стабилизации повторить создание томов и загрузку/чтение образов | Подтвердить результат по отдельным операциям, а не только по конечному статусу после повторных попыток |

Для пункта 2 нельзя считать `openstack volume service set --disable` остановкой процесса или гарантией прекращения RPC attach/detach. В active-passive один экземпляр должен действительно быть активен, а запуск второго должен исключаться механизмом управления HA. Конкретный порядок переключения зависит от существующей схемы запуска и размещения backend.

Для исправления кода рекомендуется ограниченный набор изменений:

1. При коде конфликта имени повторно найти LUN group или mapping view, проверить найденный объект и продолжить согласование необходимых связей. Другие ошибки не подавлять. Повторы должны быть ограничены.
2. Отслеживать, была ли связь данного LUN добавлена именно текущей операцией. Выполнять откат только для известной и действительно созданной этой операцией связи; не удалять связь только потому, что удалось найти объект по имени.
3. Не выполнять откат с неизвестным `lungroup_id`; сохранить первичное исключение, а ошибку очистки записывать отдельно.
4. Проверить сценарии одновременных attach/attach и attach/detach для одного `connector['host']`, включая работу разных процессов и узлов. Unit-тесты с mock не подтверждают распределённую координацию на стенде.

Патч в рамках исследования не вносился. Его приёмка должна включать конфликт имени при создании обоих типов объектов, сбой создания до получения ID, сбой отката, существующую связь LUN и параллельное подключение разных томов к одному хосту.

## Проверки на работающем стенде

### Конфигурация и версия Cinder

Сначала получить список сервисов:

```bash
openstack volume service list --service cinder-volume
```

Этот список нужно сопоставить с процессами на каждом контроллере: одинаковая идентичность сервиса может скрывать несколько физических экземпляров.

Ниже команды для Podman. При использовании Docker заменить `podman` на `docker`. Уточнить имя контейнера по выводу первой команды.

```bash
sudo podman ps --filter name=cinder_volume --format '{{.Names}} {{.Image}} {{.Status}}'
```

На каждом узле с `cinder_volume` выполнить чтение конфигурации и идентификацию кода. Команда не выводит учётные данные из `backend_url`: печатает схему, адрес и SHA-256 полной строки для сравнения. Это чтение `/etc/cinder/cinder.conf`; если сервис запускается с дополнительными конфигурационными файлами или переопределениями, нужно учесть их порядок отдельно.

```bash
sudo podman exec -i cinder_volume /var/lib/kolla/venv/bin/python - <<'PY'
import configparser
import hashlib
import inspect
from pathlib import Path
from urllib.parse import urlsplit
from cinder import coordination
from cinder.volume.drivers.huawei import common, huawei_driver, rest_client

cfg = configparser.ConfigParser(interpolation=None, strict=False)
paths = cfg.read('/etc/cinder/cinder.conf')
if not paths:
    raise SystemExit('cinder.conf was not read')
print('config_files:', paths)
for section in ['DEFAULT'] + cfg.sections():
    keys = ('host', 'cluster', 'enabled_backends', 'default_volume_type') if section == 'DEFAULT' else (
        'backend_host', 'volume_driver', 'volume_backend_name',
        'use_multipath_for_image_xfer', 'enforce_multipath_for_image_xfer')
    values = {k: cfg.get(section, k) for k in keys if cfg.has_option(section, k)}
    if values:
        print(section, values)
url = cfg.get('coordination', 'backend_url', fallback=None)
if url:
    parsed = urlsplit(url)
    print('coordination_scheme:', parsed.scheme)
    print('coordination_host:', parsed.hostname)
    print('coordination_port:', parsed.port)
    print('coordination_url_sha256:', hashlib.sha256(url.encode()).hexdigest())
else:
    print('coordination_backend_url: not set in this file; inspected source default is file://$state_path')
print('HuaweiFCDriver.VERSION:', huawei_driver.HuaweiFCDriver.VERSION)
print('HuaweiFCDriver.SUPPORTS_ACTIVE_ACTIVE:', huawei_driver.HuaweiFCDriver.SUPPORTS_ACTIVE_ACTIVE)
for module in (huawei_driver, rest_client, common, coordination):
    path = Path(inspect.getfile(module))
    print('source:', path, 'sha256:', hashlib.sha256(path.read_bytes()).hexdigest())
PY
```

Совпадение хешей URL подтверждает совпадение строк, но не доступность DLM и не корректное взаимное исключение. Разные строки могут указывать на один сервис. Дополнительно проверить ошибки Tooz, реальные конечные адреса и namespace координации, имена блокировок и значения `connector['host']`.

### FC и multipath со стороны Glance

На всех узлах, обслуживающих Glance Cinder store, проверить HBA и видимость устройств:

```bash
hostname
cat /sys/class/fc_host/host*/port_name
cat /sys/class/fc_host/host*/port_state
ls -l /dev/disk/by-path/*fc*
sudo multipath -ll
```

`multipath -ll` выполнять в том окружении, где установлен multipath-tools: на хосте или в контейнере `multipathd`. Отсутствие команды на хосте не означает отсутствие multipath в системе. Наличие устройства нужно сопоставлять с конкретным активным attachment, WWID и Host LUN ID; после штатного detach mapping может уже отсутствовать.

Внутри Glance проверить доступность конфигурации и FC-устройств:

```bash
sudo podman exec glance_api sh -c 'hostname; ls -l /etc/multipath.conf; ls -l /sys/class/fc_host; ls -l /dev/disk/by-path/*fc*'
sudo podman exec glance_api grep -nE '^\[|^[[:space:]]*(enabled_backends|default_backend|cinder_use_multipath|cinder_enforce_multipath|cinder_volume_type|rootwrap_config)[[:space:]]*=' /etc/glance/glance-api.conf
```

Проверить параметры в фактической секции store `blockstore`, конфигурацию `multipathd`, mounts `/dev` и `/sys`, доступность rootwrap/privsep и сопоставление WWPN контроллеров с host/mapping на Dorado. Настройки Cinder `use_multipath_for_image_xfer` относятся к передаче образа самим Cinder; они не заменяют настройки Glance `cinder_use_multipath` и `cinder_enforce_multipath`.

Если LUN виден на хосте, но не внутри `glance_api`, приоритет — контейнерная видимость устройства и udev. Если LUN не виден и на хосте при действующем attachment, приоритет — mapping, WWPN, zoning, состояние HBA и сообщения ядра. Если пути видны, а multipath-устройство не собирается, анализировать конфигурацию и состояние multipath.

### Корреляция между узлами и СХД

Собрать журналы всех `cinder-volume` и `glance-api` за интервалы 12:26:55–12:27:35, 13:53:35–13:54:40, 15:29:55–15:30:35 и 15:52:25–15:52:40, а также аудит Dorado за эти интервалы. Уточнить часовые пояса: временные метки в начале строк и UTC внутри notification payload в архиве различаются на три часа.

Искать операции над `OpenStack_Mapping_View_2347`, `OpenStack_LunGroup_2349`, `OpenStack_Mapping_View_2465`, а также томами из таблицы выше. Для каждого attach и detach связать request ID, узел `cinder-volume`, `connector.host`, WWPN, LUN ID и время изменения mapping на СХД. Одновременные изменения одного объекта разными экземплярами подтвердят гипотезу гонки.

Для диагностики не требуется удалять mapping view или LUN group вручную, сбрасывать статусы томов, выполнять массовый rescan или принудительный flush multipath. Такие действия меняют исследуемое состояние и могут затронуть действующие подключения.

## Дополнительные ошибки

| Событие | Интерпретация и действие |
| --- | --- |
| `Volume type with name huawei_storage could not be found`, 12:19:00 | Проверить `default_volume_type` и существование одноимённого типа. Имя типа и имя backend — разные сущности. `logs.15.10/cinder-api.log:9763` |
| `Unable to get Cinder internal context, will not use image-volume cache` | Кеш включён, но внутренний контекст не настроен. В этом сценарии Cinder продолжает через скачивание образа; это не исходная причина `NoFibreChannelVolumeDeviceFound`. `logs.15.10/cinder-volume.log:43` |
| `VolumeLimitExceeded`, лимит 10 томов, 13:52:47 | Отдельная причина неудачной загрузки образа через Cinder store. Проверить проект, которому принадлежат создаваемые тома, квоту и оставшиеся ресурсы тестов. `logs.15.10/glance-api.log:18834` |
| Отказ удаления томов из-за состояния или attachment | Для каждого тома сначала установить наличие действующих пользователей и attachments; HTTP 400 сам по себе не разрешает принудительную очистку. `logs.15.10/glance-api.log:17689` |
| `ResourceProviderUpdateConflict` при удалении compute из aggregate | Ошибка Nova/Placement в отдельной операции. Связь с рассмотренными FC/mapping сбоями не установлена. `logs.15.10/nova-api.log:27759` |

## Критерии проверки исправления

Проверку выполнять на выделенных тестовых ресурсах после согласованного изменения топологии или установки патча. Проверить создание пустого тома, загрузку и скачивание образа через Cinder store, создание тома из образа, подключение и отключение на каждой используемой compute-ноде. Повторить последовательные и параллельные операции; для выбранной HA-схемы отдельно проверить переключение активного сервиса.

Условия успешной проверки:

1. В выбранной схеме обеспечено единоличное управление backend либо поставщик подтверждает active-active для установленного драйвера, а межузловые блокировки проверены практически.
2. В тестовых операциях отсутствуют необработанные `1077948993`, запросы с `ID=None`, `NoFibreChannelVolumeDeviceFound` и связанные HTTP 500.
3. Загрузка и скачивание образа завершаются успешно, контрольная сумма скачанного содержимого совпадает с исходной.
4. Параллельное отключение одного тестового тома не нарушает доступ к другому тому на том же хосте; существующие подключения остаются доступны.
5. После тестов не остаются неожиданные attachments, зависшие операции и объекты mapping, не соответствующие действующим подключениям.

Конечный статус `available` после повторной попытки следует учитывать отдельно от ошибок первой попытки. Архив уже содержит такие успешные повторы, поэтому один успешный запуск ВМ не доказывает устранение нестабильности.

## Хеши исследованного кода

Пути приведены относительно `cinder-pvs/`.

| Файл | SHA-256 |
| --- | --- |
| `cinder/volume/drivers/huawei/huawei_driver.py` | `3f92995efd15a0b6190c5c14e596fe05461b79d868be78d015039ebcabf87b0c` |
| `cinder/volume/drivers/huawei/rest_client.py` | `66b8c4bf8899ad2e91cc4bbb33ba14a37272130efb5a228508fde8e7c06b5b7b` |
| `cinder/volume/drivers/huawei/common.py` | `14c14b72d6ed1dd58ecf02f57afeee5c53e8776a26bac6ddd49b1cb8ad67024c` |
| `cinder/volume/driver.py` | `5638c91d4929a391f83a53705c19dbb5245ef74153bc2556b92e78de1b0b5224` |
| `cinder/volume/manager.py` | `1b0191f33e09189e63521394c2e87a1f6c6b47acb87d683924fe1bd6b3de87d0` |
| `cinder/coordination.py` | `d5aaf0c534c891b8387150bd8fed5f7d9b7ebf6a0bfede451379c9924ead6973` |
