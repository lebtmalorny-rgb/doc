# Watcher → Prometheus: какие настройки и файлы исправить

Дата: 21.09.2026. Основание: архивы `kolla-ansible-pvs_1.0.0_21.09zip.zip` и `watcher-pvs_1.0.0_21.09.zip`.

## Краткий вывод

В конфигурации из архива подтверждено несовпадение меток: Watcher ищет compute-узлы по `fqdn`, а PVS-шаблон Prometheus создаёт `instance_hostname`. PVS-шаблон имеет приоритет над базовым шаблоном, в котором поддержка `fqdn` уже есть. При такой комбинации Watcher не находит узел и не может построить запрос CPU/RAM, даже если Prometheus успешно собирает исходные метрики.

Дополнительно нужно согласовать адрес Prometheus для Watcher Engine/Applier и убрать ограничение `user_name="admin"` из двух recording rules, если Watcher должен получать метрики ВМ всех пользователей. Для HTTPS отдельно требуется проверить CA: параметр `scheme`, который записывает роль Kolla, исходником Watcher из архива не используется.

**Статус:** подготовлены рекомендации; исходники ролей, конфигурация стенда и сервисы при подготовке документа не изменялись. Ошибка сопоставления labels воспроизведена локально на методах datasource с подставным ответом API. Состояние работающего облака не проверялось.

Пути ниже заданы относительно корня соответствующего распакованного архива. Исходники в репозиторий документации не включены. Общая схема мониторинга описана в [руководстве Prometheus и Grafana](PROMETHEUS_GRAFANA_ADMIN_GUIDE.md).

## 1. Карта необходимых правок

| Что | Где | Изменение | Когда требуется |
|---|---|---|---|
| Идентификация compute-узлов | Kolla: `ansible/alerts/prometheus/templates/prometheus.yml.j2`, job `node`, строки 51–73 | Добавить target label `fqdn`, согласованный с именем compute-сервиса Nova | Основная правка при использовании PVS-шаблона |
| Временная настройка без изменения Prometheus | Globals стенда: `watcher_prometheus_client_fqdn_label` | Использовать `instance_hostname` | Альтернатива предыдущей строке, только при совпадении имён с Nova |
| Адрес datasource | Globals стенда; для исправления defaults — `ansible/roles/watcher/defaults/main.yml:218–224` | Явно указать доступный endpoint Prometheus; согласовать Engine и Applier | Если текущий адрес выбран из неподходящей группы/сети |
| CPU/RAM ВМ всех пользователей | Kolla: `ansible/roles/prometheus/templates/watcher.rules.j2:28,36` | Убрать `user_name="admin"` в обеих выборках metadata | Если мониторинг должен охватывать все ВМ |
| TLS клиента | Globals и при необходимости `ansible/roles/watcher/templates/watcher.conf.j2:22–38` | Задать CA для HTTPS; при требовании mTLS доставить и настроить клиентские cert/key | Только для TLS endpoint |

Сначала устанавливают фактические значения конфигурации. Не требуется одновременно переключать Watcher на `instance_hostname` и добавлять `fqdn`: это два варианта согласования одного контракта.

## 2. Какие FQDN и адреса используются

| Назначение | Значение по умолчанию | Источник Kolla |
|---|---|---|
| Внутренний FQDN Watcher API | `watcher_internal_fqdn = kolla_internal_fqdn` | `ansible/group_vars/all.yml:819` |
| Внешний FQDN Watcher API | `watcher_external_fqdn = kolla_external_fqdn` | `ansible/group_vars/all.yml:820` |
| Внутренний порт Watcher API | `9322` | `ansible/group_vars/all.yml:823` |
| Внутренний FQDN Prometheus | `prometheus_internal_fqdn = kolla_internal_fqdn` | `ansible/group_vars/all.yml:727` |
| Внешний FQDN Prometheus | `prometheus_external_fqdn = kolla_external_fqdn` | `ansible/group_vars/all.yml:728` |
| Внутренний порт Prometheus | `9091` | `ansible/group_vars/all.yml:731` |
| Watcher Engine → Prometheus | Первый после сортировки `ansible_host` из группы `control`; выражение содержит fallback на VIP | `ansible/roles/watcher/defaults/main.yml:218` |
| Watcher Applier → Prometheus | `kolla_internal_vip_address:9091` | `ansible/roles/watcher/defaults/main.yml:222–223` |

В defaults `kolla_internal_fqdn` наследует `kolla_internal_vip_address`; название переменной не гарантирует, что её значение — доменное имя. Конкретные FQDN/IP стенда определяются его inventory, globals и overrides. Внешний frontend Prometheus по умолчанию выключен (`enable_prometheus_server_external: false`). Публичные порты также зависят от настройки единого внешнего frontend.

Для получения метрик Decision Engine использует `[prometheus_client]` в `watcher.conf`. Изменение FQDN Watcher API само по себе не меняет адрес этого клиента. Кроме того, default клиента использует `ansible_host`, а Prometheus слушает `api_interface_address`: SSH-адрес контроллера может принадлежать другой сети. В типовом `ansible/inventory/multinode:68–69` группа `prometheus` наследует `monitoring`, а не `control`.

Метка `fqdn` в Prometheus — отдельное понятие. Её значение служит идентификатором compute-узла, а не адресом сервиса Prometheus. В данной версии Watcher берёт имя узла из Nova `node.service["host"]` (`watcher/decision_engine/model/collector/nova.py:405–409`). Это нужно учитывать при сравнении с inventory, `ansible_hostname` и `hypervisor_hostname`.

## 3. Основная правка: согласовать hostname label

### Почему теряется существующая поддержка `fqdn`

Цепочка выбора конфигурации в Kolla:

1. `ansible/roles/prometheus/tasks/deploy.yml:2–5` запускает `pvs_alerts.yml` перед `config.yml`.
2. `tasks/pvs_alerts.yml:78–87` рендерит `ansible/alerts/prometheus/templates/prometheus.yml.j2` в `{{ node_custom_config }}/prometheus/prometheus.yml`.
3. `tasks/config.yml:93–108` выбирает этот файл раньше `ansible/roles/prometheus/templates/prometheus.yml.j2`. Host-specific override имеет ещё более высокий приоритет.
4. В базовом шаблоне на строках 63–66 есть `fqdn`, в PVS job `node` на строках 61–71 её нет.

Поэтому исправление только базового `ansible/roles/prometheus/templates/prometheus.yml.j2` не исправит конфигурацию, сформированную из PVS-шаблона. Ручная правка сгенерированного файла может быть перезаписана при следующем deploy/reconfigure.

### Вариант A: исправить PVS-шаблон

В `ansible/alerts/prometheus/templates/prometheus.yml.j2`, внутри `static_configs` job `node`, после `instance_hostname` добавить:

```jinja2
          instance_hostname: "{{ hostvars[host]['ansible_hostname'] }}"
{% if enable_watcher | bool %}
          fqdn: "{{ hostvars[host].ansible_hostname | default(host) }}"
{% endif %}
          region: "{{ openstack_region_name }}"
```

Существующие `instance_hostname`, `instance`, `region`, `sm_ci` сохранить. Настройку Watcher оставить прежней:

```yaml
watcher_prometheus_client_fqdn_label: "fqdn"
```

Такой фрагмент повторяет действующее соглашение базового шаблона: `fqdn` содержит короткий `ansible_hostname`. Он подходит, если Nova также использует это короткое имя.

Если Nova использует полное имя, например `compute01.example.org`, а `ansible_hostname` равен `compute01`, одной добавленной метки недостаточно. Для такого стенда можно ввести **новую необязательную inventory-переменную** `watcher_metric_hostname` и использовать вместо предыдущей строки:

```jinja2
          fqdn: "{{ hostvars[host].watcher_metric_hostname | default(hostvars[host].ansible_hostname | default(host)) }}"
```

Пример `host_vars/compute01.yml` для этого варианта:

```yaml
watcher_metric_hostname: "compute01.example.org"
```

Это предлагаемый параметр новой правки, в текущем архиве его нет. Если он вводится, то то же выражение нужно применить в базовом `ansible/roles/prometheus/templates/prometheus.yml.j2:66`, чтобы оба режима использовали одинаковое соответствие имён. Значение должно соответствовать конкретному Nova compute service host; нельзя выбирать его только по результату `hostname -f`.

### Вариант B: использовать уже имеющуюся метку PVS

Если `instance_hostname` точно совпадает с именами compute-сервисов Nova, достаточно переопределить globals стенда:

```yaml
watcher_prometheus_client_fqdn_label: "instance_hostname"
```

Роль запишет `fqdn_label = instance_hostname` в `[prometheus_client]`. Этот вариант локально восстановил построение запросов для совпадающих коротких имён. Он не устраняет несовпадение короткого имени с FQDN Nova.

Не использовать `fqdn_label = instance`: обычно Prometheus хранит там `IP:порт`. В шаблоне Watcher для такого значения предусмотрена строка отказа `ERROR_REFUSING_TO_RENDER_FQDN_LABEL_INSTANCE`.

Для host CPU/RAM необходима согласованная метка на job `node`. Метрики ВМ используют другой ключ — `resource`, содержащий UUID ВМ; добавление hostname label не заменяет recording rules для ВМ.

## 4. Исправить адрес Prometheus для Watcher

В globals стенда явно задать выбранный доступный внутренний endpoint. Если используется штатный HAProxy endpoint Prometheus, согласованная настройка выглядит так:

```yaml
watcher_prometheus_client_host: "{{ prometheus_internal_fqdn }}"
watcher_applier_prometheus_client_host: "{{ watcher_prometheus_client_host }}"
watcher_prometheus_client_port: "{{ prometheus_port }}"
```

Такие же значения можно принять как новые defaults в `ansible/roles/watcher/defaults/main.yml:218–223`, если общий контракт установки предполагает доступность Prometheus через внутренний HAProxy. До этого проверить DNS/VIP, listener и доступность именно из сети контейнера Watcher Engine. Для установки без такого frontend вместо него явно указать проверенный адрес Prometheus на monitoring-узле.

В `host` задаётся только DNS-имя или IPv4-адрес, без `http://`, `https://`, порта и `/api/v1`. В данной версии `_validate_host_port()` в `watcher/decision_engine/datasources/prometheus.py:84–99` не поддерживает IPv6-литералы; это отдельное ограничение исходника.

Engine и Applier имеют разные defaults. Поэтому при переопределении только `watcher_prometheus_client_host` нельзя считать адрес Applier автоматически изменённым. Также разные Prometheus-серверы могут иметь различную историю TSDB; наличие нескольких экземпляров само по себе её не синхронизирует.

## 5. Исправить метрики ВМ всех пользователей

Файл Kolla: `ansible/roles/prometheus/templates/watcher.rules.j2`.

В правиле `ceilometer_cpu` на строке 28 и в правиле `ceilometer_memory_usage` на строке 36 заменить:

```promql
topk by(domain) (1, libvirt_domain_openstack_info{user_name="admin"})
```

на:

```promql
topk by(domain) (1, libvirt_domain_openstack_info)
```

Остальные части выражений сохранить: соединение по `domain`, перенос `instance_id` и `label_replace`, формирующий `resource`. Сохранить существующие единицы результата и нормирование CPU на число vCPU.

При текущем фильтре ряды без metadata `user_name="admin"` не проходят соединение. Если exporter вообще не выдаёт такое значение, результат может оказаться пустым для всех ВМ. После изменения проверить наличие `instance_id` в исходных metadata и `resource=<UUID>` в вычисленных рядах, включая ВМ обычного пользователя.

Наличие файла `watcher.rules.j2` в исходниках не доказывает, что правила загружены работающим Prometheus. В архиве предусмотрены рендеринг `watcher.rules` (`tasks/config.yml:24–34`), доставка в контейнер (`templates/prometheus-server.json.j2:22–28`) и загрузка PVS glob `/etc/prometheus/*.rules`. Проверить каждый результат на стенде.

## 6. Если endpoint использует HTTPS или mTLS

Шаблон Kolla записывает `scheme = {{ watcher_prometheus_client_scheme }}`, но в `watcher/conf/prometheus_client.py` соответствующий параметр не зарегистрирован, а `_setup_prometheus_client()` в `watcher/decision_engine/datasources/prometheus.py:120–135` его не читает. Поэтому одно изменение `watcher_prometheus_client_scheme: "https"` не включает HTTPS в исследованном datasource.

В проверенном upstream-клиенте `python-observabilityclient` схема выбирается через настройку CA: `set_ca_cert()` включает проверку сертификата и HTTPS. В работающем образе требуется подтвердить соответствующую версию клиента.

Для TLS endpoint задать `watcher_prometheus_client_cafile` в globals равным реальному пути к доверенному CA **в контейнере Watcher**, например `/etc/ssl/certs/ca-certificates.crt`, если нужный CA действительно присутствует в этом bundle. Использовать имя endpoint, совпадающее с SAN сертификата. Сохранить согласованные basic-auth credentials; не переносить пароль в Markdown или командную строку.

Если выбранный listener требует клиентский сертификат, исходник Watcher поддерживает `certfile` и `keyfile`, но роль не рендерит эти поля в `[prometheus_client]`. Возможны два способа:

- Задать `[prometheus_client]` с `cafile`, `certfile`, `keyfile` в `{{ node_custom_config }}/watcher.conf` и обеспечить доставку файлов в контейнеры.
- Добавить явные переменные для cert/key в defaults роли, их рендеринг в `templates/watcher.conf.j2` и доставку сертификатов.

Выбор способа и путей зависит от TLS-контура стенда. Не добавлять клиентские сертификаты только по факту наличия HTTPS: необходимость определяется настройкой конкретного listener. Подробности общего контура сертификатов выходят за рамки исправления labels.

## 7. Проверки до применения и после него

### Сначала прочитать фактические настройки

Команды ниже приведены для Podman. При другом runtime заменить команду контейнерного движка. Они выполняют чтение; во время подготовки документа на стенде не запускались.

Вывести только несекретные параметры клиента в работающем Engine:

```bash
sudo podman exec -i watcher_engine python3 - <<'PY'
import configparser
cfg = configparser.ConfigParser(interpolation=None, strict=False)
loaded = cfg.read('/etc/watcher/watcher.conf')
if not loaded or not cfg.has_section('prometheus_client'):
    raise SystemExit('watcher.conf or [prometheus_client] not found')
for key in ('host', 'port', 'scheme', 'fqdn_label', 'instance_uuid_label',
            'cafile', 'certfile', 'keyfile'):
    print(f'{key}={cfg.get("prometheus_client", key, fallback="<unset>")}')
PY
```

Повторить для `watcher_applier`, если он используется для операций, читающих datasource. `scheme` в этом выводе — только содержимое файла, а не подтверждение того, что библиотека использует эту настройку.

Получить имена compute-сервисов Nova из окружения с настроенной OpenStack-аутентификацией:

```bash
openstack compute service list --service nova-compute -f json
```

Сравнить поле `Host` с labels активных targets в Prometheus (`/api/v1/targets?state=active`). Ожидается, например, `job="node"`, `instance="192.0.2.11:9100"`, `fqdn="compute01"` или согласованный `instance_hostname="compute01"`. Это иллюстративные значения, не адреса стенда.

Проверять доступность API Prometheus нужно из сети Watcher Engine, с теми же endpoint, CA и учётными данными. Работоспособность Grafana из браузера не подтверждает этот путь. Не ограничиваться `/-/ready`: datasource также должен успешно читать `/api/v1/targets?state=active` и `/api/v1/query`.

### Проверить конфигурацию и правила

Запустить проверки отдельно и проверить код возврата каждой:

```bash
sudo podman exec prometheus_server /opt/prometheus/promtool check config /etc/prometheus/prometheus.yml
sudo podman exec prometheus_server /opt/prometheus/promtool check rules /etc/prometheus/watcher.rules
sudo podman exec prometheus_server /opt/prometheus/promtool check web-config /etc/prometheus/web.yml
```

Штатный `ansible/roles/prometheus/tasks/config_validate.yml:5–8` соединяет проверки config и web-config через `;`, поэтому успешная вторая команда может скрыть ненулевой код первой. Для приёмки данной правки нужны результаты обеих проверок, а не только общий `rc` роли.

В UI Prometheus или через его API выполнить:

| PromQL | Что подтверждает |
|---|---|
| `up{job="node"}` | Состояние scrape Node exporter |
| `count by (fqdn, instance_hostname) (node_cpu_seconds_total{job="node"})` | Какие имена и ключи реально присутствуют |
| `count(node_cpu_seconds_total{fqdn="compute01"})` | Наличие рядов конкретного узла для варианта A |
| `count(node_cpu_seconds_total{instance_hostname="compute01"})` | Наличие рядов конкретного узла для варианта B |
| `count(ceilometer_cpu)` | Наличие вычисленных CPU-метрик ВМ |
| `count(ceilometer_memory_usage)` | Наличие вычисленных RAM-метрик ВМ |
| `ceilometer_cpu{resource="<VM_UUID>"}` | Наличие CPU-метрики конкретной ВМ |
| `ceilometer_memory_usage{resource="<VM_UUID>"}` | Наличие RAM-метрики конкретной ВМ |

Заменить `compute01` и `<VM_UUID>` фактическими значениями. Проверить минимум одну ВМ обычного пользователя. Отсутствующий результат запроса `count(...)` также означает отсутствие подходящих рядов; не следует ожидать обязательного числового нуля.

Убедиться, что `/api/v1/rules` содержит группу `watcher_ceilometer_emulation`, оба recording rules и не сообщает об ошибках их вычисления. После появления новых меток/рядов накопить достаточное число samples для используемых окон; исходник обычно запрашивает последние 300 секунд.

Проверить журнал Engine на сообщения:

```text
Could not create fqdn labels list from Prometheus targets config
Cannot build host_instance_map without fqdn_instance_labels
Cannot query prometheus without instance label
Cannot build prometheus query without args
```

Эти ошибки указывают на mapping/query. Ошибки соединения, HTTP 401/403 и проверки сертификата требуют сначала исправить endpoint, аутентификацию или TLS.

### Порядок внедрения

1. Зафиксировать текущие globals, фактический `[prometheus_client]`, выбранный шаблон Prometheus и имена Nova. Выбрать вариант A или B.
2. Внести изменения в источники конфигурации/роли, проверить рендеринг и итоговый diff. Для recording rules проверить синтаксис и оба выражения.
3. По принятой процедуре обновить Prometheus и подтвердить labels, загрузку правил и появление рядов. При варианте B без изменений правил/Prometheus этот шаг не нужен.
4. Обновить конфигурацию Watcher и применить её принятой процедурой. Роль содержит обработчик перезапуска `watcher-engine`; это реальное изменение сервиса, а не read-only проверка.
5. Повторить проверки API и datasource. Контролируемый аудит Watcher использовать как отдельную проверку стратегии без автоматического применения плана действий.

Порядок применения зависит также от ограничений комплектации роли, отмеченных в общем [руководстве мониторинга](PROMETHEUS_GRAFANA_ADMIN_GUIDE.md). В частности, проверить разрешение импорта `pvs_post_config.yml`: файл находится на уровне `ansible/pvs_post_config.yml`, а в каталоге tasks роли его нет. До внедрения установленная роль должна успешно проходить синтаксическую проверку; данный документ не подтверждает работоспособность всей цепочки deploy/reconfigure.

Откат: вернуть исходные изменения шаблонов/globals/rules и применить тот же штатный процесс конфигурации. Не удалять TSDB или существующие данные Prometheus. После отката отдельно проверить доступность сервисов; прежний дефект labels при этом может вернуться.

## 8. Что проверено при подготовке документа

Изученные 86 файлов Kolla (роли Watcher/Prometheus, набор PVS Prometheus, group vars) и два файла Watcher datasource/config совпали с ZIP побайтово. Проверены пути доставки конфигурации и правил.

Локальное воспроизведение использовало рендеринг блока job `node` и неизменённые методы `PrometheusHelper`, извлечённые из архивного исходника. Ответ API targets был подставным, `health="up"`. Это проверка логики mapping, не запуск полного Watcher и не обращение к настоящему Prometheus.

| Вариант | Результат |
|---|---|
| Базовый шаблон, `fqdn_label=fqdn`, Nova host `compute01` | Имя найдено, CPU-запрос построен |
| PVS-шаблон, `fqdn_label=fqdn`, Nova host `compute01` | Имя не найдено, построение запроса завершается `InvalidParameter` |
| PVS-шаблон, `fqdn_label=instance_hostname`, Nova host `compute01` | Имя найдено, CPU-запрос построен |
| PVS-шаблон, `fqdn_label=instance_hostname`, Nova host `compute01.example.test` | Короткое имя не сопоставлено с полным, построение запроса завершается ошибкой |

Также подтверждено наличие фильтра `user_name="admin"` в обеих recording rules и отсутствие чтения опции `scheme` в архивном datasource. Предлагаемые изменения в роли не применялись. DNS, VIP, firewall, credentials, сертификаты, фактические labels и получение метрик на стенде остаются предметом эксплуатационной проверки.

## 9. Источники и версии

| Архив | Коммит из комментария ZIP | SHA-256 |
|---|---|---|
| `kolla-ansible-pvs_1.0.0_21.09zip.zip` | `365af98421ff35db2e9ca5ee605723a1bcc8e756` | `e68e98cb5ce6d2384ebf90c4ff1e6a9b779efe986ae11a83bc8cb1b556bfe004` |
| `watcher-pvs_1.0.0_21.09.zip` | `96eeba4c5b8ce30f29fd7d6461bdac28fdfdfa4d` | `67722deaa94b4e606620519c34a3db84f3253c492e7238f78bf0045a65c2ac0b` |

Архивный код является основанием выводов о данной поставке. Официальные материалы использованы для проверки контракта datasource и поведения внешнего клиента:

- [Watcher 2025.1: Prometheus datasource](https://docs.openstack.org/watcher/2025.1/datasources/prometheus.html) — hostname label, `resource`, параметры клиента.
- [OpenStack python-observabilityclient: prometheus_client.py](https://github.com/openstack/python-observabilityclient/blob/master/observabilityclient/prometheus_client.py) — `set_ca_cert()` и выбор схемы в `_get_url()`. Ссылка на upstream `master` не фиксирует версию библиотеки внутри образа стенда.
