# Диагностика FC/multipath Kolla: проект и план

Пользователь подтвердил область: FC/multipath, Dorado, подключения томов
Nova/Cinder/Glance. Результат — самостоятельный комплект, запускаемый оператором
с существующим inventory Kolla. Запуск на инфраструктуре в эту задачу не входит.

## Контракт

- Один play, `--limit` работает и для сбора, и для итогового отчёта.
- Собственный Ansible module использует только Python stdlib и базовый API
  Ansible: без зависимостей от коллекции/ролей конкретного форка Kolla.
- Только чтение sysfs, procfs, udev DB, конфигов и ограниченных журналов;
  разрешённые команды состояния. Нет rescan, flush, reload, удаления устройств,
  service start/stop, установки пакетов, запросов к multipathd/libvirt socket.
- Доступ к Docker/Podman API нужен для чтения состояния контейнеров и `exec`
  фиксированных запросов чтения. Проверить socket activation runtime до обращения.
- Временные файлы на хосте — только обычный транспорт Ansible. Артефакты на
  контроллере: JSON каждого хоста, Markdown каждого хоста, summary.json, index.md.
- Не копировать passwords.yml, окружение контейнеров, полные service config/XML.
  Сервисные настройки — только whitelist. Логи маскируются эвристически.
- Неполнота, timeout, missing tool, недоступность и truncation — часть результата.
- Выводы имеют ссылки на evidence и разделяют факт/гипотезу. Ошибка 25/00 сама
  по себе не доказывает unmap; пустые данные не означают исправность.
- Сопоставление с mapping/audit Dorado и API OpenStack остаётся внешним шагом:
  inventory не содержит этих данных и полномочий.

## Интерфейсы

`diagnose.yml` → module `storage_diagnostics(options)` → `report` schema 1.
Report: host, timestamps, options, evidence{id,status,data}, findings,
limitations. Evidence bounded по байтам/времени/количеству.

`tools/render_report.py RUN_DIR` читает manifest.json и records/*.json,
пишет summary.json/index.md и hosts/<sha256(host)>.(json|md). Имена inventory
не используются как пути. В manifest включаются все выбранные узлы.

## Выполнение

1. Тесты: различение ошибок, неизвестное состояние, маскирование,
   whitelist настроек, ограничение subprocess, sysfs связи, недоступный хост.
   Сначала RED (нет реализации), затем GREEN.
2. Реализовать сборщик и анализ, оболочку Ansible module, orchestration/report.
3. Проверить syntax-check, unit suite и end-to-end на локальных fixture-модулях
   плюс недоступный localhost:1. Проверить `--limit`, check-mode, права файлов.
4. Написать README с командами, границами сбора и таблицей интерпретации.
   Отдельно зафиксировать непроверенный live Linux/Kolla/Dorado.

## Решения

- Отдельный каталог в рабочем пространстве, которое не является Git-репозиторием;
  исходники форка не меняются. Дополнительный репозиторий не нужен.
- Применяются planning/TDD практики; запрос пользователя на создание комплекта
  разрешает локальную реализацию. Дополнительная публикация и live-запуск
  не подразумеваются.
- Check mode отклоняется явно: пропущенный сбор нельзя принять за диагностику.

## Проверки

- RED: исходный suite не импортировал отсутствующий сборщик; затем GREEN.
- 20 unit tests: классификация, correlation, privacy, bounded subprocess,
  escaped/truncated secrets, long-token performance, Docker socket ownership.
- Integration: syntax-check; ограничение inventory; первый недоступный хост;
  fixture module; права файлов; check-mode; упаковка реального module и
  сохранение безопасной ошибки некорректного времени.
- Независимый review выявил 5 важных замечаний: формат journal timestamps,
  escaped quotes в secret values, квадратичная обработка длинных tokens,
  слишком слабая проверка Docker socket и неограниченное post-kill wait.
  Все исправлены; регрессионные тесты включены в комплект.
- Исходники форка и production-инфраструктура не изменялись. Live сбор
  Linux/Kolla/Dorado не выполнялся. Детали — `VERIFICATION.md`.
