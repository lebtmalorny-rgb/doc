# Prometheus и Grafana в OpenStack: руководство администратора

> Пути к исходникам указаны внутри архивов соответствующей версии; состав и коммиты см. в [README](README.md). В репозитории публикуется только Markdown.

## 1. Краткая справка: от общего к частному

**Prometheus собирает метрики, Grafana показывает их, Alertmanager доставляет уведомления.** Exporters предоставляют метрики Linux-узлов, гипервизоров, контейнеров и инфраструктурных сервисов. OpenStack exporter получает сведения через API облака; Blackbox exporter проверяет доступность endpoints. Это разные виды наблюдения: работающий HTTP endpoint ещё не подтверждает успешное создание ВМ.

**В исследованной ветке используется дополнительный набор PVS.** Он автоматически подготавливает конфигурации Prometheus/Alertmanager, правила и дашборды Grafana. Поэтому состав мониторинга определяется не только `ansible/roles/prometheus/templates`, но и `ansible/alerts/prometheus`. Параметры установки задаются в globals, сложные scrape jobs, правила и панели — отдельными файлами.

**В архиве поставляются два дашборда:** `Node Exporter Full` и `(sber) Troubleshooting infrastructure v100`. Найдены 18 файлов правил PVS с 160 записями alert и 25 записями recording rule. Это состав поставки, а не подтверждение загрузки правил и получения всех метрик на стенде.

| Уровень | Компонент | Что наблюдает |
|---|---|---|
| Linux | Node exporter | CPU, RAM, файловые системы, диски, сеть и доступные collectors ОС |
| Контейнеры | cAdvisor | Ресурсы и присутствие контейнеров; покрытие Podman требует проверки |
| Виртуализация | Libvirt exporter | CPU, RAM, диски, сеть и состояние ВМ со стороны гипервизора |
| Облако | OpenStack exporter | Состояния агентов, ВМ, ёмкость и объекты сервисов через API |
| Инфраструктура | MySQL, HAProxy, RabbitMQ, Memcached, ProxySQL и другие | Работоспособность и внутренние показатели сервисов |
| Доступность | Blackbox exporter | HTTP/TCP-проверки endpoints, длительность проверки, TLS при применимом модуле |
| Представление / оповещение | Grafana / Alertmanager | Запросы к Prometheus / маршрутизация сработавших alert rules |

Поток данных: `exporters/API → Prometheus → Grafana`; для уведомлений — `Prometheus → Alertmanager → настроенный получатель`. Сам Prometheus обращается к exporters; для Blackbox дополнительно нужен доступ **от exporter к проверяемому сервису**. Порты приведены в [руководстве по firewall](FIREWALL_ADMIN_GUIDE.md).

**Граница проверки:** документ основан на локальных исходниках от 21.09.2026. Targets, временные ряды, отправка уведомлений и наличие панелей в работающей Grafana не проверялись. В `prometheus/tasks/deploy.yml` найден статический импорт **отсутствующего `pvs_post_config.yml`**. До восстановления согласованного комплекта роли нельзя считать этот архив готовым к `deploy`/`reconfigure`; отключение PVS флагом не гарантирует обход ошибки статического импорта. Исходники при подготовке документа не исправлялись.

## 2. Где задаются параметры: globals, all.yml и отдельные конфиги

Под «alls» понимается **`ansible/group_vars/all.yml`** в Kolla-Ansible. Это базовые значения поставки. Конкретную установку настраивать через `/etc/kolla/globals.yml` либо `/etc/kolla/globals.d/monitoring.yml`, сохраняя исходные defaults для сравнения.

| Где | Что задаётся | Примеры / назначение |
|---|---|---|
| `ansible/group_vars/all.yml` | Defaults включения сервисов, портов, интервалов и retention | `enable_prometheus*`, `prometheus_port`, `prometheus_scrape_interval`, `prometheus_cmdline_extras` |
| `ansible/roles/prometheus/defaults/main.yml` | Контейнеры, группы, volumes, аргументы exporters, endpoints Blackbox, путь PVS | Источник defaults; поддерживаемые переменные переопределять в globals |
| `/etc/kolla/globals.yml` или `globals.d/monitoring.yml` | Выбор компонентов и параметры площадки | Флаги, интервалы, retention, публикация UI/API, `kolla_pvs_alerts_enabled` |
| `/etc/kolla/passwords.yml` | Пароли Prometheus, Grafana и служебных подключений | Например, `prometheus_password`, `prometheus_grafana_password`; не хранить в globals |
| Inventory / `host_vars` | Узлы групп exporters, адреса и дополнительные labels | `monitoring`, `prometheus-node-exporter`, `prometheus-libvirt-exporter`; `sm_ci`, `prometheus_instance_label` |
| `ansible/alerts/prometheus/` либо отдельный каталог `kolla_pvs_alerts_path` | Поддерживаемый исходный набор PVS: `rules/*.rules`, `templates/*` | Основной источник при включённом PVS; удобен отдельный версионируемый каталог площадки |
| `/etc/kolla/config/prometheus/prometheus.yml` | Общая конфигурация Prometheus | При PVS **перезаписывается** из набора; не хранить здесь единственную ручную копию |
| `/etc/kolla/config/prometheus/<HOST>/prometheus.yml` | Полная конфигурация для конкретного узла | Имеет приоритет над общим файлом и шаблоном роли |
| `/etc/kolla/config/prometheus/prometheus.yml.d/*.yml` и `<HOST>/prometheus.yml.d/*.yml` | Дополнительные фрагменты YAML | Merge после основного файла; списки расширяются, а не заменяются по `job_name` |
| `/etc/kolla/config/prometheus/*.rules`, `*.tmpl`, `prometheus-alertmanager.yml` | Правила, шаблоны сообщений, Alertmanager | PVS заново копирует одноимённые файлы; новые уникальные файлы можно сопровождать отдельно |
| `/etc/kolla/config/prometheus/prometheus-blackbox-exporter.yml` | Модули Blackbox | Отдельный поддержанный override; только фактически выбранные targets запускают проверки |
| `ansible/alerts/grafana/` либо `kolla_pvs_grafana_path` | Исходные `provisioning/prometheus-datasource.yaml.j2`, `dashboards/*.json` | PVS копирует в `/etc/kolla/config/grafana/` |
| `/etc/kolla/config/grafana/prometheus.yaml`, `provisioning.yaml`, `dashboards/*.json` | Datasource, provider, панели | `prometheus.yaml` и поставляемые JSON перезаписываются PVS; provider можно сопровождать отдельно |
| `/etc/kolla/config/grafana.ini` и `/etc/kolla/config/grafana/<HOST>/grafana.ini` | Дополнительные INI-настройки Grafana | Merge после шаблона роли; не путать с итоговым `/etc/kolla/grafana/grafana.ini` на сервисном узле |
| `/etc/kolla/<service>/…` на сервисных узлах | Сгенерированные файлы для контейнеров | Проверять итог; не использовать как постоянный источник настроек |
| `/etc/prometheus/…`, `/etc/grafana/provisioning/…`, `/var/lib/grafana/dashboards/` внутри контейнеров | Файлы, которые читают приложения | Проверять загрузку и ошибки; ручная правка потеряется при следующей доставке |

Обычный CLI загружает `globals.yml`, затем `passwords.yml`, затем файлы `globals.d` по алфавиту, затем пользовательские `-e`. Более позднее определение переменной перекрывает предыдущее. `/etc/kolla` — default, изменяемый `--configdir`; `node_custom_config` и `node_config_directory` имеют разные роли. Загрузка переменных (`kolla-ansible-pvs_1.0.0/kolla_ansible/ansible.py`).

### 2.1. Значения по умолчанию

| Настройка | Значение / зависимость |
|---|---|
| `enable_prometheus` | От `enable_security_audit`; аудит включён в defaults ветки |
| `enable_prometheus_server`, `enable_prometheus_node_exporter`, `enable_prometheus_cadvisor`, `enable_prometheus_openstack_exporter`, `enable_prometheus_blackbox_exporter`, `enable_prometheus_alertmanager` | От `enable_prometheus` |
| `enable_prometheus_libvirt_exporter` | Prometheus + Nova + тип виртуализации `kvm`/`qemu` |
| `enable_prometheus_mysqld_exporter`, `enable_prometheus_haproxy_exporter`, `enable_prometheus_memcached_exporter` | От включения соответственно MariaDB / HAProxy / Memcached |
| `enable_prometheus_rabbitmq_exporter`, `enable_prometheus_fluentd_integration`, `enable_prometheus_elasticsearch_exporter`, `enable_prometheus_proxysql_exporter`, `enable_prometheus_etcd_integration` | Prometheus + соответственно RabbitMQ / Fluentd / OpenSearch / ProxySQL / etcd |
| `enable_ironic_prometheus_exporter` | Ironic + Prometheus |
| `enable_prometheus_ceph_mgr_exporter` | `no`; endpoints задаются отдельно |
| `kolla_pvs_alerts_enabled` | От `enable_prometheus` |
| `prometheus_scrape_interval` | `60s` |
| `scrape_timeout`, `evaluation_interval` | `10s`, `15s` в основном шаблоне; это поля отдельного конфига, а не одноимённые globals-переменные |
| `prometheus_openstack_exporter_interval`, `prometheus_openstack_exporter_timeout` | `60s` через общий интервал, `45s` |
| `prometheus_libvirt_exporter_interval` | `60s` |
| Retention | `--storage.tsdb.retention.time=7d` при включённом аудите через `prometheus_cmdline_extras`; не универсальное свойство любой установки |
| `enable_prometheus_server_external` | `false` |
| `enable_prometheus_openstack_exporter_external` | `no` |
| `enable_prometheus_alertmanager_external` | От включения Alertmanager: внешний frontend нужно оценить явно |

Период хранения и частоту сбора выбирают по ёмкости диска, числу рядов и требуемой глубине истории. Изменение `prometheus_scrape_interval` не меняет автоматически отдельные явно переопределённые интервалы. TSDB хранится в `/var/lib/prometheus` контейнера, используется volume `prometheus_server`. Наличие нескольких серверов и active/passive HAProxy не означает репликацию их TSDB.

Источники: all.yml (`kolla-ansible-pvs_1.0.0/ansible/group_vars/all.yml`), defaults Prometheus (`kolla-ansible-pvs_1.0.0/ansible/roles/prometheus/defaults/main.yml`).

## 3. Как выбирается фактическая конфигурация

При обычном `deploy`/`reconfigure` сначала выполняется `pvs_alerts.yml`: шаблоны и правила из `ansible/alerts/prometheus` подготавливаются в `node_custom_config`. Затем `config.yml` выбирает основной Prometheus YAML в следующем порядке:

1. `/etc/kolla/config/prometheus/<inventory_hostname>/prometheus.yml`.
2. `/etc/kolla/config/prometheus/prometheus.yml` — сюда PVS уже записал свой шаблон.
3. `ansible/roles/prometheus/templates/prometheus.yml.j2` — только если overrides отсутствуют.

После выбранной основы присоединяются общие и узловые `prometheus.yml.d/*.yml`. `extend_lists: true` означает, что добавленный job с уже существующим именем не заменяет его. Для изменения существующего job сопровождать выбранный основной шаблон или полный узловой файл; результат проверить `promtool`.

**Отключение `kolla_pvs_alerts_enabled` не удаляет ранее подготовленные файлы.** Старый общий `prometheus.yml` продолжит иметь приоритет. Переход между PVS и базовой ролью требует резервной копии, явного согласования оставшихся overrides и проверки итогового конфига. `genconfig` не равнозначен выполнению всех подготовительных задач `deploy`: сравнивать следует фактическую цепочку конкретной команды.

Grafana аналогично подготавливает datasource и JSON из `ansible/alerts/grafana`. Затем роль доставляет их в контейнер: datasource — `/etc/grafana/provisioning/datasources/prometheus.yaml`, provider — `/etc/grafana/provisioning/dashboards/provisioning.yaml`, панели — `/var/lib/grafana/dashboards`. Default provider использует организацию `1` и пустую папку. Правки provisioned-панелей следует сохранять в сопровождаемых JSON, учитывая повторную загрузку файлов. [Grafana provisioning](https://grafana.com/docs/grafana/latest/administration/provisioning/#dashboards).

Источники: PVS staging (`kolla-ansible-pvs_1.0.0/ansible/roles/prometheus/tasks/pvs_alerts.yml`), merge конфигурации (`kolla-ansible-pvs_1.0.0/ansible/roles/prometheus/tasks/config.yml`), подготовка Grafana (`kolla-ansible-pvs_1.0.0/ansible/roles/grafana/tasks/pvs_grafana_datasource.yml`), Grafana config (`kolla-ansible-pvs_1.0.0/ansible/roles/grafana/tasks/config.yml`).

## 4. Какие сервисы и метрики собираются

### 4.1. Jobs, для которых в ветке есть штатная интеграция

Имена ниже взяты из **PVS-шаблона**, содержащего 24 условных объявления `job_name`. Это не 24 гарантированно активных targets. Число targets зависит от флагов, inventory и отдельной конфигурации; одно объявление может содержать несколько узлов.

В таблице приведены назначение и примеры ожидаемых метрик. Точные имена, labels и доступность рядов зависят от версии exporter и его collectors. Исходники образов exporters в этих архивах отсутствуют; полный runtime-каталог получают через `/metrics` и API Prometheus. Для OpenStack, Node, Libvirt, MySQL, HAProxy и RabbitMQ конкретные примеры ниже также встречаются в поставленных rules/панелях.

| Job в PVS | Endpoint / порт по умолчанию | Что собирается |
|---|---|---|
| `prometheus` | Группа `prometheus`, TCP/9091 | Состояние самого Prometheus: reload, ошибки вычисления правил, scrape, TSDB; например `prometheus_config_last_reload_successful`, `prometheus_rule_evaluation_failures_total` |
| `node` | `prometheus-node-exporter`, TCP/9100 | CPU `node_cpu_seconds_total`, RAM `node_memory_MemAvailable_bytes`, файловые системы `node_filesystem_*`, диски `node_disk_*`, сеть `node_network_*`, load и collectors ОС |
| `mysqld` | `prometheus-mysqld-exporter`, TCP/9104 | Доступность MySQL `mysql_up`, Galera `mysql_global_status_wsrep_*`, блокировки и InnoDB; права мониторингового пользователя влияют на полноту |
| `haproxy` | `loadbalancer`, TCP/9101 | Состояние backend/server, HTTP-коды, ошибки healthcheck, время ответа; например `haproxy_backend_up`, `haproxy_server_check_failures_total` |
| `rabbitmq_internal` | `rabbitmq`, TCP/15692 | Native Prometheus endpoint RabbitMQ: сообщения, соединения, память, файловые дескрипторы; правила используют `rabbitmq_queue_messages`, `rabbitmq_connections` и другие семейства, совместимость версий проверить |
| `memcached` | `prometheus-memcached-exporter`, TCP/9150 | Hits/misses, connections, items, память и eviction; фактические семейства `memcached_*` проверить в exporter |
| `cadvisor` | `prometheus-cadvisor`, TCP/18080 | CPU, память, I/O и сеть контейнеров в пределах включённых collectors; правило присутствия использует `container_last_seen` |
| `fluentd` | `fluentd`, TCP/24231 | Внутренние показатели Fluentd, входной/выходной поток и буферы согласно установленным plugins; это не содержимое логов |
| `ceph_mgr_exporter` | Список `prometheus_ceph_mgr_exporter_endpoints` | Показатели Ceph mgr Prometheus module; disabled по умолчанию, адреса и порты задаёт администратор внешнего Ceph |
| `openstack_exporter` | Внутренний FQDN/VIP, TCP/9198 | Объекты/состояния через OpenStack API: `openstack_nova_agent_state`, `openstack_nova_server_status`, `openstack_neutron_agent_state`, `openstack_cinder_*`, ёмкость Nova |
| `elasticsearch_exporter` | `prometheus-elasticsearch-exporter`, TCP/9108 | Состояние кластера OpenSearch, индексов, shards и ресурсов через совместимый exporter; имя job исторически содержит Elasticsearch |
| `blackbox_exporter` | Exporter TCP/9115, `/probe` | Доступность endpoints `probe_success`, длительность и параметры проверки; дополнительные проверки UI/TLS формируются PVS-шаблоном |
| `blackbox_exporter_service_check` | Через Blackbox TCP/9115 | Дополнительные HTTP-проверки Nova API VIP и backend согласно условиям шаблона |
| `libvirt_exporter` | `prometheus-libvirt-exporter`, TCP/9177 | ВМ: `libvirt_domain_info_cpu_time_seconds_total`, `libvirt_domain_info_virtual_cpus`, `libvirt_domain_memory_stats_used_percent`, `libvirt_domain_block_stats_*`, `libvirt_domain_interface_stats_*` |
| `etcd` | `etcd`, обычно TCP/2379 | Native endpoint etcd: Raft, операции, дисковая задержка, ресурсы процесса; только при включённом etcd, TLS — по его настройке |
| `ironic_prometheus_exporter` | `ironic-conductor`, TCP/9608 | Данные датчиков bare metal, переданные Ironic; набор зависит от BMC и драйвера, не равен мониторингу ОС bare metal |
| `alertmanager` | `prometheus-alertmanager`, TCP/9093 | Метрики обработки alerts, уведомлений и самого Alertmanager |
| `proxysql` | `loadbalancer`, TCP/6070 | Native metrics ProxySQL: соединения и показатели проксирования БД; в PVS job вложен также в условие включённого Alertmanager |

**OpenStack exporter не означает сбор произвольных метрик всех API.** Роль отключает volume collector без Cinder, DNS без Designate, load-balancer без Octavia. В архиве нет отдельных штатных exporters Masakari, Mistral или Watcher: их API присутствуют среди условных Blackbox endpoints, а события и журналы относятся к другому контуру.

**Метрики ВМ снимаются с гипервизора.** Они не подтверждают исправность приложения внутри гостя и не заменяют гостевого агента мониторинга. Служебная информация `libvirt_domain_openstack_info` используется для связки domain с UUID/именем ВМ и проектом.

**Особенности collectors:** дополнительные параметры Node exporter по умолчанию пусты; наличие Systemd/Hardware-панелей не включает соответствующий collector. У cAdvisor задан `--docker_only` и отключены, среди прочего, `percpu`, `tcp`, `udp`, `process`, `sched`, `hugetlb`, `memory_numa`. При default `kolla_container_engine=podman` необходимо проверить фактическое присутствие нужных контейнеров в рядах. У Ironic `send_sensor_data_interval=300` секунд: scrape раз в минуту не делает исходные датчики минутными.

Источники: PVS scrape config (`kolla-ansible-pvs_1.0.0/ansible/alerts/prometheus/templates/prometheus.yml.j2`), контейнеры и параметры exporters (`kolla-ansible-pvs_1.0.0/ansible/roles/prometheus/defaults/main.yml`), Ironic config (`kolla-ansible-pvs_1.0.0/ansible/roles/ironic/templates/ironic.conf.j2`).

### 4.2. Дополнительные условные объявления

| Job | Флаг в шаблоне | Что требуется дополнительно |
|---|---|---|
| `rabbitmq` | `enable_prometheus_rabbitmq_exporter_external` | Шаблон повторно опрашивает ту же группу `rabbitmq` и `prometheus_rabbitmq_exporter_port`, что `rabbitmq_internal`; отдельный exporter не развёртывает. Одновременное включение создаёт ряды с разными `job` для одного endpoint |
| `ovs_exporter` | `enable_prometheus_ovs_exporter` | Exporter OVS, inventory-группа, порт и интервал; rules ожидают ошибки/drops интерфейсов `ovs_interface_*` |
| `consul_exporter` | `enable_prometheus_consul_exporter` | Exporter Consul, группа, порт и интервал; rules ожидают `consul_up`, health, Serf и Raft |
| `multipath_exporter` | `enable_prometheus_multipath_exporter` | Exporter multipath, группа и порт; rules ожидают `multipath_path_status`, `multipath_status`, ошибки |
| `hypervisor_exporter` | `enable_prometheus_hypervisor_exporter` | Внешняя реализация, группа, порт; контракт метрик не определён полным сервисом в этой роли |
| `bird_exporter` | `enable_prometheus_bird_exporter` | Exporter BIRD, группа, порт и интервал; не следует считать автоматически включённым мониторингом BGP |

Для этих флагов используется `default(false)`. Для пяти дополнительных exporters OVS, Consul, multipath, hypervisor и BIRD в проверенных `all.yml`, штатном inventory и `prometheus_services` нет полного соответствующего описания развёртывания. Одного `enable_…: "yes"` в globals недостаточно: возможны отсутствующие переменные/группы и отсутствие самого listener. Наличие `consul.rules`, `ovs.rules` и `multipath.rules` не устраняет эту зависимость.

### 4.3. Что именно проверяет Blackbox

Штатный модуль `os_endpoint` принимает HTTP 200/300 и ожидает `versions` в теле ответа. Это проверка публикации версии API. Дополнительно определены `http_2xx`, `tcp_connect`, `tls_connect`, `ssh_banner`, `icmp` и отдельные HTTP-модули с аутентификацией для некоторых UI. Определённый модуль сам не создаёт проверку: нужен target, который его использует.

PVS добавляет UI-проверки и отдельный `blackbox_exporter_service_check`. Для диагностики смотреть labels `service`, `module`, `instance`: `up=1` означает успешный scrape exporter, а `probe_success=1` — успешную проверку конечного сервиса. Модули Blackbox (`kolla-ansible-pvs_1.0.0/ansible/roles/prometheus/templates/prometheus-blackbox-exporter.yml.j2`).

## 5. Правила, вычисляемые метрики и уведомления

### 5.1. Состав набора PVS

Alert rules определяют состояние предупреждения. Recording rules сохраняют результат PromQL под новым именем для дальнейших запросов. Они не заменяют исходный exporter. [Механизм recording rules](https://prometheus.io/docs/prometheus/latest/configuration/recording_rules/).

| Файл в `ansible/alerts/prometheus/rules/` | Alert entries | Recording entries | Назначение |
|---|---:|---:|---|
| `cinder.rules` | 9 | 0 | Состояние Cinder, томов, snapshots и ёмкость |
| `consul.rules` | 10 | 0 | Доступность Consul, health, Serf/Raft |
| `docker.rules` | 1 | 0 | Присутствие контейнеров |
| `haproxy.rules` | 7 | 0 | Backend, HTTP-ошибки, healthcheck |
| `libvirt.rules` | 3 | 0 | Состояния виртуализации |
| `mariadb.rules` | 14 | 0 | MySQL/Galera, блокировки |
| `multipath.rules` | 4 | 0 | Состояние путей к storage |
| `neutron.rules` | 2 | 0 | Агенты Neutron |
| `nova.rules` | 5 | 0 | Агенты Nova |
| `ovs.rules` | 8 | 0 | Ошибки и drops интерфейсов OVS |
| `prometheus-sber.rules` | 11 | 0 | Контроль инфраструктуры и сбора |
| `prometheus.rules` | 14 | 0 | Scrape, reload, вычисление правил, Alertmanager discovery |
| `rabbitmq.rules` | 16 | 0 | Очереди, память, сообщения, partitions |
| `sber-alerts.rules` | 6 | 0 | Сводные состояния OpenStack |
| `sber-host.rules` | 14 | 1 | Хосты, bonding, FC, память и storage |
| `sber-metrics.rules` | 0 | 21 | Агрегаты AZ/region/domain для ёмкости и производительности |
| `sber-vm.rules` | 7 | 2 | Состояние и показатели ВМ |
| `system.rules` | 29 | 1 | CPU, RAM, filesystem, сеть и системные состояния |
| **Всего** | **160** | **25** | Количество записей в YAML, не число уникальных имён или активных alerts |

Примеры вычисляемых рядов: `az:openstack_nova_vcpus_used:sum`, `az:openstack_nova_memory_free:sum`, `region:libvirt_domain_block_stats_capacity_bytes:sum`, `vm:libvirt_domain_vcpu_delay_seconds_total:rate5m`. Они зависят от наличия исходных метрик и labels для join. Пустой результат запроса — не обязательно нормальное состояние объекта.

В базовой роли дополнительно имеются `watcher.rules.j2` с двумя recording entries и `security-audit.rules.j2` с `OpenStackServiceDown`. Последний срабатывает после двух минут неудачного `os_endpoint` probe; Horizon исключён фильтром. Их фактическую доставку и загрузку проверить по `rule_files`, файлам контейнера и API `/api/v1/rules`. В частности, обработка пользовательских `*.rules` в `config.yml` и glob-копирование в контейнер зависят от `enable_prometheus_alertmanager`.

Количество 18 взято из файлов, а не из `ansible/alerts/README.md`, где упомянуто 19. В `system.rules` также встречается `node_network_trasmit_errs_total` с пропущенной буквой: это пример условия, которое требует проверки на существующие ряды, даже если YAML успешно читается. Исходные правила автоматически не исправлялись.

### 5.2. Watcher и связь с пользователями AD

`watcher.rules.j2` формирует `ceilometer_cpu` из скорости CPU time Libvirt, нормированной на число vCPU, и `ceilometer_memory_usage` из `libvirt_domain_memory_stats_used_percent`. Оба результата — проценты; название `ceilometer_*` здесь не означает, что включён сбор Ceilometer.

В обоих join жёстко задано `libvirt_domain_openstack_info{user_name="admin"}`. Поэтому покрытие ВМ, созданных другими пользователями, включая AD, **не подтверждено**. Метка `resource` создаётся из `instance_id`. При приёмке проверить ВМ обычного AD-пользователя, а не только локального администратора.

Ещё одно различие: базовый scrape-шаблон добавляет узлам label `fqdn` для Watcher, а активный PVS-шаблон содержит `instance_hostname`, `region`, `sm_ci`, но не этот label. Watcher по умолчанию ищет host-метрики по `fqdn`. Перед эксплуатацией его стратегий необходимо согласовать labels и запросы; работа дашборда сама по себе не подтверждает работу datasource Watcher.

Источники: Watcher recording rules (`kolla-ansible-pvs_1.0.0/ansible/roles/prometheus/templates/watcher.rules.j2`), базовый scrape-шаблон (`kolla-ansible-pvs_1.0.0/ansible/roles/prometheus/templates/prometheus.yml.j2`), Watcher Prometheus options (`watcher-pvs_1.0.0/watcher/conf/prometheus_client.py`). Настройка AD описана в [LDAP-документе](LDAP_AD_ADMIN_GUIDE.md).

### 5.3. Alertmanager: что необходимо настроить отдельно

PVS-шаблон содержит receivers `admins`, `dez-smena`, `monitoring`, `default-receiver`, маршруты по `team`, `severity`, `alertname` и группировку по labels. Исходные интервалы: `group_wait=30s`, `group_interval=5m`, `repeat_interval=8736h` с локальными переопределениями в дочерних маршрутах.

**Готовых получателей уведомлений нет.** При отсутствии `pvs_smtp_smarthost` используются пустые `webhook_configs`; при его задании поля email `to` остаются пустыми. Нужно подготовить собственный шаблон Alertmanager с адресатами/webhooks, TLS, маршрутизацией и согласованными интервалами. Сам флаг включения Alertmanager не подтверждает доставку.

SMTP-параметры PVS: `pvs_smtp_smarthost`, `pvs_smtp_hello`, `pvs_smtp_from`, `pvs_smtp_user`, `pvs_smtp_require_tls`; пароль `pvs_smtp_password` — в защищённом passwords-файле. Редактирование одного `smtp_*` не считать достаточным: PVS рендерит свой файл до последующих задач с локальным отображением SMTP-переменных. В исходных email receivers стоит `require_tls: false`, поэтому один глобальный SMTP TLS-флаг не заменяет проверку полного итогового файла.

**Webhook аудита:** базовый шаблон роли содержит receiver для `OpenStackServiceDown` с отправкой на Fluentd-узел, TCP/19890. PVS-шаблон его не содержит и имеет приоритет после staging. Для передачи событий в аудит требуется явно сохранить/добавить соответствующий маршрут в сопровождаемый Alertmanager config и проверить доставку.

Источники: Alertmanager PVS (`kolla-ansible-pvs_1.0.0/ansible/alerts/prometheus/templates/alertmanager.yml`), базовый Alertmanager (`kolla-ansible-pvs_1.0.0/ansible/roles/prometheus/templates/prometheus-alertmanager.yml.j2`), security audit rule (`kolla-ansible-pvs_1.0.0/ansible/roles/prometheus/templates/security-audit.rules.j2`).

## 6. Какие дашборды поставляются в Grafana

### 6.1. Node Exporter Full

Файл: node-exporter.json (`kolla-ansible-pvs_1.0.0/ansible/alerts/grafana/dashboards/node-exporter.json`). UID: `rYdddlPWk`. В JSON 142 объекта панели, включая 16 строк-разделов; 126 объектов имеют тип панели, отличный от `row`.

| Разделы | Что показывают |
|---|---|
| Quick / Basic CPU, Mem, Net, Disk | Общую загрузку CPU, RAM, дисков и сети |
| Memory Meminfo / Vmstat | Состав памяти, paging и swap |
| System Timesync / Processes / Misc / Systemd | Время, процессы, системные показатели и units при наличии нужных collectors |
| Hardware Misc | Доступные аппаратные показатели ОС |
| Storage Disk / Filesystem | I/O, пропускную способность, задержки, место и inodes |
| Network Traffic / Sockstat / Netstat | Трафик, ошибки, drops, sockets и протокольную статистику |
| Node Exporter | Состояние и параметры сбора exporter |

Переменные: `ds_prometheus`, `job`, `nodename`, `node`. Datasource выбирается через `${ds_prometheus}`. В поставленном JSON есть локальные дополнения с `openstack_nova_agent_state`, включая панель памяти активных compute-хостов; это не полностью независимый от OpenStack dashboard.

### 6.2. (sber) Troubleshooting infrastructure v100

Файл: sber-dashboard.json (`kolla-ansible-pvs_1.0.0/ansible/alerts/grafana/dashboards/sber-dashboard.json`). UID: `ff707996-13bf-4507-9d50-9a8a2f508a7d`. В JSON 71 объект, включая 16 строк-разделов, 54 панели с указанным типом и один объект без `type`.

| Разделы | Что показывают |
|---|---|
| AZ overview / service status | Ёмкость, агенты Nova/Neutron и состояния инфраструктуры |
| Hypervisor max over time / CPU / memory | Сводные и временные показатели хоста |
| Hypervisor I/O / network details | Диски, FC, сеть и ошибки по устройствам |
| VM state / max over time | Состояния ВМ и сводную диагностику |
| VM CPU / memory / vCPU per cores | Использование ресурсов и показатели отдельных vCPU |
| VM disk / disk by devices | IOPS, объём операций, throughput и задержки |
| VM network / drop / error packets | Трафик и ошибки виртуальных интерфейсов |

Дашборд объединяет `node_*`, `libvirt_*`, `openstack_*` и вычисляемые ряды из rules. Переменные включают AZ, hostname, domain/VM и устройства. У переменной с именем `region` запрос фактически извлекает label **`instance`** из `up{job="openstack_exporter"}` — не предполагать, что это список `openstack_region_name`.

Datasource жёстко связан с UID **`PBFA97CFB590B2093`**. Этот UID назначает поставленный PVS datasource (`kolla-ansible-pvs_1.0.0/ansible/alerts/grafana/provisioning/prometheus-datasource.yaml.j2`). При ручном создании datasource с другим UID панели могут не найти источник, даже если URL и имя совпадают. Grafana обращается к Prometheus от собственного backend с `prometheus_grafana_user`/`prometheus_grafana_password`; AD-вход пользователя — отдельная настройка.

**Других dashboard JSON в исследованном каталоге нет.** Отдельные панели для RabbitMQ, MariaDB, HAProxy, Masakari, Mistral и Watcher не поставляются этим набором. Файлы alert rules с похожими именами не являются дашбордами.

## 7. Практическая настройка

### 7.1. Параметры в globals

Пример основных overrides в `/etc/kolla/globals.d/monitoring.yml` для установки с Nova/KVM. Это дополнение к существующим настройкам, не замена всего `globals.yml` и не команда запуска:

```yaml
enable_prometheus: "yes"
enable_grafana: "yes"
enable_prometheus_server: "yes"
enable_prometheus_node_exporter: "yes"
enable_prometheus_openstack_exporter: "yes"
enable_prometheus_libvirt_exporter: "yes"
enable_prometheus_blackbox_exporter: "yes"
enable_prometheus_alertmanager: "yes"
kolla_pvs_alerts_enabled: true

prometheus_scrape_interval: "60s"
prometheus_openstack_exporter_interval: "60s"
prometheus_openstack_exporter_timeout: "45s"
prometheus_libvirt_exporter_interval: "60s"
prometheus_cmdline_extras: "--storage.tsdb.retention.time=7d"

# Пример публикации только во внутреннем контуре.
enable_prometheus_server_external: false
enable_prometheus_openstack_exporter_external: "no"
enable_prometheus_alertmanager_external: "no"
```

Для собственного набора скопировать полную структуру PVS в сопровождаемые каталоги и указать, например, `kolla_pvs_alerts_path: /etc/kolla/pvs-monitoring/prometheus`, `kolla_pvs_grafana_path: /etc/kolla/pvs-monitoring/grafana`. Это **отдельные пути**: первому нужны `rules/` и `templates/`, второму — `provisioning/` и `dashboards/`. Не направлять их на каталог с единственным файлом.

Существующие служебные пароли сохранять в `/etc/kolla/passwords.yml` и принятом хранилище секретов. PVS staging делает datasource Grafana читаемым с mode `0644`, хотя YAML содержит BasicAuth-пароль: доступ к deployment-узлу и копиям этого файла должен соответствовать обращению с секретом.

### 7.2. Отдельные конфиги

Дополнительный **новый** scrape job можно положить в `/etc/kolla/config/prometheus/prometheus.yml.d/site.yml`. Пример только для уже подготовленного стороннего exporter; адрес и порт заменить, доступ согласовать по firewall:

```yaml
scrape_configs:
  - job_name: site_example_exporter
    scrape_interval: 60s
    static_configs:
      - targets:
          - "exporter.example.org:9100"
        labels:
          service: site_example
```

Правила — отдельный `site.rules` с секцией `groups`; SMTP/webhooks — в сопровождаемом шаблоне `templates/alertmanager.yml` набора PVS или полном узловом override. Dashboard — отдельный JSON в наборе Grafana. Для изменения основного интервала вычисления правил можно задать `global.evaluation_interval` в YAML-фрагменте; не придумывать одноимённую Ansible-переменную, которой шаблон не читает.

При внутреннем mTLS PVS меняет `scheme` ряда jobs на HTTPS. Это не доказательство, что соответствующий exporter уже слушает TLS: серверный listener, CA, клиентский сертификат и фактический endpoint нужно согласовать отдельно. Некоторые TLS-блоки шаблона содержат `insecure_skip_verify: true`; проверка наличия HTTPS сама по себе не доказывает проверку подлинности сервера.

### 7.3. Последовательность применения

1. Сохранить globals, passwords, `config/prometheus`, `config/grafana`, собственные PVS-наборы и inventory. Снять текущий список targets, rules и дашбордов.
2. **До запуска исправить комплект поставки роли:** восстановить согласованный `pvs_post_config.yml` либо получить исправленную версию ветки. Проверить цепочку `deploy.yml` → статические импорты. Этот документ не предлагает создавать пустой файл для обхода ошибки.
3. Проверить группы/адреса, необходимые exporters, секреты, доверие TLS и сетевые потоки. Изменения интеграций RabbitMQ, HAProxy, Fluentd, Ironic и других сервисов могут требовать применения соответствующих ролей.
4. На тестовом контуре подготовить итоговую конфигурацию, проверить YAML и команды `promtool` раздельно, сверить job names и `rule_files`.
5. После проверки комплектности и в согласованное окно применить изменения. Для изменения уже развёрнутого мониторинга команда ниже ограничивает роли Prometheus/Grafana; для включения интеграций в других сервисах перечень ролей расширяется по изменению.

```bash
# Выполнять только после устранения отсутствующего import и проверки конфигурации.
kolla-ansible -i /etc/kolla/multinode reconfigure --tags prometheus,grafana
```

Команда меняет конфигурацию и может перезапустить контейнеры. Она приведена для администратора и при подготовке документа не выполнялась. Возврат предыдущих файлов требует повторного применения и проверки; сам по себе возврат globals не восстанавливает историю TSDB и не удаляет оставшиеся overrides.

## 8. Проверка работающей установки без изменения настроек

### 8.1. Файлы и валидаторы

На нужных узлах, с учётом используемого container engine:

```bash
sudo podman ps --format '{{.Names}}'
sudo podman exec prometheus_server /opt/prometheus/promtool check config /etc/prometheus/prometheus.yml
sudo podman exec prometheus_server /opt/prometheus/promtool check web-config /etc/prometheus/web.yml
sudo podman exec grafana ls -l /var/lib/grafana/dashboards
sudo podman logs --since 15m prometheus_server
sudo podman logs --since 15m grafana
```

Проверки `promtool` выполнять отдельно и оценивать обе: в `config_validate.yml` ветки они объединены через `;`, поэтому exit code последней команды может скрыть ошибку первой. Логи и конфиги перед передачей наружу очищать от секретов. Отсутствие синтаксических ошибок не доказывает наличие рядов, используемых правилами.

### 8.2. Targets, правила и ряды Prometheus

Использовать фактический внутренний endpoint, принятый CA и учётную запись мониторинга. Пример с HTTPS: `curl --user admin` запросит пароль интерактивно, пароль в команду не включён. Если установка публикует другой порт/протокол, адаптировать URL по сгенерированной конфигурации.

```bash
curl --fail --silent --show-error --user admin \
  --cacert /path/to/internal-ca.pem \
  'https://prometheus.example.org:9091/api/v1/targets?state=active'

curl --fail --silent --show-error --user admin \
  --cacert /path/to/internal-ca.pem \
  'https://prometheus.example.org:9091/api/v1/rules'

curl --fail --silent --show-error --user admin \
  --cacert /path/to/internal-ca.pem --get \
  --data-urlencode 'query=count by (job) (up)' \
  'https://prometheus.example.org:9091/api/v1/query'
```

В targets проверить `health`, `lastError`, адрес, labels и интервал. В rules — наличие ожидаемых файлов/групп и ошибки вычисления. Через `/api/v1/label/__name__/values` можно получить имена метрик, но историческое наличие имени не доказывает текущую свежесть ряда. [HTTP API Prometheus](https://prometheus.io/docs/prometheus/latest/querying/api/).

Полезные запросы для Prometheus UI / Grafana Explore:

| Запрос | Что проверяет |
|---|---|
| `up == 0` | Targets с неуспешным последним scrape |
| `count by (job) (up)` | Наличие ожидаемых jobs и количество targets, включая DOWN |
| `probe_success == 0` | Неудачные Blackbox-проверки конечных endpoints |
| `count(node_cpu_seconds_total)` | Наличие host CPU рядов |
| `count(libvirt_domain_info_cpu_time_seconds_total)` | Наличие CPU рядов ВМ |
| `openstack_nova_agent_state` | Фактические состояния/labels агентов Nova для проверки dashboard joins |
| `count(ceilometer_cpu)` | Наличие вычисляемых CPU рядов Watcher; отдельно сверить UUID ВМ обычного пользователя |
| `count by (fqdn) (node_cpu_seconds_total)` | Наличие нужной Watcher метки; отдельно проверить, что `fqdn` не пустой |

### 8.3. Grafana и уведомления

В Grafana проверить datasource, его UID, успешность запроса `up` в Explore и оба UID дашбордов. Выбрать реальный узел/ВМ и интервал с данными. При `No data` проверить последовательно источник, исходную метрику, labels, recording rule и фильтры переменных панели. Присутствие JSON на диске не заменяет успешное provisioning без ошибок.

Для уведомлений сначала проверить загруженные receivers/routes Alertmanager и реального адресата. Контрольный alert выполнять отдельно в согласованном тестовом сценарии; критерий — получение и разрешение сообщения нужным каналом. Для аудита отдельно подтвердить приём webhook и появление события в журнале. При подготовке документа контрольные сообщения не отправлялись.

## 9. Источники и подтверждённые ограничения

| Источник | Что подтверждает |
|---|---|
| `kolla-ansible-pvs_1.0.0_21.09zip.zip`, коммит `365af98421ff35db2e9ca5ee605723a1bcc8e756` из ZIP comment | Основной срез ролей, templates, rules и dashboards |
| `watcher-pvs_1.0.0_21.09.zip`, коммит `96eeba4c5b8ce30f29fd7d6461bdac28fdfdfa4d` | Ожидания datasource Watcher |
| deploy.yml (`kolla-ansible-pvs_1.0.0/ansible/roles/prometheus/tasks/deploy.yml`) | Staging PVS и импорт отсутствующего `pvs_post_config.yml` |
| Каталог правил (`kolla-ansible-pvs_1.0.0/ansible/alerts/prometheus/rules`) | 18 файлов, 160 alert entries, 25 recording entries |
| Каталог дашбордов (`kolla-ansible-pvs_1.0.0/ansible/alerts/grafana/dashboards`) | Два JSON, названия, UID и запросы панелей |
| Валидация роли (`kolla-ansible-pvs_1.0.0/ansible/roles/prometheus/tasks/config_validate.yml`) | Необходимость отдельно проверять config и web-config |

Defaults с `openstack_release: latest` и привязка коллекции `openstack.kolla` к `stable/2025.1` не устанавливают версии работающих exporters. Полное подтверждение готовности требует восстановления комплекта роли, проверки каждого ожидаемого target и используемых метрик, загрузки двух dashboards, проверки Watcher labels/охвата ВМ и доставки уведомлений. Это эксплуатационные критерии; их выполнение на стенде данным документом не заявляется.
