# OpenStack Epoxy 2025.1 / Huawei Dorado V6: ошибки FC/multipath

## Что за ошибка

На `compute03` внутри контейнера `nova_compute` команда `multipath -ll` сообщает:

```text
/etc/multipath.conf does not exist, blacklisting all devices.
```

**Подтверждено:** утилита не находит конфигурацию и исключает устройства из обработки. Это не доказывает, что сам `multipathd` остановлен.

Ранее наблюдались `Logical unit not supported` и `I/O error`. Первое сообщение соответствует SCSI-коду `25/00`: target не поддерживает запрошенный LUN. Возможное объяснение — отображение LUN уже снято, а Linux продолжает обращаться к оставшимся устройствам. **Связь этих ошибок с отсутствием конфигурации пока не доказана.** [1]

## Предположения по устранению

Обновлено 12.10.2026 по [расширенному исследованию](openstack_dorado_multipath_investigation.md). Подробные изменения и команды — в [рекомендациях по фиксу](KOLLA_MULTIPATH_NOVA_CINDER_FIX.md).

1. **Исправить доставку и обновление конфигурации.** Для сопровождаемого форка предпочтительны существующие каталоги конфигурации Nova/Cinder и запись `/etc/multipath.conf` в их `config.json`. Прямой файловый bind через `*_extra_volumes` требует отдельного обновления mounts при атомарной замене источника; один `reconfigure` не гарантирует обнаружения изменения произвольного extra-volume. Проверить хеши всех потребителей на одном хосте, эффективную политику и единственный управляющий `multipathd`. Не совмещать bind в `/etc/multipath.conf` с копированием Kolla в этот же путь.

2. **Проверить `skip_kpartx` и holders.** Пользовательский конфиг заменяет штатный шаблон целиком и может потерять `skip_kpartx yes`. Автоматические partition-карты могут мешать detach. Установить владельцев зависимых устройств; для SAN-boot и нужных host-разделов политику выбирать отдельно. [6]

3. **Проверить узкий сценарий неполной FC-очистки.** В исследовании описана непередача `force` в `remove_scsi_device`: при требуемом flush и его ошибке путь может остаться. Это не вывод обо всех multipath-detach. Сначала сравнить установленный код и журналы одной операции, затем проверять минимальный патч регрессионными и стендовыми тестами. Успешный `remove_fc_from_host` бывает частью штатного удаления последнего подключения; сам по себе он не доказывает ошибку. Обновление до os-brick 6.11.1 не является подтверждённым решением этого сценария: его исправление orphaned devices относится к iSCSI. [7]

## Проверка результата

Проверить фактический путь тома, включая dm-crypt при наличии, локальную политику `multipath -t` и настройки демона `multipathd show config`. На тестовых томах повторить attach/detach, отключение одного из двух и последнего тома, image-transfer Cinder, повторное применение и изменение конфигурации. Оставшийся рабочий том должен сохранять I/O и данные; после полного отключения без других потребителей не должно оставаться нежелательных устройств. Для Cinder отдельно проверить `use_multipath_for_image_xfer` и `enforce_multipath_for_image_xfer`.

**Итог:** сначала устранить подтверждённую проблему конфигурации контейнера; причину исходных SCSI-ошибок проверять отдельно. Рабочие `sdX` и multipath-карты массово не удалять.

Исходники Kolla/Cinder и инфраструктура при обновлении рекомендаций не менялись. Архив os-brick и его пробы в текущей папке отсутствуют; их результаты взяты из расширенного исследования, повторно здесь не воспроизводились.

## Источники

[1]: https://raw.githubusercontent.com/torvalds/linux/v6.12/drivers/scsi/sense_codes.h
[2]: https://docs.openstack.org/kolla-ansible/2025.1/admin/advanced-configuration.html#mount-additional-docker-volumes-in-containers
[3]: https://docs.openstack.org/kolla-ansible/2025.1/user/operating-kolla.html
[4]: https://raw.githubusercontent.com/openstack/os-brick/6.11.1/os_brick/initiator/connectors/fibre_channel.py
[5]: https://raw.githubusercontent.com/openstack/os-brick/6.11.1/os_brick/initiator/linuxscsi.py
[6]: https://docs.openstack.org/releasenotes/kolla-ansible/2024.2.html
[7]: https://docs.openstack.org/releasenotes/os-brick/2025.1.html

- [SCSI: значения кодов ошибок][1].
- [Kolla: дополнительные монтирования][2] и [применение конфигурации][3].
- [os-brick: FC-disconnect][4] и [удаление SCSI-устройств][5].
- [Kolla: причина добавления skip_kpartx][6].
- [os-brick: состав изменений 6.11.1][7].
