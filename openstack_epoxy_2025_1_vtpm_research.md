# vTPM и миграция ВМ в OpenStack 2025.1 Epoxy

*Краткое техническое исследование · актуализировано 9 октября 2026 г. · Область: Nova 2025.1–2026.2 + libvirt/KVM/QEMU + swtpm + Barbican*

## Краткий вывод

- **В Epoxy (Nova 31.x) виртуальный TPM поддерживается, но live migration ВМ с vTPM штатно запрещена.** Cold migration и resize поддерживаются (с ограничениями по правам доступа к секрету); evacuation, shelving и rescue для vTPM также заблокированы.
- Причина не в отсутствии самого vTPM, а в **жизненном цикле ключа шифрования и состоянии `swtpm`**. На принимающем хосте требуется тот же секрет libvirt, а в Epoxy он создаётся как `private` + `ephemeral` и после запуска домена удаляется из libvirt.
- **Да, в 2026 году это уже реализовано:** поддержка live migration ВМ с vTPM впервые появилась в **Nova 33.0.0 / OpenStack 2026.1 Gazpacho** и сохранена в **Nova 34.0.0 / 2026.2 Hibiscus**. Работает только для режима `hw:tpm_secret_security=host`, не для `user`.
- **Практический путь для Epoxy:** перенести/адаптировать реализацию из Nova **2026.1 Gazpacho**. **В Epoxy этой настройки нет**: одной правкой `nova.conf` или снятием API-блокировки проблему не решить.
- **Версии гипервизора критичны:** в Nova 31–34 общий минимум — **libvirt 8.0.0 / QEMU 6.2.0**, но для безопасного сохранения состояния vTPM при `undefine` желательно **libvirt ≥ 8.9.0**, а для сценария с *общим* хранилищем TPM-state — **libvirt ≥ 8.10.0**. Между хостами должны быть совместимы `swtpm`/`libtpms`; обновление одного лишь libvirt/QEMU не разблокирует vTPM live migration в Epoxy.

## 0. В каких версиях Nova реализована live migration с vTPM

**Короткий ответ: начиная с Nova `33.0.0` (OpenStack `2026.1 Gazpacho`), но только для `host` secret security mode.** В следующем стабильном релизе, `2026.2 Hibiscus` (Nova `34.0.0`), поддержка сохранена. Официальная [документация Nova](https://docs.openstack.org/nova/2026.1/admin/emulated-tpm.html) прямо содержит отметку *Added in version 33.0.0* для live migration с vTPM.

| Релиз OpenStack | Версия Nova в серии | Обычный vTPM | Live migration с vTPM | Подтверждение |
|---|---|---|---|---|
| 2025.1 **Epoxy** | **31.x** (31.0.0–31.3.1 на 09.10.2026) | Да | **Нет** | [релизы](https://releases.openstack.org/epoxy/) · [ограничения Nova 31](https://docs.openstack.org/nova/2025.1/admin/emulated-tpm.html) |
| 2025.2 **Flamingo** | **32.x** (32.0.0–32.2.1) | Да | **Нет** | [релизы](https://releases.openstack.org/flamingo/) · [ограничения Nova 32](https://docs.openstack.org/nova/2025.2/admin/emulated-tpm.html) |
| 2026.1 **Gazpacho** | **33.x** (впервые **33.0.0**, на 09.10.2026 — 33.0.2) | Да | **Да, только `host`** | [релизы](https://releases.openstack.org/gazpacho/) · [release notes](https://docs.openstack.org/releasenotes/nova/2026.1.html) |
| 2026.2 **Hibiscus** | **34.x** (первый релиз **34.0.0**, 30.09.2026) | Да | **Да, только `host`** | [релизы](https://releases.openstack.org/hibiscus/) · [Nova 34 docs](https://docs.openstack.org/nova/2026.2/admin/emulated-tpm.html) |

Для контекста: **базовый vTPM появился намного раньше, в Nova 22.0.0 (Victoria)**; новшество версии 33.0.0 — именно *live migration с vTPM*, а не само устройство.

### Отличайте версию пакета Nova от версии `nova-compute` service

В Nova 33 код [`nova/compute/api.py`](https://github.com/openstack/nova/blob/stable/2026.1/nova/compute/api.py) задаёт `MIN_COMPUTE_VTPM_LIVE_MIGRATION = 72`. Проверка выполняется по **минимальной версии всех `nova-compute` в cell**, где расположена ВМ. Пока хоть один compute в этой cell имеет меньшую версию, API не разрешит live migration ВМ с vTPM даже в режиме `host`. Это не номер Python-пакета, а отдельная внутренняя версия сервиса.

| Релиз | Nova package major | Типичная service version `nova-compute` |
|---|---:|---:|
| Epoxy | 31 | 68 |
| Flamingo | 32 | 70 |
| Gazpacho | 33 | **72** (минимум для vTPM live migration) |
| Hibiscus | 34 | не ниже 72 для соответствующего функционала |

Источники значений: [`nova/objects/service.py` для 2026.1](https://github.com/openstack/nova/blob/stable/2026.1/nova/objects/service.py) (алиасы релизов 68/70/72), [`nova/compute/api.py` для 2026.1](https://github.com/openstack/nova/blob/stable/2026.1/nova/compute/api.py) (API guard). Для **rolling upgrade 2025.1 → 2026.1** схема SLURP официально предусмотрена, но **vTPM live migration не становится доступна посередине обновления**; сначала необходимо обновить все compute нужной cell. [Nova 2026.1 release notes](https://docs.openstack.org/releasenotes/nova/2026.1.html).

### Что реально появилось в Nova 33

- Новое свойство flavor `hw:tpm_secret_security=host` и `[libvirt] supported_tpm_secret_security` на compute-хостах.
- Libvirt secret становится **persistent + retrievable** в режиме `host`: source получает тот же UUID и значение ключа, передаёт его на destination посредством RPC, destination определяет secret до старта принимающего vTPM.
- [`LibvirtLiveMigrateData`](https://github.com/openstack/nova/blob/stable/2026.1/nova/objects/migrate_data.py) обновлён с **1.13 до 1.14**: поля `vtpm_secret_uuid`, `vtpm_secret_value` (`SensitiveStringField`) и запрет отката сериализации на старую версию при наличии vTPM-данных.
- Улучшен запуск ВМ после перезагрузки compute-хоста в режиме `host`: доступ к локальному libvirt-secret не требует токена владельца в Barbican.
- **Без новой Compute API microversion**: поддержка выбирается flavor, возможностями хостов и проверкой версии compute-сервисов.

### Минимальный пример настройки 2026.1/2026.2 (НЕ для чистого Epoxy)

На **каждом** compute-хосте, который должен принимать такие ВМ, в `nova.conf`:

```ini
[libvirt]
swtpm_enabled = true
supported_tpm_secret_security = user,host
```

Для новых ВМ в подходящем flavor:

```bash
openstack flavor set <FLAVOR> \
  --property hw:tpm_version=2.0 \
  --property hw:tpm_model=tpm-crb \
  --property hw:tpm_secret_security=host
```

Для **существующей** vTPM-ВМ, ранее созданной в `user`-режиме, требуется **resize** в flavor с `host` и `resize confirm` (планировать окно обслуживания):

```bash
openstack server resize --flavor <FLAVOR_WITH_HOST_MODE> <SERVER>
openstack server resize confirm <SERVER>
```

Как правило, resize выполняет **владелец ВМ**, поскольку именно его учётной записи принадлежит секрет в Barbican; другой пользователь/администратор сможет выполнить resize только при соответствующих ACL key manager. Простое изменение extra specs flavor задним числом **не конвертирует** секрет уже созданной ВМ. [Официальная инструкция](https://docs.openstack.org/nova/2026.2/admin/emulated-tpm.html#legacy-servers-and-live-migration).

Проверить capability traits (хосты должны сообщать `COMPUTE_SECURITY_TPM_SECRET_SECURITY_HOST`):

```bash
COMPUTE_UUID=$(openstack resource provider list --name <COMPUTE_HOST> -f value -c uuid)
openstack resource provider trait list "$COMPUTE_UUID" | grep SECURITY_TPM
```

Обязательны совместимые `swtpm`/`libtpms`, key manager (обычно Barbican), драйвер libvirt `kvm`/`qemu`, корректно работающая штатная live migration и защита RPC/миграционного трафика. В Nova 33 и 34 общий минимум драйвера — **libvirt 8.0.0 и QEMU 6.2.0**; спецификация vTPM live migration требует libvirt не ниже 7.1.0, то есть более строгий общий минимум Nova уже перекрывает этот порог. **Но для `VIR_DOMAIN_UNDEFINE_KEEP_TPM` нужна libvirt ≥ 8.9.0:** на более старых версиях временный `undefine` может удалить vTPM-state, о чём Nova явно предупреждает. Это не гарантия совместимости дистрибутивных сборок: проверить версии, настройки и миграцию с реальным `swtpm` на обоих узлах. См. [Nova 33 driver](https://github.com/openstack/nova/blob/stable/2026.1/nova/virt/libvirt/driver.py), [Nova 34 driver](https://github.com/openstack/nova/blob/stable/2026.2/nova/virt/libvirt/driver.py) и [vTPM live migration spec](https://specs.openstack.org/openstack/nova-specs/specs/2026.1/implemented/vtpm-live-migration.html).

**Остающиеся ограничения даже в Nova 34:** режим `user` не поддерживает live migration; `rebuild`, `evacuate`, `shelve`, `rescue` для vTPM по-прежнему ограничены. Код Nova 33 содержит внутренние упоминания третьего режима `deployment` (в том числе в конфигурационной опции), однако **API live migration пропускает только `host`**; не стоит считать `deployment` поддерживаемым путём для live migration. [Nova 34 ограничения](https://docs.openstack.org/nova/2026.2/admin/emulated-tpm.html#limitations) · [Nova 33 API guard](https://github.com/openstack/nova/blob/stable/2026.1/nova/compute/api.py).

## 1. Что такое vTPM и как он работает

**vTPM (virtual Trusted Platform Module)** — программная реализация устройства TPM, доступная ОС гостевой ВМ как обычный TPM 1.2 или TPM 2.0. TPM предназначен для защищённого хранения/использования ключей, ведения PCR-регистров с измерениями загрузки и выполнения криптографических операций. Применения: Windows 11, BitLocker, измеренная загрузка, запечатывание (sealing) секретов к состоянию платформы.

Для драйвера Nova `libvirt` с `virt_type=kvm` или `qemu` цепочка выглядит так:

```text
Гостевая ОС ── TPM-драйвер (/dev/tpm0 / Windows TPM) ── QEMU (tpm-tis / tpm-crb)
                                                          │ Unix socket
                                                          ▼
                                                      swtpm + libtpms
                                                          │
                                     зашифрованное состояние TPM на compute-хосте
                                     /var/lib/libvirt/swtpm/<UUID_ВМ>/
                                                          ▲
                                                          │ ключ шифрования
 Nova ── Castellan ── Barbican / другой key manager ── libvirt secret (UUID)
```

- Для **каждой ВМ** libvirt запускает отдельный экземпляр `swtpm`; гостю предоставляется модель `tpm-tis` либо `tpm-crb` (последняя — только TPM 2.0).
- Состояние TPM (включая постоянные TPM-данные) хранится **отдельно от диска ВМ**. Шифрование *файлов состояния vTPM* не равнозначно шифрованию системного диска гостя: BitLocker, например, использует TPM как часть механизма защиты своего ключа.
- Nova через `crypto.ensure_vtpm_secret()` получает/создаёт секрет в key manager и сохраняет **UUID секрета**, но не его значение, в `instance.system_metadata['vtpm_secret_uuid']`. При создании домена secret передаётся в libvirt; `<tpm><backend type='emulator' ...><encryption secret='...'/></backend></tpm>` связывает vTPM с этим секретом.

Для базового vTPM нужны `swtpm`/`libtpms`, доступный key manager (обычно Barbican) и `[libvirt] swtpm_enabled = true` на compute-узлах. Запрос со стороны ВМ задаётся image properties `hw_tpm_version`/`hw_tpm_model` или flavor extra specs `hw:tpm_version`/`hw:tpm_model`.

## 2. Как vTPM влияет на миграцию между хостами

При **live migration** нужно согласованно перенести:

1. Состояние работающей ВМ (QEMU RAM/CPU, устройства), диски — согласно схеме обычной миграции; отдельно учитывается UEFI NVRAM, если используется.
2. **Состояние `swtpm`** (в том числе его runtime- и persistent-части). Не следует копировать каталог `swtpm` простым `rsync` во время работы гостя: требуется согласованная передача через поддерживаемый механизм QEMU/libvirt/swtpm.
3. **Тот же UUID и значение секрета** на целевом хосте **до** запуска принимающего TPM-эмулятора, чтобы состояние можно было расшифровать.

Обычные shared storage для дисков/`instances_path` **не делают каталог vTPM общим**: типичный путь `/var/lib/libvirt/swtpm/<UUID_ВМ>`. Для целевого сценария следует отдельно тестировать **локальное, неразделяемое хранилище vTPM**; общий каталог TPM-state — отдельная конфигурация, не покрытая стандартным сценарием Nova Epoxy.

**Почему не работает в Epoxy:** секрет в Barbican принадлежит владельцу ВМ и читается в контексте его токена. Администратор, запускающий live migration, обычно не может получить этот секрет. На исходном хосте libvirt-secret создан как `private` + `ephemeral` и удаляется после старта домена — получить значение через libvirt тоже нельзя. Следовательно, одного переноса RAM/дисков недостаточно. По сходной причине автоматический restart ВМ с vTPM после перезагрузки compute-хоста может упереться в отсутствие токена владельца.

**Что уже есть:** для *cold migration/resize* в Epoxy реализованы `save_and_migrate_vtpm_dir()` и `restore_vtpm_dir()` в `nova/virt/libvirt/utils.py`, с переносом файлов и восстановлением прав. Это **не готовая реализация live migration**.

## 2.1. Влияют ли версии libvirt, QEMU, swtpm и libtpms на миграцию?

**Да. Нужно различать два независимых условия:** (а) Nova *разрешает* live migration ВМ с vTPM на уровне API и правильно передаёт секрет, (б) стек **libvirt/QEMU/swtpm/libtpms** умеет согласованно переносить и восстанавливать состояние TPM. Выполнение только одного условия недостаточно.

### Версии и пороги

| OpenStack / Nova | Минимум **libvirt** для Nova | Минимум **QEMU** для Nova | Live migration vTPM из коробки |
|---|---:|---:|---|
| 2025.1 Epoxy / **Nova 31.x** | **8.0.0** | **6.2.0** | **Нет**, блокировка Nova |
| 2025.2 Flamingo / **Nova 32.x** | **8.0.0** | **6.2.0** | **Нет**, блокировка Nova |
| 2026.1 Gazpacho / **Nova 33.x** | **8.0.0** | **6.2.0** | **Да**, `hw:tpm_secret_security=host` |
| 2026.2 Hibiscus / **Nova 34.x** | **8.0.0** | **6.2.0** | **Да**, `hw:tpm_secret_security=host` |

Пороги приведены по [матрице Nova 2026.1](https://docs.openstack.org/nova/2026.1/reference/libvirt-distro-support-matrix.html), а для Nova 34 — **не по устаревшей таблице**, а непосредственно по [`stable/2026.2/nova/virt/libvirt/driver.py`](https://github.com/openstack/nova/blob/stable/2026.2/nova/virt/libvirt/driver.py), где заданы `MIN_LIBVIRT_VERSION = (8, 0, 0)` и `MIN_QEMU_VERSION = (6, 2, 0)`. Значения `NEXT_MIN_LIBVIRT_VERSION = (10, 0, 0)` и `NEXT_MIN_QEMU_VERSION = (8, 2, 2)` — **предупреждение о планируемом повышении порога**, а не обязательное требование к этим релизам.

Важные **дополнительные пороги** (их нельзя смешивать с общим минимумом Nova):

- **libvirt ≥ 7.1.0** — порог для миграции vTPM с *неразделяемым* TPM-state, указанный в [спецификации Nova](https://specs.openstack.org/openstack/nova-specs/specs/2026.1/implemented/vtpm-live-migration.html#libvirt-support) со ссылкой на исправление libvirt. Поскольку сама Epoxy уже требует libvirt 8.0.0, отдельного повышения ради этого механизма не нужно.
- **libvirt ≥ 8.9.0 — практически важный порог сохранности TPM-state.** Появился флаг `VIR_DOMAIN_UNDEFINE_KEEP_TPM` (`virsh undefine --keep-tpm`). В Nova 31/33/34 код проверки `MIN_VERSION_INT_FOR_KEEP_TPM = (8, 9, 0)` предупреждает, что на libvirt **8.0–8.8** временное снятие определения домена может **удалить содержимое vTPM**. Поэтому для рабочего кластера с vTPM разумно использовать **8.9+** и отдельно проверить операции cleanup/rollback; это **рекомендация, а не формальный минимум запуска Nova**. [libvirt 8.9 release notes](https://libvirt.org/news.html#v8-9-0-2022-11-01) · [Nova driver](https://github.com/openstack/nova/blob/stable/2026.1/nova/virt/libvirt/driver.py).
- **libvirt ≥ 8.10.0** — в [libvirt 8.10 release notes](https://libvirt.org/news.html#v8-10-0-2022-12-01) явно отмечена миграция состояния vTPM на *общем* хранилище. **Это не обязательный порог для штатного сценария Nova с локальным TPM-state** (`/var/lib/libvirt/swtpm/<UUID>`), который рассматривает upstream-спецификация. Миграция с shared TPM-state не является покрытым CI сценарием Nova и требует отдельных испытаний.
- **QEMU ≥ 6.2.0** — общий минимум Epoxy/Gazpacho/Hibiscus. У QEMU есть поддержка сетевой миграции с TPM-эмулятором, но **одного выполнения версии 6.2.0 недостаточно для гарантии успеха**. Для иной функции — одновременного `multifd + post-copy` — в Nova 2026.1 требуется **QEMU ≥ 10.1.0**; это **не отдельное требование vTPM**. [QEMU TPM docs](https://www.qemu.org/docs/master/specs/tpm.html#migration-with-the-tpm-emulator) · [Nova 2026.1 release notes](https://docs.openstack.org/releasenotes/nova/2026.1.html).
- **swtpm и libtpms** — официальная спецификация Nova **не задаёт единого отдельного числового минимума именно для live migration**. На source и destination необходимы совместимые форматы состояния, TPM 1.2/2.0 и криптографические возможности. Практически предпочтительно иметь **одинаковые версии и сборки** `swtpm`/`libtpms` на обоих узлах. **Downgrade `libtpms` не гарантируется**, а различные compile-time options libtpms или TPM-профили/FIPS-политики могут сделать состояние непригодным на destination. См. [QEMU: Troubleshooting migration](https://www.qemu.org/docs/master/specs/tpm.html#troubleshooting-migration) и [объяснение разработчика swtpm](https://github.com/stefanberger/swtpm/issues/525). Не путать обычный `libvirt secret`, шифрующий файлы состояния vTPM, с опциональным ключом протокола миграции самого `swtpm`.

Для настройки **нестандартного пути** состояния через `<tpm><backend><source ...>` требуются **libvirt ≥ 10.10.0** и **swtpm ≥ 0.7**, согласно [формату XML libvirt](https://libvirt.org/formatdomain.html#tpm-device). **Это не требование стандартной live migration Nova:** её штатный сценарий не задаёт `<source>` и использует путь, выбранный libvirt.

### Что проверять на обоих compute-хостах

Команды выполняются **в окружении фактического libvirt/QEMU compute-хоста** (если сервисы контейнеризированы — в соответствующем namespace/контейнере или с доступом к его libvirt-сокету):

```bash
# Версия подключённого libvirt и гипервизора (не только версия virsh-клиента)
virsh version

# Версия QEMU: имя исполняемого файла зависит от архитектуры хоста
qemu-system-x86_64 --version | head -n 1

# Версия эмулятора TPM и инструментов инициализации
swtpm --version
swtpm_setup --version

# Доступные TPM-модели по данным libvirt
virsh domcapabilities | sed -n '/<tpm /,/<\/tpm>/p'

# Дополнительно: точные версии пакетов на Ubuntu/Debian
dpkg-query -W 'libtpms*' 'swtpm*' 2>/dev/null

# Или на RHEL/CentOS (названия пакетов зависят от дистрибутива)
rpm -qa | grep -E '^(libtpms|swtpm)'
```

По результатам сравнить версии и сборки **A/B**, доступность `tpm-tis` или `tpm-crb`, TPM 2.0, состояние `swtpm` и права на его каталог, возможности шифрования и сетевой миграции. Пакетная версия в дистрибутиве с backport-патчами может отличаться по возможностям от исходного upstream; **финальное подтверждение — реальный тест A → B → A**, включая `rollback` и проверку TPM sealed keys/BitLocker. Не считать вывод `virsh version` самостоятельным доказательством готовности к vTPM migration.

**Решение для Epoxy:** сначала определить текущие версии. На **libvirt 8.0–8.8** отдельно рассмотреть обновление как меру против риска утраты TPM-state при `undefine`; на **libvirt 8.9+ / QEMU 6.2+** готовность нижнего уровня всё равно требует испытаний `swtpm`/`libtpms`. **И в любом случае** для live migration с vTPM в Nova 31 потребуется backport логики `host` из Nova 33 — установка более нового QEMU/libvirt не заменяет эти изменения.

## 3. Что и где дорабатывать в Epoxy

Для минимального, проверенного upstream-варианта разумно реализовать только **режим `host`** (а существующий `user` оставить по умолчанию). Таблица показывает точки работы в исходниках ветки `stable/2025.1`, а не готовые параметры этого релиза.

| Компонент / файл Nova | Требуемое изменение |
|---|---|
| **API:** [`nova/compute/api.py`](https://github.com/openstack/nova/blob/stable/2025.1/nova/compute/api.py) | Заменить безусловный запрет через `reject_vtpm_instances(...)` для live migration на проверку режима секрета и минимальной версии всех затронутых `nova-compute`; для `user` запрет сохранить. |
| **Параметры и placement:** `nova/conf/libvirt.py`, `nova/virt/hardware.py`, `nova/scheduler/utils.py`, проверка flavor extra specs | Добавить `hw:tpm_secret_security={user,host}` и настройку поддерживаемых режимов compute-хоста; транслировать требуемый режим в Placement trait, чтобы не мигрировать на неподдерживающий хост. |
| **Создание и жизненный цикл секретов:** [`nova/crypto.py`](https://github.com/openstack/nova/blob/stable/2025.1/nova/crypto.py), [`nova/virt/libvirt/driver.py`](https://github.com/openstack/nova/blob/stable/2025.1/nova/virt/libvirt/driver.py), при необходимости `nova/virt/libvirt/host.py` | Для `user` оставить `private=yes, ephemeral=yes`; для `host` формировать **читаемый через libvirt API, сохраняемый на диске libvirt-secret** (`private=no, ephemeral=no`), корректно привязывать его к домену и управлять очисткой. Учесть повторный старт, destroy, resize, откат и удаление. |
| **RPC/объект миграции:** [`nova/objects/migrate_data.py`](https://github.com/openstack/nova/blob/stable/2025.1/nova/objects/migrate_data.py) | Расширить `LibvirtLiveMigrateData` (в Epoxy версия **1.13**) полями `vtpm_secret_uuid`, `vtpm_secret_value`; перенести схему **1.14** из Nova 33 (включая `SensitiveStringField`, сериализацию байтов и запрет несовместимого backport). |
| **Путь live migration:** `nova/virt/libvirt/driver.py`, `nova/compute/manager.py`, при необходимости `nova/virt/libvirt/migration.py` | На source получить libvirt-secret и передать его через защищённый RPC; на destination определить **тот же secret UUID/value до миграции**. В `pre_live_migration`, success/rollback/cleanup обеспечить корректный порядок, идемпотентность и отсутствие утечек. Перенос самого состояния `swtpm` делегировать совместимым libvirt/QEMU. |
| **Совместимость и проверки:** `nova/objects/service.py`, тесты Nova/Tempest, документация | Добавить собственный bump сервисной версии `nova-compute` и guard по минимальной версии compute-сервисов в cell (ориентир upstream — **service version 72**, нельзя просто записать 72 без согласования локальной истории версий). Проверить стек libvirt/QEMU/swtpm на обоих узлах. Добавить unit/functional и интеграционные тесты с `swtpm`. |
| **Гипервизор и пакеты:** дистрибутивные сборки `libvirt`, `qemu`, `swtpm`, `libtpms`; `nova/virt/libvirt/driver.py` | Сверить минимумы Nova (8.0/6.2), поддержку сохранения TPM-state при `undefine` (libvirt 8.9+), совместимость состояний `swtpm`/`libtpms` между хостами и права на TPM-state. Внести при backport проверку/предупреждение для неподходящих версий и интеграционные тесты с разными сочетаниями библиотек. **Патчить libvirt/QEMU обычно не нужно**, если требуемые возможности присутствуют в их сборках. |

**Важное различие спецификаций:** одобренный *проект* для Epoxy (2025.1) описывал режимы `user`/`host`/`deployment` и названия наподобие `hw:vtpm_secret_security`. В **официально документированном сценарии live migration Nova 2026.1/2026.2** используется `hw:tpm_secret_security=host`; `user` блокируется. В исходниках Nova 33 есть упоминания режима `deployment` (включая `nova/vtpm.py` и config option), но **декоратор API live migration разрешает только `host`**, поэтому `deployment` нельзя считать рабочим upstream-способом live migration. Для backport ориентироваться на **фактический код и документацию 2026.1**, а не дословно на ранний spec.

## 4. Предлагаемый целевой сценарий

```text
[VM с vTPM, режим host] на A
      │ 1) Nova проверяет пригодность B и версии сервисов
      │ 2) A читает persistent libvirt-secret
      │ 3) RPC переносит UUID + секрет (защищённый канал)
      ▼
  B: pre_live_migration ──> определить libvirt-secret
      │ 4) libvirt/QEMU/swtpm мигрируют согласованное состояние
      ▼
  B: запуск/продолжение ВМ и vTPM
      │ 5) успех: очистка временных ресурсов на A
      └─ ошибка: rollback, сохранение работоспособности ВМ на A,
                  удаление только временных ресурсов/секретов на B
```

В **2026.1**, но **не в чистом Epoxy**, создание flavor для этого сценария выглядит так:

```bash
openstack flavor set <FLAVOR> \
  --property hw:tpm_version=2.0 \
  --property hw:tpm_model=tpm-crb \
  --property hw:tpm_secret_security=host
```

Существующую ВМ с режимом `user` нельзя просто пометить как `host` изменением свойства flavor: нужно конвертировать политику секретов. В upstream 2026.1 это делается **resize** в flavor с `host`, обычно от имени владельца ВМ (из-за прав доступа к Barbican).

**Компромисс безопасности:** режим `host` открывает пользователю с достаточными привилегиями на compute-хосте доступ к ключу vTPM через libvirt и сохраняет этот ключ на хосте. Необходимы защита хостов/backup, TLS для Nova RPC/MQ и отдельно для migration stream, запрет логирования значения секрета, строгие ACL и очистка ресурсов. Режим `user` лучше изолирует секрет на уровне интерфейсов управления, но блокирует live migration.

## 5. Минимальные критерии приёмки

- Успешная **A → B → A** live migration с TPM 2.0, Linux `tpm2-tools` и/или Windows + BitLocker; UUID/состояние TPM и доступность sealed-секретов сохраняются, BitLocker не требует recovery из-за миграции.
- Проверки **shared disks / volume-backed и block migration**, но TPM-state на **локальном** диске; отдельный прогон UEFI/Secure Boot при использовании.
- Контролируемые ошибки: недоступен секрет, несовпадение secret UUID/value, отказ destination, таймаут/rollback; VM на source остаётся работоспособной, целевой хост не содержит осиротевших секретов или частично созданных TPM-state.
- Миграция `user` запрещена; несовместимый/старый `nova-compute` или неподдерживающий TPM destination отфильтрованы; создание, resize, stop/start, hard reboot, удаление и cleanup протестированы.
- На двух compute-хостах зафиксированы версии libvirt/QEMU/swtpm/libtpms, сделан тест с **одинаковыми сборками** и негативный тест с заведомо несовместимыми `libtpms`/профилями; отдельно проверены сохранение TPM-state при `undefine`/rollback для libvirt **8.9+** и поведение на версиях ниже 8.9 (только в изолированном тестовом окружении).
- В логах и уведомлениях нет **значения** секрета; трафик управления и миграции защищён.

## Итог

Для **обычного vTPM** в Epoxy хватает настройки compute-хостов + Barbican. Для **live migration vTPM** нужна доработка **Nova по нескольким слоям**: API/проверки политик, сериализация RPC, libvirt-secret lifecycle, подготовка destination, откат и тесты. Дополнительно важен **стек гипервизора**: формальный минимум libvirt **8.0.0** / QEMU **6.2.0** не гарантирует сохранность TPM-state при `undefine` (для этого желательно **libvirt ≥ 8.9.0**) и не устраняет несовместимости `swtpm`/`libtpms` между хостами. Изменять сам `swtpm` или Barbican обычно не требуется, **если** используемые версии и политика доступа поддерживают целевой сценарий. Наиболее низкорисковый подход — адаптация уже реализованной схемы **Nova 2026.1 (`host`)** с тестированием на конкретных пакетах Epoxy.

## Основные источники

1. [Nova 2025.1: Emulated TPM — включение и ограничения](https://docs.openstack.org/nova/2025.1/admin/emulated-tpm.html)
2. [Nova 2025.1: список реализованных и только одобренных спецификаций](https://specs.openstack.org/openstack/nova-specs/specs/2025.1/index.html)
3. [Nova 2025.1: vTPM live migration — approved spec, не реализация](https://specs.openstack.org/openstack/nova-specs/specs/2025.1/approved/vtpm-live-migration.html)
4. [Nova 2026.1: реализованный vTPM live migration spec](https://specs.openstack.org/openstack/nova-specs/specs/2026.1/implemented/vtpm-live-migration.html)
5. [Nova 2026.1: документация `user`/`host` и конвертации старых ВМ](https://docs.openstack.org/nova/2026.1/admin/emulated-tpm.html)
6. [Nova 2026.1: Release Notes — live migration с vTPM](https://docs.openstack.org/releasenotes/nova/2026.1.html)
7. [QEMU: TPM device and migration](https://www.qemu.org/docs/master/specs/tpm) · [libvirt: TPM domain XML](https://libvirt.org/formatdomain.html) · [libvirt: secret XML](https://libvirt.org/formatsecret.html)
8. Исходный код Nova Epoxy: [`crypto.py`](https://github.com/openstack/nova/blob/stable/2025.1/nova/crypto.py), [`migrate_data.py`](https://github.com/openstack/nova/blob/stable/2025.1/nova/objects/migrate_data.py), [`libvirt/utils.py`](https://github.com/openstack/nova/blob/stable/2025.1/nova/virt/libvirt/utils.py), [`compute/api.py`](https://github.com/openstack/nova/blob/stable/2025.1/nova/compute/api.py).
9. [Матрица минимальных версий Nova libvirt/QEMU (2026.1)](https://docs.openstack.org/nova/2026.1/reference/libvirt-distro-support-matrix.html) и [константы Nova 34 (2026.2) в `driver.py`](https://github.com/openstack/nova/blob/stable/2026.2/nova/virt/libvirt/driver.py).
10. [libvirt releases: 8.9 — флаг сохранения TPM, 8.10 — миграция TPM-state на shared storage](https://libvirt.org/news.html).
11. [QEMU: TPM emulator migration & compatibility pitfalls](https://www.qemu.org/docs/master/specs/tpm.html) и [libvirt: TPM domain XML](https://libvirt.org/formatdomain.html#tpm-device).

### Дополнительные первичные источники по версиям Nova

- [OpenStack releases: Epoxy — Nova 31](https://releases.openstack.org/epoxy/)
- [OpenStack releases: Flamingo — Nova 32](https://releases.openstack.org/flamingo/)
- [OpenStack releases: Gazpacho — Nova 33](https://releases.openstack.org/gazpacho/)
- [OpenStack releases: Hibiscus — Nova 34](https://releases.openstack.org/hibiscus/)
- [Nova 2026.2: vTPM administration / limitations](https://docs.openstack.org/nova/2026.2/admin/emulated-tpm.html)
- [Nova 33: API guard / service version 72](https://github.com/openstack/nova/blob/stable/2026.1/nova/compute/api.py)
- [Nova 33: `LibvirtLiveMigrateData` 1.14 / sensitive secret](https://github.com/openstack/nova/blob/stable/2026.1/nova/objects/migrate_data.py)
- [Nova 33: supported TPM mode option](https://github.com/openstack/nova/blob/stable/2026.1/nova/conf/libvirt.py)
