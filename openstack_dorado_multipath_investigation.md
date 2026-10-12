# OpenStack Epoxy 2025.1 / Kolla / Podman / Huawei Dorado V6
## Исследование FC, multipath и жизненного цикла томов

Дата проверки источников: 12 октября 2026 года.

**Область исследования:** предоставленные скриншоты, архив `os-brick-pvs.zip`, исходники Kolla-Ansible/Kolla и Cinder ветки `stable/2025.1`, документация и исходники multipath-tools. Проверенные upstream-ветки не заменяют проверку commit/image digest установленной модифицированной сборки. Для объяснения конкретных механизмов multipath-tools использована также фиксированная версия 0.9.4: это не утверждение, что она установлена в кластере.

**Ограничение:** доступа к работающему кластеру, полным журналам одной операции и аудиту Dorado нет. Исследование устанавливает устройство системы и проверяемые сценарии отказа, но не доказывает единственную первопричину исходного инцидента.

## 1. Основной вывод

Проблема не сводится к выбору «multipath на хосте или в контейнере». DM-multipath работает в ядре хоста; его управляющий демон может быть контейнеризирован. Nova/Cinder запускают собственные клиентские утилиты и os-brick, которые должны видеть соответствующие устройства и корректное окружение управления. Один общий `multipath.conf` не обеспечивает автоматически согласованность этих компонентов. [S1, S2, L1]

Наиболее существенные результаты исследования:

- Отсутствие `multipath.conf` внутри `nova_compute` на `compute03` подтверждено скриншотом, но остановка демона и потеря всех FC-путей этим не доказаны.
- В штатной Kolla исходный файл создаёт Ansible, а механизм запуска контейнера копирует его в собственный `/etc/multipath.conf`. Это не общий файл, которым по умолчанию управляет сам `multipathd`.
- Bind-mount отдельного файла может остаться привязанным к старому файловому объекту после атомарной замены файла на хосте. Совпадение строк `Source` в `podman inspect` не доказывает актуальность содержимого.
- Пользовательский конфиг в роли multipathd заменяет штатный целиком. При этом можно потерять `skip_kpartx yes`, добавленный в Kolla для предотвращения проблем отключения томов.
- В присланном os-brick воспроизводится узкий сценарий неполной FC-очистки при ошибке flush. Он требует подтверждения в журнале реальной операции и не означает, что каждый multipath-detach неисправен.

## 2. Что показывают предоставленные материалы

| Наблюдение | Что можно заключить | Чего оно не доказывает |
|---|---|---|
| `nova_compute` на `compute03`: `/etc/multipath.conf does not exist, blacklisting all devices` | Конкретный запуск клиентской утилиты не видит нужного файла и исключает устройства | Что управляющий демон остановлен или ВМ использует одиночный путь |
| `ctrl01`: `Logical unit not supported`, затем `I/O error` | SCSI-запрос к logical unit завершился ошибкой; код additional sense — `25/00` | Физическую неисправность дисков Dorado или причину изменения mapping |
| `error 2 in pathinfo, discarding path` | В multipath-tools код 2 — `PATHINFO_SKIPPED`; это не errno 2 и не код поломки диска | Отсутствие здоровых путей у работающего демона |
| REST-вызов `remove_fc_from_host` с успешным ответом | Привязка инициатора к Host удалялась | Что это было ошибочно: операция бывает частью штатного удаления последнего подключения |
| Здоровая топология слева и ошибка справа на последнем кадре | Есть результаты с разных серверов | Что изменение уже исправило тот же узел: слева указан `ktte02-rh1p1`, справа `compute03` |

Коды sense и PATHINFO проверены по первичным исходникам. [S24, S25]

Ошибки ядра относятся к 12:18:58, а показанный REST detach — примерно к 12:27:17. Нельзя считать их одной причинно-следственной последовательностью без промежуточных журналов. Сопоставление требуется по **узлу, UUID тома, WWID, request ID и времени с часовым поясом**, а не только по `sdX`.

## 3. Где действительно работает multipath

| Уровень | Роль | Значение для диагностики |
|---|---|---|
| Ядро хоста | SCSI, FC HBA, device-mapper и карты multipath | ВМ и контейнеры работают с устройствами этого ядра; отдельной SAN в каждом контейнере нет |
| Управляющий процесс | `multipathd` наблюдает пути и управляет картами | Для одной общей системы устройств следует иметь одного согласованно управляемого демона |
| Клиенты и обработчики событий | os-brick, `multipath`, клиент `multipathd`, udev | Разные процессы могут читать разные файлы и использовать разные версии библиотек |

В штатной Kolla сервис multipathd привилегированный, с доступом к `/dev`, `/run` и модулям хоста. Контейнеризация демона не переносит DM-multipath из ядра хоста. [S1, S2]

### Почему недостаточно только сокета

В присланном `linuxscsi.py` os-brick проверяет демон командой `multipathd show status`, но также использует локальные `multipath -l`, `multipath -C` и `multipath -f` в соответствующих ветках кода. Это не полностью «тонкий клиент» к единственному демону. Часть операций сама утилита может делегировать демону; конкретное поведение зависит от версии. [L1, S16]

### Почему недостаточно только общего `/run`

В upstream multipath-tools 0.9.4 соединение идёт через **абстрактный Unix-сокет**, а не обычный файл: `/org/kernel/linux/storage/multipathd` с нулевым первым байтом `sun_path`. Поэтому для такой сборки существенен network namespace; одного общего каталога `/run` недостаточно. В штатном Podman worker Kolla задан host networking. Проверять всё равно следует фактическую сборку и namespaces, а не предполагать конкретный путь сокета. [S13, S14]

Соединение через активный systemd socket-unit может запустить соответствующий `multipathd.service`. До опроса клиента полезно установить, какой daemon/service/socket уже действует, чтобы диагностика не стала случайным запуском дополнительного управления. [S15]

## 4. Кто формирует и кто читает конфигурацию в Kolla 2025.1

При стандартных значениях путей цепочка выглядит так:

```text
Bootstrap: /etc/kolla/config/multipath.conf
    или host-specific multipath/<inventory_hostname>/multipath.conf
    или штатный шаблон роли
        |
        | Ansible template
        v
Целевой хост: /etc/kolla/multipathd/multipath.conf
        |
        | каталог конфигурации смонтирован read-only
        v
multipathd: /var/lib/kolla/config_files/multipath.conf
        |
        | kolla_set_configs, копирование
        v
multipathd: /etc/multipath.conf
        |
        | чтение при запуске / перечитывании
        v
Конфигурация в памяти демона
```

Порядок выбора источника проверен в `roles/multipathd/tasks/config.yml`; это `with_first_found` и `template`, а не слияние пользовательского файла с defaults. Копирование в `/etc/multipath.conf` задано в `multipathd.json.j2`. [S3, S4]

**Ответ на вопрос о владении:** в штатной схеме источник политики управляется Ansible; механизм Kolla записывает runtime-копию; multipathd читает её. Изменение внутренней копии не записывается обратно в read-only каталог источника. В вашей доработанной схеме роли могут быть другими — их устанавливают `config.json`, mounts и entrypoint, а не имя контейнера.

В просмотренных стандартных `nova_compute_default_volumes` и `cinder_volume_default_volumes` нет автоматического общего `/etc/multipath.conf`. Его доставка клиентам через `*_extra_volumes` — отдельная настройка. [S6, S7]

**Не следует одновременно назначать `/etc/multipath.conf` bind-mount-точкой и оставлять Kolla ответственным за замену этого же destination.** `set_configs.py` удаляет destination перед копированием. Удаление mountpoint может завершиться `EBUSY`; перевод монтирования из `ro` в `rw` сам по себе эту несовместимость не устраняет. [S5, S10]

## 5. Почему «все монтируют один путь» не гарантирует общую актуальную версию

На скриншоте добавлен файловый bind:

```yaml
nova_compute_extra_volumes:
  - "/etc/kolla/multipathd/multipath.conf:/etc/multipath.conf:ro"
```

Нужно различать два вида изменения источника.

**Запись в существующий файл без его замены:** читатели того же файлового объекта увидят изменённые байты. Однако демон не обязан автоматически заменить уже загруженные в память настройки.

**Атомарная замена файлом с новым inode:** уже действующий single-file bind остаётся связан со старым файловым объектом. Новый файл по прежнему имени на хосте и файл внутри клиента могут разойтись. Такое поведение bind-mount подтверждено разработчиками контейнерного runtime. Ansible `template` по умолчанию использует атомарные операции. [S8, S9]

Возможный результат после изменения конфигурации:

```text
Хостовый путь                  → новая версия B
Каталог-источник multipathd    → новая версия B
Копия и память multipathd     → B после применения
Файловый bind Nova/Cinder      → прежняя версия A до обновления mount
```

Это **риск при последующих обновлениях**, а не доказанное объяснение уже увиденного отсутствующего файла: старый bind обычно сохраняет старое содержимое, а не делает destination отсутствующим.

Флаг `:shared` относится к распространению событий монтирования, а не к отслеживанию атомарной замены файла по имени. SELinux-флаги `:z`/`:Z` тоже не являются механизмом синхронизации содержимого. [S12]

### Почему недостаточно произнести «запустить reconfigure»

В проверенном Podman worker сравнение volumes сопоставляет source/destination и режимы, но не вычисляет хеш содержимого каждого произвольного extra-volume. Отдельная проверка конфигурации запускает `kolla_set_configs --check`. Если дополнительный multipath-файл не входит в управляемый `config.json` Nova, изменение только его содержимого нельзя считать гарантированным триггером обновления Nova. [S11]

Следовательно, процедура изменения политики должна явно охватывать **всех её потребителей**, а не только обработчик роли multipathd. Штатная проверка Kolla уведомляет handlers тех сервисов, у которых обнаружила изменения. [S30]

## 6. Важная отдельная причина проблем detach: kpartx

В штатном шаблоне Kolla 2025.1 присутствует `skip_kpartx yes`, наряду с `find_multipaths yes` и `user_friendly_names no`. Это пример upstream-политики, не готовый универсальный конфиг для всех устройств вашего хоста. [S17]

В релизных примечаниях Kolla задокументирован **LP#2078973**: `skip_kpartx` добавлен, чтобы создание partition mappings не блокировало удаление multipath-карты os-brick при отключении тома. [S18]

Поскольку пользовательский `multipath.conf` заменяет шаблон целиком, проверьте, не потерялся ли этот параметр при добавлении собственного профиля Dorado.

Механизм не ограничивается контейнером: udev-правила kpartx реагируют на multipath DM-устройства и учитывают `DM_SUBSYSTEM_UDEV_FLAG1`, соответствующий skip_kpartx. В исследованных правилах этот флаг предотвращает автоматический запуск kpartx. [S19]

Признаки для проверки: дочерние partition-карты, `map in use`, ненулевые holders после того, как реальный потребитель тома уже отключён. Наличие любого holder само по себе не ошибка: dm-crypt, LVM и QEMU могут быть законными потребителями. Нужно установить владельца каждого звена.

Изменение политики не заменяет проверку уже существующих зависимостей. Не удаляйте partition-карты массово. Если сам хост использует SAN-boot или другие необходимые разделы на multipath, запрет partition discovery следует проектировать для нужных OpenStack LUN, а не распространять без разбора на все устройства.

## 7. Файл, эффективная политика и состояние — разные объекты

Проверять нужно как минимум:

1. Управляемый исходный файл и runtime-файлы всех реальных клиентов.
2. Настройки, уже загруженные демоном.
3. Фактическую топологию карт и состояние путей.
4. Версии multipath-tools, встроенные hardware defaults, дополнительные конфиги и udev-правила.
5. Используемое данной сборкой состояние WWID/alias bindings и его сохранение при пересоздании контейнера.

В multipath-tools встроенные профили устройств и дополнительные настройки участвуют в выборе эффективной политики. Файлы WWID/bindings — состояние конкретного хоста; их нельзя автоматически превращать в общий кластерный файл или считать эквивалентом `multipath.conf`. Пути хранения зависят от версии/пакета. [S20]

Две разные проверки:

```bash
multipath -t
multipathd show config
```

В проверенной версии 0.9.4 первая печатает конфигурацию, разобранную локальным процессом; вторая запрашивает уже действующий демон. Для целей диагностики это не взаимозаменяемые источники. `multipathd reconfigure` перечитывает конфигурацию и может перезагружать изменившиеся карты: это операция применения, а не безобидная команда просмотра. [S16, S21]

## 8. Что действительно воспроизведено в присланном os-brick

Исходники из архива перепроверены. SHA-256 файла `os_brick/initiator/connectors/fibre_channel.py`:

```text
4effea20b90c3f4de0de86739388a9c880db80dc18c3ffc71a92c1ef93c1f80f
```

Повторный запуск восьми изолированных проверок выбранных тел методов завершился успешно. Обращения к ОС заменены заглушками. Декораторы, реальный Cinder, udev, FC и Dorado этим не тестировались. [L1, L2]

### 8.1. Ошибка flush может оставить SCSI-путь

`fibre_channel.py:418–443`: `_remove_devices` получает `force`, но вызывает `remove_scsi_device(device_path, flush=flush)` без передачи `force`.

`linuxscsi.py:137–154`: при `flush=True` и ошибке сброса буферов низкоуровневый метод с `force=False` по умолчанию выходит до запроса sysfs delete. Внешний обработчик может перехватить ошибку, но не продолжает прерванный метод.

| Условия изолированной проверки | Запрос удаления пути | Исключение наружу |
|---|---|---|
| Успешный flush | Выполнен | Нет |
| Ошибка flush, внешний force=True, ignore_errors=False | Не выполнен | Есть |
| Ошибка flush, внешний force=True, ignore_errors=True | Не выполнен | Нет |

**Существенное ограничение:** речь о ветке, где конкретный путь требует flush. При нормальном использовании dm-multipath его отдельным sd-путям обычно не нужен индивидуальный flush; групповое удаление карты обрабатывается отдельно. Это следует из `requires_flush`, строки 328–359. Поэтому данный результат нельзя обобщать на все FC-disconnect.

В Cinder `_detach_volume` сначала вызывает локальный disconnect, затем terminate_connection; при force обработка может продолжиться после ошибки. Это даёт проверяемый сценарий «локальный путь остался → mapping снят → последующие обращения ошибочны», но не доказывает, почему первоначально отказал flush. [S22]

### 8.2. enforce не заменяет проверку фактического пути

`base.py:132–151` проверяет поддержку multipath, а `base.py:170–214` содержит возврат исходного одиночного пути, если карта не найдена. Изолированная проверка этой функции вернула single path даже при доступном демоне и enforce=True. В полном connect есть дополнительные действия, поэтому это не end-to-end доказательство результата любого attach.

Практический критерий — реальный путь тома и его цепочка device-mapper, а не только конфигурационный флаг. Устройства dm-crypt при шифровании также нужно прослеживать до multipath-основания. [L1, L2]

### 8.3. Неизвестные параметры не становятся рабочими от записи в ini

В присланном дереве нет использования `os_brick_retry_attempts`, `os_brick_scsi_scan_delay`, `enforce_multipath_io_with_iscsi`. Отдельные изменения вашего Cinder архивом os-brick не проверяются.

В `opts.py` действительно есть `[os_brick] wait_mpath_device_attempts=4`, `wait_mpath_device_interval=1`: это ожидание готовности через `multipath -C`, с интервалами retry 2, 4, 8 секунд при default. Это не исправление незавершённого detach. [L1]

Нельзя рекомендовать просто «обновиться до 6.11.1»: характерные FC-изменения этого поколения уже есть в архиве, а исправление orphaned devices в release notes 6.11.1 относится к iSCSI. [S23]

## 9. Проверка Dorado и SAN

`Logical unit not supported` — ответ о конкретном logical unit, а не сообщение «модель Dorado не поддерживается OpenStack». Увеличение времён ожидания не возвращает снятый mapping. [S24]

В штатном Huawei FC-драйвере после удаления тома проверяется число объектов соответствующей LUN Group. Если оставшихся LUN нет, очистка может включать удаление FC-инициаторов из Host. Следовательно, `remove_fc_from_host` само по себе бывает нормальным. Сравнивать нужно установленный Huawei-драйвер, аудит СХД и реально оставшиеся подключения. [S26]

**Дополнительная деталь исходников:** `left_lunnum` начинается с `-1`, а cleanup-ветка выбирается, когда значение не больше нуля. Если нужная LUN Group не найдена, значение может остаться `-1`. Это не означает само по себе дефект: очистка остаточных объектов бывает намеренной. Но такая проверка не является доказательством отсутствия всех других потребителей Host, особенно при ручных mapping или совместном использовании Host несколькими backend. Нужны реальное состояние СХД и установленный код. [S26]

Для одной операции нужно установить: WWID LUN; Host/Host Group/LUN Group/Mapping View; WWPN инициаторов; какие тома должны остаться доступны; кто изменил mapping; не участвовали ли ручные операции и другие backend. При live multiattach существование других attachments является отдельным обязательным условием проверки до любой очистки.

Универсальный ALUA-профиль для слов «Dorado V6» здесь не предлагается: нет версии прошивки, Host Access Mode и сведений о HyperMetro. Встроенный профиль multipath-tools также не равен подтверждённой Huawei матрице совместимости. [S20]

`features='1 queue_if_no_path'` не доказывает бесконечное ожидание: при конечном `no_path_retry` kernel queueing тоже используется, затем может быть выключен демоном. `no_path_retry 15` означает число повторов, не 15 секунд. `hwhandler='0'` и `prio=1` на одном фрагменте не устанавливают причину без контекста целевого режима массива. [S20]

## 10. Целевая схема управления

Для этой Kolla-инсталляции разумно сначала сохранить выбранное место запуска демона и устранить рассогласования. Переносить multipathd в systemd хоста ради одного сообщения не обосновано.

Предлагаемые инварианты:

- У политики есть один управляемый источник на уровне автоматизации и версия/хеш, сопоставимый со всеми её потребителями.
- На хосте определён один управляющий multipathd; дополнительные service/socket-units не запускают конкурирующую схему.
- Изменение политики включает её доставку, применение демоном и проверку состояния карт, а не только изменение YAML.
- Фактический I/O каждого проверяемого тома идёт по ожидаемой цепочке устройств; работающие потребители известны до detach.
- Локальная очистка и снятие доступа на СХД сопоставлены по одной операции.

### Реализация доставки конфигурации

**Предпочтительный вариант для сопровождаемой доработки Kolla:** конфигурационные каталоги монтируются как каталоги; необходимые файлы клиентов входят в их управляемый `config.json`. Это делает доставку и сравнение конфигурации частью lifecycle сервисов. Потребуются изменения поддерживаемой роли/шаблонов: это не штатная возможность, автоматически включаемая одной переменной.

**Альтернатива:** выделенный стабильный каталог политики монтируется read-only во всех нужных consumers, а `/etc/multipath.conf` указывает на файл в нём. В images/entrypoint следует согласовать symlink и исключить его удаление `kolla_set_configs`. Не монтировать весь host `/etc` поверх контейнерного. Каталог устраняет именно проблему замены отдельного файла; перечитывание демоном всё равно требуется.

**Сохранение single-file bind допустимо только с явным lifecycle:** при изменении файла обновляются mounts всех consumers, затем проверяются их хеши и эффективная политика. На автоматическое обнаружение содержимого arbitrary extra-volume полагаться нельзя.

Политика может отличаться между хостами, если отличается их назначение. «Единый источник» не означает бездумно одинаковые настройки для SAN-boot и только гостевых LUN.

## 11. Диагностика без удаления и пересканирования устройств

Команды выполнять от root на проблемном **целевом хосте**, не на bootstrap. Имена контейнеров проверять по фактическому списку. Команды просмотра не заменяют согласования чтения production-журналов; вывод может содержать чувствительные метаданные инфраструктуры.

### 11.1. Зафиксировать узел, контейнеры и управляющий процесс

```bash
hostname -f
date --iso-8601=seconds
uname -r
podman ps --format '{{.Names}} {{.Image}}'
pgrep -a -x multipathd
systemctl show multipathd.service multipathd.socket \
  -p Id -p ActiveState -p SubState -p MainPID -p ExecStart
ss -xlpn | grep -Ei 'multipath|/org/kernel/linux/storage' || true
```

Отсутствие host systemd-unit допустимо, если демон намеренно управляется Kolla. Не запускать `systemctl enable --now multipathd` в качестве автоматического «исправления».

### 11.2. Проверить mounts и файлы

```bash
# Повторить для multipathd и cinder_volume, если они есть на этом хосте.
podman inspect nova_compute --format '{{json .Mounts}}'
podman inspect nova_compute --format '{{.State.Pid}}'

stat -Lc '%d:%i size=%s mtime=%y %n' \
  /etc/kolla/multipathd/multipath.conf
sha256sum /etc/kolla/multipathd/multipath.conf

podman exec -u 0 nova_compute sh -c '
  ls -l /etc/multipath.conf
  readlink -f /etc/multipath.conf
  stat -Lc "%d:%i size=%s mtime=%y %n" /etc/multipath.conf
  sha256sum /etc/multipath.conf
'
```

Сравнить на том же хосте `multipathd`, `nova_compute`, `cinder_volume` и `/etc/multipath.conf` хоста, если host-side утилиты участвуют в обработке.

Для настоящего bind одного файла сопоставимы device/inode и хеш. Для Kolla-копии другой inode нормален: нужно совпадение ожидаемого содержимого и версии. Одинаковый хеш доказывает одинаковые байты сейчас, но не гарантирует корректность будущих обновлений.

Дополнительно прочитать безопасно выбранную часть `/etc/kolla/multipathd/config.json` или соответствующий файл внутри контейнера: источник, destination, strategy. Не публиковать целиком service config/env с паролями.

### 11.3. Сравнить демон и локальные утилиты

После установления действующего демона и проверки socket-unit:

```bash
podman exec -u 0 multipathd multipathd show status
podman exec -u 0 multipathd multipathd show maps topology
podman exec -u 0 multipathd multipathd show config

podman exec -u 0 nova_compute multipathd show status
podman exec -u 0 nova_compute multipath -t

# На хосте с локальными операциями Cinder:
podman exec -u 0 cinder_volume multipathd show status
podman exec -u 0 cinder_volume multipath -t
```

В отсутствие контейнера multipathd при намеренном host-managed варианте соответствующие daemon-запросы выполняются средствами ОС. Успех `exec -u 0` проверяет инфраструктуру, но не заменяет проверку реального privsep/rootwrap и ошибок доступа у сервиса.

В rpm-based окружениях сравнить установленные версии `device-mapper-multipath`, `device-mapper-multipath-libs`, `kpartx` на хосте и в нужных контейнерах. Отдельно зафиксировать image IDs/digests, Kolla commit и фактическую версию os-brick.

### 11.4. Проверить один том и его holders

```bash
lsblk -o NAME,TYPE,SIZE,PKNAME,HCTL,WWN,MOUNTPOINT
dmsetup ls --tree
dmsetup info -c
```

Далее — только для заранее установленной карты нужного WWID, не произвольно выбранного `dm-0`:

```bash
# dm-N — placeholder: заменить картой исследуемого тома.
cat /sys/block/dm-N/dm/uuid
ls -l /sys/block/dm-N/slaves /sys/block/dm-N/holders
udevadm info --query=property --name=/dev/dm-N
```

Для ВМ изучить её block-device source в libvirt/domain XML штатным способом с существующей аутентификацией; разрешить symlink до устройства. Проверять всю цепочку, включая dm-crypt при шифровании. Статус OpenStack `in-use` не заменяет эту проверку.

### 11.5. Проверить установленный FC-модуль

```bash
podman exec -i cinder_volume /var/lib/kolla/venv/bin/python - <<'PY'
import hashlib
import inspect
from importlib.metadata import version
from pathlib import Path
from os_brick.initiator.connectors import fibre_channel

path = Path(inspect.getsourcefile(fibre_channel))
print('os-brick:', version('os-brick'))
print('source:', path)
print('sha256:', hashlib.sha256(path.read_bytes()).hexdigest())
PY
```

Проверить также `nova_compute`. Путь venv соответствует типовой Kolla-сборке и может отличаться в вашем образе.

### 11.6. Сопоставить одну ошибочную операцию

Нужны kernel log, nova-compute/cinder-volume, multipathd и аудит Dorado за один интервал. В os-brick искать начало disconnect, ошибки flush, `devices to remove`, `Remove SCSI device`, `leftovers may remain`, `Disconnect failed`; затем driver terminate/unmap и удаление инициаторов. Некоторые строки доступны только при debug.

Если требуется debug, включать ограниченно на выбранном тестовом узле и учитывать, что backend-запросы могут содержать чувствительные данные. При включённом SELinux дополнительно проверить AVC, но не отключать SELinux и не выполнять массовый relabel `/dev`, `/run` или `/etc`.

## 12. План устранения и критерии проверки

| Этап | Действие после проверки | Критерий |
|---|---|---|
| A | Зафиксировать текущие роли, mounts, хеши, версии и topology | Известно, кто читает какой файл и какой daemon обслуживает клиентов |
| B | Исправить подтверждённый разрыв доставки конфигурации на тестовом узле | Клиенты видят ожидаемую версию; изменение переживает предусмотренный lifecycle |
| C | Проверить эффективные настройки guest LUN и kpartx/holders | Нет непредусмотренных потребителей, мешающих штатному detach |
| D | Сопоставить реальный FC-disconnect с unmap | Неисправность локальной очистки не маскируется успешным REST-ответом |
| E | При совпадении code path согласовать исправление os-brick | Unit/regression-тест и стендовый сценарий проходят без разрушения соседних томов |
| F | Раскатать проверенную схему по ролям | Повторяемая конфигурация и контроль состояния после изменений |

Стендовые сценарии: подключение и отключение одного тома; отключение одного из двух при продолжающемся I/O второго; отключение последнего; создание тома из образа и обратная операция на controller; повторное применение конфигурации без изменений; реальное изменение политики с проверкой всех consumers; контролируемая потеря одного FC-пути и восстановление.

Запись и проверку контрольных сумм выполнять только на выделенных тестовых данных. Успех — не только отсутствие сообщений: данные корректны, нужные paths сохранены, посторонние тома не затронуты, полностью отключённый и никем не используемый том не оставляет нежелательных устройств.

**Не выполнять вслепую:** `multipath -F`, удаление всех `sdX`, `dmsetup remove -f`, массовый kpartx cleanup, принудительное удаление attachments, generic FC-rescan всего хоста и запуск второго демона. Не менять таймауты как замену исправлению mapping/lifecycle.

## 13. Какие данные остаются необходимыми

Для окончательного root cause нужны mounts и эффективные конфиги с `compute03` и `ctrl01`; версия host ОС/ядра/HBA driver и firmware; multipath-tools и image digests; установленный Huawei Cinder driver; версия/режим Dorado и HyperMetro; журнал одной операции с UUID/WWID и аудит mapping. Отдельно важен тип операции, после которой возникает сбой: image transfer, attach, detach или удаление.

Полная актуальная Huawei-матрица Host Access Mode/прошивка/HyperMetro не была доступна для проверки через полученную страницу поддержки. Поэтому здесь нет неподтверждённого универсального `devices { ... }` для Dorado; это часть исследования, требующая точных данных СХД и соответствующего vendor guide.

## Источники и воспроизводимость

Внешние ссылки — первичные исходники и документация, проверенные 12.10.2026. Ветки `stable/2025.1` могут изменяться; их содержимое не доказывает содержимое установленных образов.

- [S1: multipath-tools, компоненты](https://raw.githubusercontent.com/opensvc/multipath-tools/master/README.md)
- [S2: Kolla-Ansible, multipathd volumes и privileges](https://raw.githubusercontent.com/openstack/kolla-ansible/stable/2025.1/ansible/roles/multipathd/defaults/main.yml)
- [S3: Kolla-Ansible, выбор и доставка multipath.conf](https://raw.githubusercontent.com/openstack/kolla-ansible/stable/2025.1/ansible/roles/multipathd/tasks/config.yml)
- [S4: Kolla-Ansible, multipathd config.json](https://raw.githubusercontent.com/openstack/kolla-ansible/stable/2025.1/ansible/roles/multipathd/templates/multipathd.json.j2)
- [S5: Kolla, set_configs.py](https://raw.githubusercontent.com/openstack/kolla/stable/2025.1/docker/base/set_configs.py)
- [S6: Kolla-Ansible, Nova cell volumes](https://raw.githubusercontent.com/openstack/kolla-ansible/stable/2025.1/ansible/roles/nova-cell/defaults/main.yml)
- [S7: Kolla-Ansible, Cinder volumes](https://raw.githubusercontent.com/openstack/kolla-ansible/stable/2025.1/ansible/roles/cinder/defaults/main.yml)
- [S8: Ansible template, атомарные обновления](https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/template_module.html)
- [S9: Moby, inode и single-file bind](https://github.com/moby/moby/issues/6011)
- [S10: Linux unlink(2), EBUSY для mountpoint](https://man7.org/linux/man-pages/man2/unlink.2.html)
- [S11: Kolla-Ansible, Podman comparison/lifecycle](https://raw.githubusercontent.com/openstack/kolla-ansible/stable/2025.1/ansible/module_utils/kolla_podman_worker.py)
- [S12: Podman run, volume propagation и labels](https://docs.podman.io/en/latest/markdown/podman-run.1.html)
- [S13: multipath-tools 0.9.4, abstract socket](https://raw.githubusercontent.com/opensvc/multipath-tools/0.9.4/libmpathcmd/mpath_cmd.c)
- [S14: Kolla-Ansible, network_mode в Podman worker](https://raw.githubusercontent.com/openstack/kolla-ansible/stable/2025.1/ansible/module_utils/kolla_podman_worker.py)
- [S15: multipath-tools 0.9.4, socket activation](https://raw.githubusercontent.com/opensvc/multipath-tools/0.9.4/libmpathcmd/mpath_cmd.h)
- [S16: multipath-tools 0.9.4, main.c, local config/delegation](https://raw.githubusercontent.com/opensvc/multipath-tools/0.9.4/multipath/main.c)
- [S17: Kolla-Ansible, штатный multipath.conf](https://raw.githubusercontent.com/openstack/kolla-ansible/stable/2025.1/ansible/roles/multipathd/templates/multipath.conf.j2)
- [S18: Kolla release notes, LP#2078973](https://docs.openstack.org/releasenotes/kolla-ansible/2024.2.html)
- [S19: kpartx udev rules, skip flag](https://raw.githubusercontent.com/opensvc/multipath-tools/0.9.4/kpartx/kpartx.rules)
- [S20: multipath-tools 0.9.4, политика и приоритеты](https://raw.githubusercontent.com/opensvc/multipath-tools/0.9.4/multipath/multipath.conf.5)
- [S21: multipathd 0.9.4, show/reconfigure](https://raw.githubusercontent.com/opensvc/multipath-tools/0.9.4/multipathd/multipathd.8)
- [S22: Cinder, _detach_volume](https://raw.githubusercontent.com/openstack/cinder/stable/2025.1/cinder/volume/driver.py)
- [S23: os-brick Epoxy release notes](https://docs.openstack.org/releasenotes/os-brick/2025.1.html)
- [S24: Linux sense codes](https://raw.githubusercontent.com/torvalds/linux/v6.12/drivers/scsi/sense_codes.h)
- [S25: multipath PATHINFO codes](https://raw.githubusercontent.com/opensvc/multipath-tools/0.9.4/libmultipath/discovery.h)
- [S26: Huawei Cinder FC terminate_connection](https://raw.githubusercontent.com/openstack/cinder/stable/2025.1/cinder/volume/drivers/huawei/huawei_driver.py)
- [S27: Huawei Cinder configuration](https://docs.openstack.org/cinder/2025.1/configuration/block-storage/drivers/huawei-storage-driver.html)
- [S28: Nova Epoxy configuration](https://docs.openstack.org/nova/2025.1/configuration/config.html)
- [S29: Kolla-Ansible, multipathd handler](https://raw.githubusercontent.com/openstack/kolla-ansible/stable/2025.1/ansible/roles/multipathd/handlers/main.yml)
- [S30: Kolla-Ansible, notification of service handlers](https://raw.githubusercontent.com/openstack/kolla-ansible/stable/2025.1/ansible/roles/service-check-containers/tasks/main.yml)

Локальные материалы:

- **L1:** пользовательский архив `os-brick-pvs.zip`. Номера строк в разделе 8 относятся к извлечённым из него файлам, а не к строкам веб-представления upstream.
- **L2:** повторно выполненный `probe_fc_behavior.py`, восемь изолированных проверок выбранных методов; результат `probe-results-rerun.json`. Исходный скрипт находился в предыдущем `os-brick-fc-review.zip`; перед повторным запуском просмотрен. Это не тест полного OpenStack или СХД.
