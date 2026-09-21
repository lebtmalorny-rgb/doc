# Firewall OpenStack: порты, правила доступа и реализация в Kolla-Ansible

> Пути к исходникам указаны внутри архивов соответствующей версии; состав и коммиты см. в [README](README.md). В репозитории публикуется только Markdown.

## 1. Краткая справка: от общего к частному

**Доступ в OpenStack фильтруется на нескольких уровнях.** Внешний firewall ограничивает доступ к адресам облака; host firewall защищает сами узлы; Neutron Security Groups управляют доступом к сетевым портам виртуальных машин. Разрешение порта на одном уровне не означает, что соединение разрешено на остальных.

**В исследованной ветке есть два отдельных механизма firewalld:** добавление TCP-портов внешних HAProxy frontend при `enable_external_api_firewalld=true` и самостоятельная команда `kolla-ansible host-firewall`. Первая только добавляет разрешения, вторая умеет формировать ограничительную policy для входящего трафика к узлу.

**Что открыто и что закрыто:** после успешного применения ограничительной policy разрешаются SSH, ICMP/ICMPv6 и перечисленные в плане потоки от определённых источников к определённым адресам. Прочий трафик, дошедший до завершающего правила этой policy, отбрасывается. Без фактических правил узла, inventory и сетевых проверок нельзя объявить порт открытым или закрытым на действующем стенде.

**Текущий каталог нельзя применять как готовый полный список разрешений для любой конфигурации.** Он содержит 38 сервисных записей и 66 потоков, однако не описывает ряд нужных связей: VRRP, VXLAN, OpenSearch, webhook аудита и некоторые варианты libvirt/миграции. При политике обработки неизвестных флагов `warning`, установленной по умолчанию, неизвестный сервис сам по себе не блокирует применение. Подробности — в разделе 6.

| Класс доступа | Требуемая граница | Что подтверждено исходниками |
|---|---|---|
| Пользователи облака | Только опубликованные UI/API на VIP/FQDN | Порты и HAProxy frontend задаются ролями |
| Администраторы | SSH и административные API с согласованных адресов | Host policy разрешает SSH **без ограничения источника**; внешнее ограничение нужно отдельно |
| Межсервисные соединения | Только нужные узлы и сети | Каталог содержит группы источников/назначения; текущая проекция использует сеть `api` |
| Базы, очереди, exporters | Не публиковать в пользовательскую/внешнюю сеть | Наличие listener не означает разрешение для внешних клиентов |
| Остальные новые входящие соединения | Запрет, если явно не согласованы | В host policy есть завершающий `drop` |
| Исходящий трафик и трафик ВМ | Самостоятельные правила и проверки | Эта host policy не управляет `OUTPUT`, `FORWARD`, NAT и Security Groups |

**Граница проверки:** анализ архивов от 21.09.2026, без подключения к узлам. Ни правила firewall, ни сервисы, ни сеть при подготовке документа не изменялись. Значения ниже — исходные defaults и логика генерации; команды — инструкция для отдельной эксплуатационной проверки.

## 2. Исходный срез и условия чтения таблиц

| Архив | Коммит из комментария ZIP | Использование |
|---|---|---|
| `kolla-ansible-pvs_1.0.0_21.09zip.zip` | `365af98421ff35db2e9ca5ee605723a1bcc8e756` | Роли, шаблоны, переменные, host-firewall |
| `masakari-pvs_1.0.0_21.09.zip` | `702480386d63c935a6f1b143fbd65f54dba63f52` | Подтверждение API-порта `15868` |
| `watcher-pvs_1.0.0_21.09.zip` | `96eeba4c5b8ce30f29fd7d6461bdac28fdfdfa4d` | Подтверждение API-порта `9322` |

Конфигурация по умолчанию ориентирована на SberLinux и Podman. В ней включены основные OpenStack-сервисы, Cinder, Ironic, Masakari, Mistral, Watcher, Consul, ProxySQL, Grafana и аудит безопасности; окончательные значения определяются inventory, `globals.yml`, `globals.d`, переменными узлов и `-e`. Таблицы не являются вычисленным inventory действующей установки.

Обозначения:

- **Разрешить по назначению** — требование к согласованной схеме доступа, а не утверждение о существующем правиле.
- **Есть в каталоге** — роль может сформировать правило при выполнении её условий; это ещё не применённое разрешение.
- **Нет в каталоге** — нужный поток следует учитывать отдельно; его отсутствие не доказывает закрытие в runtime.
- Все номера относятся к **порту назначения**. Ответный трафик проверяется вместе с stateful-правилами, а не через открытие всех ephemeral-портов снаружи.

Источник чисел: group_vars/all.yml (`kolla-ansible-pvs_1.0.0/ansible/group_vars/all.yml`). Источник состава разрешений: каталог host-firewall (`kolla-ansible-pvs_1.0.0/ansible/roles/host-firewall/vars/catalog.yml`).

### 2.1. Где задаются параметры: globals, all.yml и отдельные конфиги

Под «alls» здесь понимается **`ansible/group_vars/all.yml`** в исходниках Kolla-Ansible. Это defaults поставки; параметры конкретной площадки задаются в globals и inventory.

| Где | Что задаётся | Как использовать |
|---|---|---|
| `ansible/group_vars/all.yml` | Исходные порты сервисов, `enable_*`, сетевые интерфейсы, TLS и `enable_external_api_firewalld` | Справочник defaults; site overrides хранить в globals |
| `/etc/kolla/globals.yml` или `globals.d/network.yml` | Выбранные сервисы, порты, интерфейсы, VIP/FQDN, TLS, публикация через HAProxy | Основное место настроек установки; изменение порта сервиса ещё не гарантирует изменение всех правил каталога |
| Inventory, `host_vars`, `group_vars` установки | Состав `control`, `compute`, `monitoring`, `loadbalancer`, адреса, `ansible_host`, `ansible_port` | Определяют узлы и источники/назначения; учитывать переопределение одноимённых значений через globals/CLI |
| `ansible/roles/host-firewall/defaults/main.yml` | Defaults режима, таймаута rollback, проверок и operator sources | Не редактировать ради разового применения |
| Отдельный YAML, например `/etc/kolla/host-firewall-apply.yml`, переданный через `-e @…` | `host_firewall_plan_id`, `host_firewall_verification_checks`, `host_firewall_operator_sources`, политика флагов | Хранить параметры конкретного проверенного плана; пример в разделе 8 |
| `ansible/roles/host-firewall/vars/catalog.yml` и код компилятора | Модель разрешённых потоков, фиксированные порты, поддержанные протоколы | Это реализация ветки; произвольный YAML сервиса в `/etc/kolla/config` её автоматически не расширяет |
| `/etc/kolla/config/<service>/…` (`node_custom_config`) | Поддержанные ролью дополнительные конфиги сервисов на deployment-узле | Сверять получившийся listener и отдельно учитывать его в firewall |
| firewalld runtime/permanent на узлах | Фактически действующие правила и сохранённая конфигурация | Проверять отдельно от globals; ручные изменения учитывать при управлении policy |
| Neutron Security Groups | Правила доступа к портам ВМ | Управляются API/CLI OpenStack, а не `host-firewall` и не `globals.yml` |

CLI загружает `globals.yml`, затем `globals.d` по алфавиту и пользовательские `-e`; обычные команды дополнительно читают `passwords.yml` между globals и globals.d, но `host-firewall` запускается **без passwords**. Встроенный параметр команды `--mode` задаёт режим после пользовательских extra vars. `all.yml` не является отчётом о фактическом состоянии firewall. CLI (`kolla-ansible-pvs_1.0.0/kolla_ansible/ansible.py`), defaults host-firewall (`kolla-ansible-pvs_1.0.0/ansible/roles/host-firewall/defaults/main.yml`).

## 3. Порты, которые нужны сервисам

### 3.1. Пользовательские UI и API

Доступ разрешается к опубликованным VIP/FQDN от согласованных клиентских сетей. Прямой доступ клиентов к backend-адресам узлов для обычного использования API не требуется.

| Сервис | TCP-порт по умолчанию | Переменная / условие |
|---|---:|---|
| Horizon | 80 или 443 | `horizon_port`, `horizon_tls_port`; 443 зависит от TLS |
| Keystone | 5000 | `keystone_internal_port`, `keystone_public_listen_port` |
| Glance | 9292 | `glance_api_port` |
| Nova API | 8774 | `nova_api_port` |
| Neutron API | 9696 | `neutron_server_port` |
| Cinder API | 8776 | `cinder_api_port` |
| Placement | 8780 | `placement_api_port`; доступ только необходимым клиентам |
| Ironic API | 6385 | `ironic_api_port`; административный контур |
| Masakari API | 15868 | `masakari_api_port`; административный контур |
| Mistral API | 8989 | `mistral_api_port`; административный контур |
| Watcher API | 9322 | `watcher_api_port`; административный контур |
| noVNC proxy | 6080 | `nova_novncproxy_port`, если выбран noVNC |
| SPICE proxy | 6082 | `nova_spicehtml5proxy_port`, только если выбран SPICE; отсутствует в host-каталоге |
| Serial console proxy | 6083 | `nova_serialproxy_port`, если сервис включён |
| Grafana | 3000 | `grafana_server_port`; внешний доступ зависит от публикации |
| OpenSearch Dashboards | 5601 | `opensearch_dashboards_port`; административная сеть, нет в host-каталоге |
| Prometheus | 9091 | `prometheus_port`; в этой ветке **не 9090** |
| Alertmanager UI/API | 9093 | `prometheus_alertmanager_port`; административная сеть |

При `haproxy_single_external_frontend=true` внешние HTTP API могут использовать общий порт `haproxy_single_external_frontend_public_port` — обычно 443 с TLS или 80 без TLS — и разные FQDN. Backend-порты сохраняются. Один флаг `kolla_enable_tls_external` сам по себе не переводит все API с 5000/8774/9696 на 443; нужно смотреть фактические frontend и endpoint.

В исходных defaults внешний/внутренний TLS не следует считать включённым. Порт 80 Horizon может быть redirect на HTTPS; решение о его доступности принимается по сгенерированному HAProxy. Для production-схемы публикация API должна соответствовать принятой политике TLS.

Подтверждение API-портов дополнительных архивов: Masakari service options (`masakari-pvs_1.0.0/masakari/conf/service.py`), Watcher API options (`watcher-pvs_1.0.0/watcher/conf/api.py`). Для реального bind-адреса приоритет имеет сгенерированная конфигурация Kolla, а не default сервиса вне контейнерной установки.

### 3.2. Внутренние управляющие и кластерные соединения

Эти порты не предназначены для общего внешнего доступа. Названия групп — из inventory; точный список IP устанавливается по действующей конфигурации.

| Назначение | Протокол / порт | Источники и получатели по назначению | Учёт в host-каталоге |
|---|---|---|---|
| SSH администратора | TCP/22 или `ansible_port` | Deployment/bastion → узлы | Есть, но правило разрешает любые источники |
| Синхронизация Fernet | TCP/8023 | Keystone ↔ Keystone | Есть |
| Nova SSH | TCP/8022 | Compute ↔ compute | Есть; число фиксировано в каталоге |
| Nova metadata backend | TCP/8775 | HAProxy/нужные metadata-компоненты → nova-metadata | Есть от `loadbalancer`; не пользовательская публикация |
| MariaDB / ProxySQL SQL frontend | TCP/3306 | Клиенты БД → соответствующий frontend/backend | Есть; отдельные записи MariaDB и ProxySQL |
| Galera replication | TCP/4567 | MariaDB ↔ MariaDB | Есть только TCP; иной транспорт проверять отдельно |
| Galera IST / SST | TCP/4568, TCP/4444 | MariaDB ↔ MariaDB | Есть |
| MariaDB clustercheck | TCP/4569 | Проверяющий компонент → MariaDB | Нет отдельной записи |
| ProxySQL admin | TCP/6032 | Только доверенный контур управления БД | Есть от `common`, то есть разрешение шире одного bastion |
| RabbitMQ AMQP | TCP/5672 либо TLS TCP/5671 | Сервисы OpenStack → RabbitMQ | Есть, выбор зависит от TLS |
| RabbitMQ EPMD / cluster | TCP/4369, TCP/25672 | Участники кластера и необходимые control-узлы | Есть от `control` |
| RabbitMQ management | TCP/15672 | Ограниченный admin/monitoring-контур | Есть от `loadbalancer` |
| Memcached | TCP/11211 | Разрешённые сервисы → Memcached | Есть; UDP выключен аргументом `-U 0` |
| etcd client / peer | TCP/2379, TCP/2380 | Клиенты etcd / участники кластера | Есть только при включённом etcd; default — `no` |
| Consul HTTP | TCP/8500 | Необходимые узлы → Consul | Есть |
| Consul LAN gossip | TCP и UDP/8501 | Consul agents/servers | Есть; в этой ветке это **8501**, не стандартный 8301 |
| Consul server RPC | TCP/8300 | Consul clients/servers → servers | Есть |
| Consul WAN gossip | TCP и UDP/8302 | Consul servers | Есть |
| Consul DNS | TCP и UDP/8600 | Разрешённые клиенты → Consul | Есть |
| Corosync | UDP/5405 | Узлы `hacluster` ↔ `hacluster` | Есть |
| Pacemaker Remote | TCP/3121 | `hacluster` → `hacluster-remote` | Есть |
| Keepalived VRRP | IP protocol 112, без TCP/UDP-порта | Только участники VRRP | **Нет:** запись Keepalived имеет пустой `flows` |
| Libvirt | TCP/16509 либо TLS TCP/16514 | Нужные compute/control → compute, сеть migration | В каталоге только 16509, адрес сети api |
| iSCSI target | TCP/3260 | Инициаторы compute/control → storage target | Есть для `enable_tgtd`; внешние СХД учитывать отдельно |
| Ironic HTTP | TCP/8089 | Нужные provisioning-клиенты → Ironic HTTP | Есть только от группы `ironic`; не полный provisioning-профиль |

Адрес libvirt берётся из `migration_interface_address`. Если migration и api разнесены, разрешение к API-адресу не заменяет разрешение к migration-адресу. Источники: libvirt defaults (`kolla-ansible-pvs_1.0.0/ansible/roles/nova-cell/defaults/main.yml`), libvirtd.conf (`kolla-ansible-pvs_1.0.0/ansible/roles/nova-cell/templates/libvirtd.conf.j2`), Consul (`kolla-ansible-pvs_1.0.0/ansible/roles/consul/templates/consul-server.hcl.j2`), Keepalived (`kolla-ansible-pvs_1.0.0/ansible/roles/loadbalancer/templates/keepalived/keepalived.conf.j2`), Memcached (`kolla-ansible-pvs_1.0.0/ansible/roles/memcached/templates/memcached.json.j2`).

### 3.3. Мониторинг, журналы и аудит

| Получатель | Протокол / порт | Кому нужен доступ | Есть в каталоге |
|---|---|---|---|
| HAProxy stats / monitor | TCP/1984, TCP/61313 | `monitoring` | Да, числа фиксированы |
| Prometheus server | TCP/9091 | `monitoring`; другие клиенты согласно схеме | Да |
| Alertmanager | TCP/9093 | `monitoring`, `loadbalancer` | Да |
| Alertmanager cluster | TCP и UDP/9094 при соответствующей кластеризации | Участники Alertmanager | Каталог разрешает только TCP |
| Node exporter | TCP/9100 | Prometheus/monitoring | Да |
| HAProxy exporter | TCP/9101 | Prometheus/monitoring | Да |
| MySQL exporter | TCP/9104 | Prometheus/monitoring | Да |
| Blackbox exporter | TCP/9115 | Prometheus → exporter; exporter → проверяемые endpoints | Нет отдельной записи для listener/9115 |
| Memcached exporter | TCP/9150 | Prometheus/monitoring | Да |
| Libvirt exporter | TCP/9177 | Prometheus/monitoring | Да |
| OpenStack exporter | TCP/9198 | `monitoring`, `loadbalancer` | Да |
| RabbitMQ exporter | TCP/15692 | Prometheus/monitoring | Да |
| ProxySQL exporter | TCP/6070 | Prometheus/monitoring | Да |
| cAdvisor | TCP/18080 | Prometheus/monitoring | Да; не 8080 |
| Fluentd metrics | TCP/24231 | Prometheus/monitoring | Да |
| Ironic exporter | TCP/9608 | Prometheus/monitoring | Да |
| Syslog/Fluentd | UDP/5140 | Согласованные узлы `common` | Да; не автоматически 514 |
| OpenSearch REST | TCP/9200, HTTPS при аудите безопасности | Fluentd, Dashboards, exporters и доверенные клиенты | Нет |
| OpenSearch transport | Обычно TCP/9300; подтвердить выбранный порт | Только OpenSearch ↔ OpenSearch | Нет |
| OpenSearch exporter | TCP/9108 | Prometheus/monitoring | Нет |
| Webhook security audit | TCP/19890 | Alertmanager → узел webhook, выбранный шаблоном | Нет |

Порт OpenSearch transport в шаблоне не фиксируется: upstream допускает диапазон выбора `9300–9400`, поэтому разрешать следует подтверждённые listener/настройки, а не автоматически весь диапазон. [OpenSearch network settings](https://docs.opensearch.org/latest/install-and-configure/configuring-opensearch/network-settings/). Для кластерного обмена Alertmanager требуются оба протокола — TCP и UDP — на выбранном cluster-порту. [Alertmanager HA](https://github.com/prometheus/alertmanager/blob/main/README.md#high-availability).

Внутренний webhook задаётся systemd-шаблоном (`kolla-ansible-pvs_1.0.0/ansible/roles/common/templates/security-audit-webhook.service.j2`), его адрес для Alertmanager — базовым шаблоном Alertmanager (`kolla-ansible-pvs_1.0.0/ansible/roles/prometheus/templates/prometheus-alertmanager.yml.j2`). Включённый по умолчанию набор PVS подменяет этот шаблон конфигурацией без данного receiver: наличие listener/19890 не доказывает доставку событий. Подробности — в [руководстве по мониторингу](PROMETHEUS_GRAFANA_ADMIN_GUIDE.md). HTTP-порт и TLS OpenSearch определяются opensearch.yml.j2 (`kolla-ansible-pvs_1.0.0/ansible/roles/opensearch/templates/opensearch.yml.j2`).

### 3.4. Трафик ВМ, storage и внешние зависимости

Эта таблица задаёт обязательные категории проверки. Указанные условные протокольные defaults нельзя считать уже реализованными правилами host-firewall.

| Поток | Типичный протокол / порт | Где разрешать и что уточнить |
|---|---|---|
| OVS VXLAN | UDP/4789 | Между tunnel-IP нужных compute/network-узлов; в host-каталоге отсутствует |
| OVN Geneve, если выбран OVN | UDP/6081 | Между tunnel-IP; проверить реализацию выбранного backend |
| OVN NB/SB / OVSDB | TCP/6641, TCP/6642 / TCP/6640 в переменных ветки | Только нужные компоненты; OVSDB в ряде шаблонов привязан к `127.0.0.1`, не открывать наружу по одному номеру |
| DHCP / DNS / metadata ВМ | UDP/67–68, TCP/UDP 53, metadata HTTP в соответствующем namespace | Проверять Neutron namespaces и datapath, отдельно от host INPUT |
| QEMU live migration / дисплеи ВМ | Фактические диапазоны libvirt/QEMU | В шаблонах ветки полный диапазон не задан; получить конфигурацию образа, domain XML и listener. 8022 и 16509/16514 не гарантируют полноту |
| NFS / внешняя СХД / Ceph | По контракту СХД; например NFSv4 TCP/2049 | Только storage-клиенты ↔ согласованные серверы; NFSv3 и динамические RPC требуют отдельной матрицы |
| Ironic PXE/TFTP, если используется | DHCP и UDP/69 плюс реальные provisioning-потоки | Только provisioning-сеть; для virtual media требования другие |
| Redfish / IPMI | Обычно TCP/443 / UDP/623 | Ironic conductor или иной фактический исполнитель → BMC; API Masakari не означает прямой доступ каждого controller ко всем BMC |
| Active Directory LDAPS | TCP/636 | Keystone, Grafana, OpenSearch → согласованный DC; см. [LDAP AD](LDAP_AD_ADMIN_GUIDE.md) |
| DNS / NTP | TCP и UDP/53 / обычно UDP/123 | Узлы → назначенные серверы |
| Registry, пакетные репозитории, secret manager | Порт фактического URL | Deployment/контейнерные узлы → конкретные endpoint; не универсальный доступ в Интернет |

В OVS-шаблоне заданы `tunnel_types=vxlan` и `OVSHybridIptablesFirewallDriver`. Это описание backend Security Groups, а не список разрешённых правил ВМ. Шаблон OVS agent (`kolla-ansible-pvs_1.0.0/ansible/roles/neutron/templates/openvswitch_agent.ini.j2`), [Neutron: VXLAN port](https://docs.openstack.org/neutron/2025.1/configuration/openvswitch-agent.html#agent.vxlan_udp_port). Сети libvirt также могут иметь собственные правила DNS/DHCP/FORWARD. [Описание фильтрации libvirt](https://libvirt.org/firewall.html).

## 4. Какие порты должны быть закрыты

Запрет формулируется для пары «источник → адрес назначения», а не для номера порта во всём облаке.

| Источник → назначение | Требуемое ограничение | Что делает текущая реализация |
|---|---|---|
| Недоверенные сети → БД, RabbitMQ, Memcached, Consul, exporters | Запрет прямого доступа | При действующей host policy — drop, если источник не попал в разрешения; внешние ACL проверяются отдельно |
| Пользователи → backend-IP API | Доступ через опубликованный VIP/FQDN | Каталог ограничивает backend источниками; operator-адреса добавляются отдельно |
| Любой источник → неиспользуемый сервис | Не публиковать и не разрешать без потребности | Выключенный сервис обычно не даёт поток, но отдельные подфункции учтены неполно |
| Недоверенные сети → SSH | Доступ только с bastion/deployment | **Не обеспечивается host policy:** SSH разрешён без `source` |
| Любой источник → UDP/11211 | Не требуется для Memcached этой ветки | Listener отключён `-U 0`; это ещё не доказательство отдельного firewall-запрета |
| OpenStack → LDAP TCP/389 | Не нужен для выбранного LDAPS/636 | Host policy не фильтрует исходящий трафик; запрет задаётся egress ACL отдельно |
| Любой непрописанный входящий поток к узлу | Drop после нужных исключений | Завершающий rich rule `drop` в `kolla-host-input` |

Отсутствие разрешения `firewall-cmd --list-ports` не является достаточным доказательством закрытия: разрешение может находиться в service, rich rule, policy, direct rule или другом firewall. Отсутствие listener означает отсутствие слушающего процесса, но не наличие правила DROP. Неудачное соединение также может быть вызвано маршрутом, bind-адресом или отказом приложения.

## 5. Детали реализации

### 5.1. Открытие внешних HAProxy-портов

При `enable_external_api_firewalld: "true"` задача `haproxy-config` добавляет `port/tcp` внешнего включённого frontend в `external_api_firewalld_zone`, по умолчанию `public`. Устанавливаются runtime и permanent разрешения. В условии также проверяются `enable_haproxy` и `kolla_action != "config"`.

В задаче нет ограничения по IP источника и нет удаления устаревших разрешений. Она не реализует «закрыть всё остальное» и не обслуживает межсервисный UDP/VRRP. По умолчанию переменная равна `false`. Если существует ранняя host policy с DROP, позднее разрешение zone может не сделать порт доступным. Проверяется весь путь обработки пакета. Задача firewalld (`kolla-ansible-pvs_1.0.0/ansible/roles/haproxy-config/tasks/main.yml`).

Комментарий `disable_firewall` в примере `globals.yml` не доказывает текущее состояние firewalld. `bootstrap-servers` вызывает внешнюю роль `openstack.kolla.baremetal`; код этой коллекции не вложен в архив Kolla-Ansible. Её установленную версию и действия нужно проверять отдельно. Bootstrap playbook (`kolla-ansible-pvs_1.0.0/ansible/kolla-host.yml`).

### 5.2. Отдельная команда host-firewall

```bash
kolla-ansible host-firewall -i /path/to/multinode --mode report
```

Команда зарегистрирована в setup.cfg (`kolla-ansible-pvs_1.0.0/setup.cfg`), реализована в CLI (`kolla-ansible-pvs_1.0.0/kolla_ansible/cli/commands.py`) и запускает host-firewall.yml (`kolla-ansible-pvs_1.0.0/ansible/host-firewall.yml`). Режимы: `report`, `apply`, `rollback`; по умолчанию `report`. Обычные `deploy`/`reconfigure` этот playbook не запускают. Для команды запрещены `--tags`, `--skip-tags` и подмена playbook.

`report` читает адреса, маршруты, сокеты, правила nftables/iptables и состояние firewalld. Ничего не устанавливает, не включает службу и не применяет правила. В консоль выводятся `plan_id`, выбранные узлы, `candidate_flows`, `blockers`, `warnings` и ограниченная сводка. `report.json` и `report.md` на deployment-узле не создаются. Подробные наблюдения остаются в памяти под `no_log`.

Кандидаты вычисляются из каталога и переменных, а не автоматически разрешаются по всем найденным `ss` listener. `apply_ready` в диагностическом отчёте задаётся как `false`; это не итог успешного применения и не самостоятельный критерий отказа admission.

### 5.3. Что компилируется в правила

Собственная policy: `kolla-host-input`, `ingress_zones=[ANY]`, `egress_zones=[HOST]`, `target=CONTINUE`, приоритет policy `-500`.

| Порядок rich rules | Условие | Решение |
|---|---|---|
| `-30000` | TCP на SSH-порт inventory | `accept`, без IP источника и назначения |
| `-29000` | IPv4 ICMP и IPv6 ICMP | `accept`, без ограничения источника |
| `-20000` | Источник, IP назначения, TCP/UDP-порт из кандидатов | `accept` |
| `30000` | Всё оставшееся, дошедшее до policy | `drop` |

SSH-порт выбирается из `ansible_port`, затем `ansible_ssh_port`, затем `host_firewall_ssh_port` (22). Адреса peer-узлов превращаются в `/32` или `/128`. К источникам **каждого** потока добавляются адреса оператора, найденные в группе `deployment` или заданные через `host_firewall_operator_sources`. Эти адреса получают доступ также к включённым backend-портам; это не только список для SSH.

Несмотря на общее название `operator_sources`, текущий CLI-проектор принимает из него отдельные IP через `ip_address`; CIDR-строки не проходят эту проекцию. Не задавать `192.0.2.0/24` в расчёте на поддержку подсети. Не расширять доступ до `0.0.0.0/0` ради работы API.

Для части потоков создаются дополнительные кандидаты на internal/external VIP. Они используют тот же порт, что backend-поток; источники — узлы собранной модели и operator-IP. Это не полноценная отдельная модель внешних клиентов. Источники: проекция (`kolla-ansible-pvs_1.0.0/ansible/action_plugins/kolla_firewall_model.py`), модель (`kolla-ansible-pvs_1.0.0/ansible/module_utils/kolla_firewall_model.py`), компилятор (`kolla-ansible-pvs_1.0.0/ansible/module_utils/kolla_firewall_plan.py`).

Правила действуют в контексте полного firewall: loopback, established/related, более ранние цепочки и независимые таблицы нужно смотреть в runtime. Policy не даёт абсолютной гарантии доступности поверх других DROP. Она не изменяет чужие zone/policy, NAT, `FORWARD`, `OUTPUT` и Neutron Security Groups.

### 5.4. Применение, проверка и откат

Поддерживаемый изменяющий профиль ограничен: `ansible-core 2.18.x`, firewalld **1.3.4**, backend **nftables**, работающая и включённая служба, RPM-пакеты `firewalld` и `python3-firewall`, доступные Python D-Bus bindings. Для произвольной Ubuntu или другой версии firewalld совместимость применять по аналогии нельзя.

Обычный `apply` требует 64-символьный `host_firewall_plan_id`, набор `host_firewall_verification_checks`, подготовленную собственную policy и recovery-механизм. Перед первой мутацией пересобирается отчёт и проверяется весь выбранный набор узлов. Затем узлы обрабатываются по одному:

1. Проверка нового SSH-соединения и согласованных сервисных endpoint.
2. Снимок runtime/permanent своей policy и контроль чужих объектов.
3. Создание транзакции с локальным сроком автоматического восстановления.
4. Применение в runtime.
5. Повторная проверка нового SSH и endpoint.
6. Запись подтверждённых правил в permanent; при ошибке — откат и остановка дальнейшего прохода.

Проверки сервисов выполняются **с deployment-узла**: TCP connect либо HTTP(S) GET с ожидаемым 2xx. Они не доказывают работоспособность UDP, VRRP, миграции, storage, LDAP bind или пользовательского доступа из другой сети. SSH проверяется с ключом, `StrictHostKeyChecking=yes`, без повторного использования старого соединения; ProxyJump/нестандартные SSH args и парольный SSH этим проверяющим кодом не поддерживаются.

По умолчанию таймер отката — 300 секунд, допустимо 60–900. На управляемом узле используются `/var/lib/kolla-host-firewall`, policy XML и службы watchdog/boot recovery. Это журналы транзакций на целевом узле, а не сохранение диагностического отчёта на controller. Источники: admission (`kolla-ansible-pvs_1.0.0/ansible/action_plugins/kolla_firewall_admission.py`), apply (`kolla-ansible-pvs_1.0.0/ansible/roles/host-firewall/tasks/apply.yml`), проверки (`kolla-ansible-pvs_1.0.0/ansible/module_utils/kolla_firewall_verification.py`), runtime (`kolla-ansible-pvs_1.0.0/ansible/module_utils/kolla_firewall_runtime.py`).

## 6. Ограничения текущего каталога: учесть до restrictive apply

Все 38 записей маркированы `coverage: complete`. Статическое сопоставление с шаблонами выявляет следующие ограничения; это вывод анализа, а не результат испытания отказов на стенде.

| Ограничение | Практическое последствие |
|---|---|
| `keepalived.flows=[]`, компилятор поддерживает только TCP/UDP | Нет разрешения IP protocol 112; при прохождении VRRP через завершающий DROP возможна потеря штатного обмена VIP |
| OVS помечен `non_network`, VXLAN отсутствует | Наличие разрешения Neutron API/9696 не обеспечивает передачу tenant-трафика |
| Все каталожные потоки используют `network: api` | Не представлены отдельные migration/storage/tunnel-сети |
| Libvirt захардкожен на 16509 и api-IP | Варианты TLS/16514 и отдельный migration-IP не покрыты |
| Нет диапазонов QEMU migration и прямых VNC/SPICE-портов | Проверка API может пройти при неработающей миграции или консоли |
| Нет OpenSearch, Dashboards, exporter/9108 и webhook/19890 | Риск нарушить сбор журналов, аудит и интерфейс безопасности |
| Нет Blackbox exporter/9115 | HTTP-проверки endpoints могут перестать выполняться, хотя сами API доступны |
| Поток `prometheus-server` направлен в группу `prometheus-server`, которой нет в штатном `inventory/multinode` | Роль размещает сервер в группе `prometheus`; сопоставление групп нужно исправить/согласовать до расчёта правил |
| Alertmanager cluster — только TCP/9094 | Если используется UDP memberlist/gossip, его нужно добавить в согласованную матрицу |
| VIP-кандидат копирует backend-порт | Не моделируются разные frontend/backend-порты и единый внешний frontend/443 |
| VIP-кандидат формируется на узле, который одновременно входит в destination-group и `loadbalancer` | Раздельные backend и loadbalancer-узлы требуют дополнительной проверки: правила VIP не выводятся из одного факта наличия HAProxy |
| Источники VIP — узлы модели и operator-IP | Произвольные пользовательские сети автоматически не разрешаются |
| Для Nova proxy-потоков нет отдельных условий каждого proxy | Возможны кандидаты для неиспользуемого 6083; SPICE/6082 при этом отсутствует |
| Ironic HTTP разрешается от `ironic` | Не описана полная доставка образов/provisioning к bare metal |
| Значения 8022, 16509, 1984, 61313 и части Consul фиксированы | Переопределение соответствующих портов сервиса не обязательно меняет правила каталога |

`host_firewall_flag_policy=warning` превращает неизвестный включённый `enable_*` в предупреждение. Для аудита использовать `strict`, чтобы неизвестные сервисы становились блокерами. Но `strict` не выявляет пропущенные потоки внутри сервиса, ошибочно помеченного `complete`, и не проверяет отдельно каждый listener. Отсутствие блокеров не заменяет эту таблицу и функциональные проверки.

**Решение для администратора:** использовать `report` для сбора и сверки. Restrictive apply для конкретного облака планировать после устранения применимых пробелов, утверждения полной матрицы и проверки на репрезентативном стенде. Ручное снятие блокеров либо простая замена `coverage` на `complete` не добавляет недостающих правил.

## 7. Проверка фактического состояния без изменения правил

### 7.1. С deployment-узла

Использовать действующее окружение этой ветки и реальный inventory. Не выводить полный `hostvars` в общедоступные журналы: он может содержать секреты.

```bash
kolla-ansible host-firewall --help
ansible --version

kolla-ansible host-firewall -i /path/to/multinode --mode report \
  -e host_firewall_flag_policy=strict
```

Для анализа всех взаимосвязей собирать полный необходимый набор узлов. `--limit` может оставить peer-группы без наблюдённых адресов; такой частичный отчёт не считать полным планом облака.

Проверить `collection_complete`, фактический набор узлов, версии, `blockers`, `warnings`, адреса источников/назначения и каждый candidate flow. `plan_id` идентифицирует модель отчёта, но не доказывает её полноту.

### 7.2. На каждом Linux-узле

```bash
sudo ss -lntup
ip -br address
ip route
ip -6 route

sudo systemctl is-active firewalld
sudo firewall-cmd --version
sudo firewall-cmd --get-active-zones
sudo firewall-cmd --list-all-zones
sudo firewall-cmd --permanent --list-all-zones
sudo firewall-cmd --list-all-policies
sudo firewall-cmd --permanent --list-all-policies

sudo nft -a list ruleset
sudo iptables-save
sudo ip6tables-save
```

Если firewalld не установлен/не запущен, ошибки его команд — результат диагностики, а не причина автоматически его включать. Отдельно проверить policy, если она существует:

```bash
sudo firewall-cmd --info-policy kolla-host-input
sudo firewall-cmd --permanent --info-policy kolla-host-input
sudo systemctl status kolla-host-firewall-watchdog.timer \
  kolla-host-firewall-boot-recovery.service --no-pager
```

`--list-ports` одной zone недостаточно. Нужны runtime и permanent, policy, direct/iptables/nftables и привязки интерфейсов. Их различие означает также возможное изменение поведения после reload/reboot.

### 7.3. Сверить сервисы и datapath

```bash
sudo podman ps --format '{{.Names}} {{.Status}}'
sudo podman exec haproxy sh -c \
  'grep -nE "^[[:space:]]*(bind|server)[[:space:]]" /etc/haproxy/services.d/*.cfg'

sudo podman exec nova_libvirt sh -c \
  'grep -E "^(listen_|tcp_port|tls_port)" /etc/libvirt/libvirtd.conf'

sudo ip netns list
```

Команды выполнять только на узлах с соответствующими контейнерами; имена и пути подтвердить по развёрнутой версии. Для консолей/миграции дополнительно изучить текущие `qemu.conf`, Nova config и domain XML, для Neutron — namespaces, OVS/OVN и правила нужных портов ВМ.

Под административным профилем OpenStack:

```bash
openstack endpoint list
openstack network agent list
openstack compute service list
openstack security group rule list <SECURITY_GROUP_ID>
```

### 7.4. Проверить доступ с правильных источников

Для каждой согласованной строки матрицы выполнить TCP/TLS/HTTP-проверку из разрешённой сети и отрицательную проверку из сети, которой доступ запрещён. Например, на проверяющем Linux-узле:

```bash
nc -vz -w 3 <VIP_OR_HOST> <TCP_PORT>
curl --connect-timeout 3 --max-time 10 \
  --cacert /path/to/api-ca.pem https://<API_FQDN>:<PORT>/v3
```

HTTP-путь подбирается для сервиса. Ответ `401/403` подтверждает достижимость HTTP, но не нужные права. Timeout сам по себе не доказывает DROP; сопоставить маршрут, listener, counters и, при необходимости, согласованный packet capture. UDP/VRRP проверять протокольными средствами, а не TCP `nc`.

Результат фиксировать в отдельном эксплуатационном журнале:

| Источник/IP | Назначение/IP | Протокол/порт | Назначение потока | Ожидается | Наблюдение и дата |
|---|---|---|---|---|---|
| Bastion | Узел управления | TCP/SSH | Администрирование | Разрешён | Заполнить |
| Недоверенная сеть | Узел управления | TCP/SSH | Негативная проверка | Запрещён внешним ACL | Заполнить |
| Клиентская сеть | VIP Keystone | TCP/публичный порт | Аутентификация | Разрешён | Заполнить |
| Клиентская сеть | MariaDB | TCP/3306 | Негативная проверка | Запрещён | Заполнить |
| Keystone | DC | TCP/636 | LDAPS | Разрешён | Заполнить |

## 8. Порядок изменения и восстановления

Это описание существующего интерфейса, **не указание немедленно применять каталог из архива**. Сначала устранить применимые ограничения раздела 6. До изменения иметь рабочую независимую консоль, проверенный SSH-ключ и known_hosts, согласованную матрицу и возможность проверить межузловые/пользовательские сценарии.

Подготовка собственной policy выполняется отдельной операцией и может вызвать firewalld reload. Она требует явных YAML boolean и проходит проверки чужих правил; не выполняет установку firewalld:

```bash
kolla-ansible host-firewall -i /path/to/multinode --mode apply \
  -e '{"host_firewall_initialize": true, "host_firewall_allow_initial_reload": true}'
```

После подготовки повторить `report` с теми же переменными, которые будут использоваться для apply, и проверить новый `plan_id`. Пример структуры отдельного файла параметров `/path/to/host-firewall-apply.yml`:

```yaml
host_firewall_flag_policy: strict
host_firewall_plan_id: "REPLACE_WITH_64_HEX_PLAN_ID_FROM_FRESH_REPORT"
host_firewall_rollback_timeout: 300
host_firewall_operator_sources:
  - "192.0.2.10"  # Заменить на фактический IP deployment, без CIDR.
host_firewall_verification_checks:
  - id: keystone-api
    type: http
    url: "https://identity.example.org:5000/v3"
    status: 200
  - id: horizon
    type: tcp
    host: "192.0.2.20"  # Фактический VIP, TCP-проверка требует IP.
    port: 443
```

IP, URL, статус и проверки в примере — заполнители. HTTP-проверка должна реально возвращать выбранный 2xx; redirect не считается им. HTTPS использует доверие deployment-узла. Список поддерживает 1–16 проверок; проверку нового SSH добавляет код. Этот минимум не проверяет все сервисы облака.

```bash
kolla-ansible host-firewall -i /path/to/multinode --mode apply \
  -e @/path/to/host-firewall-apply.yml
```

При `FRESH_REPORT_MISMATCH` заново получить и изучить отчёт; не обходить сравнение. При `REPORT_HAS_BLOCKERS` устранить причины. `host_firewall_plan_file` не поддерживается. `--check` не выполняет полноценную проверку живого firewall, SSH и приложений.

Сохранить выведенный `transaction=<UUID>` для каждого узла. Для явного отката выбрать именно этот узел и его транзакцию:

```bash
kolla-ansible host-firewall -i /path/to/multinode --mode rollback \
  --limit <INVENTORY_HOST> \
  -e host_firewall_rollback_transaction_id=<TRANSACTION_UUID>
```

Откат восстанавливает снимки собственной runtime/permanent policy. Он не является общим восстановлением чужих firewall, Neutron или внешнего сетевого оборудования. Даже после успешных встроенных проверок отдельно подтвердить доступ из клиентской сети, работу ВМ, VRRP, storage, миграции, аудита и AD в согласованном испытании.

## 9. Полный перечень потоков исходного host-каталога

Таблица ниже воспроизводит **все 66 потоков**, а не полный список потребностей OpenStack. Поток действует только при включении своего сервиса; для API могут дополнительно требоваться HAProxy и другие условия. Значение `port_var` берётся из эффективных переменных; фиксированные числа не переопределяются через переменную сервиса. Источники показаны до добавления operator-IP и VIP-кандидатов.

| ID потока | Протокол | Порт / port_var | Источники → назначение |
|---|---|---|---|
| `keystone-internal-backend` | TCP | `keystone_internal_listen_port` | `loadbalancer` → `keystone` |
| `keystone-public-backend` | TCP | `keystone_public_listen_port` | `loadbalancer` → `keystone` |
| `keystone-fernet-ssh` | TCP | `keystone_ssh_port` | `keystone` → `keystone` |
| `glance-api-backend` | TCP | `glance_api_listen_port` | `loadbalancer` → `glance-api` |
| `cinder-api-backend` | TCP | `cinder_api_listen_port` | `loadbalancer` → `cinder-api` |
| `nova-api-backend` | TCP | `nova_api_listen_port` | `loadbalancer` → `nova-api` |
| `nova-metadata-backend` | TCP | `nova_metadata_listen_port` | `loadbalancer` → `nova-metadata` |
| `nova-novncproxy-backend` | TCP | `nova_novncproxy_listen_port` | `loadbalancer` → `nova-novncproxy` |
| `nova-serialproxy-backend` | TCP | `nova_serialproxy_listen_port` | `loadbalancer` → `nova-serialproxy` |
| `neutron-server-backend` | TCP | `neutron_server_listen_port` | `loadbalancer` → `neutron-server` |
| `placement-api-backend` | TCP | `placement_api_listen_port` | `loadbalancer` → `placement-api` |
| `horizon-backend` | TCP | `horizon_listen_port` | `loadbalancer` → `horizon` |
| `watcher-api-backend` | TCP | `watcher_api_listen_port` | `loadbalancer` → `watcher-api` |
| `masakari-api-backend` | TCP | `masakari_api_listen_port` | `loadbalancer` → `masakari-api` |
| `mistral-api-backend` | TCP | `mistral_api_listen_port` | `loadbalancer` → `mistral-api` |
| `ironic-api-backend` | TCP | `ironic_api_listen_port` | `loadbalancer` → `ironic-api` |
| `ironic-http` | TCP | `ironic_http_port` | `ironic` → `ironic` |
| `mariadb-client` | TCP | `mariadb_port` | `common` → `mariadb` |
| `mariadb-galera-wsrep` | TCP | `mariadb_wsrep_port` | `mariadb` → `mariadb` |
| `mariadb-galera-ist` | TCP | `mariadb_ist_port` | `mariadb` → `mariadb` |
| `mariadb-galera-sst` | TCP | `mariadb_sst_port` | `mariadb` → `mariadb` |
| `rabbitmq-amqp` | TCP | `rabbitmq_port` | `common` → `rabbitmq` |
| `rabbitmq-epmd` | TCP | `rabbitmq_epmd_port` | `control` → `rabbitmq` |
| `rabbitmq-cluster` | TCP | `rabbitmq_cluster_port` | `control` → `rabbitmq` |
| `rabbitmq-management` | TCP | `rabbitmq_management_port` | `loadbalancer` → `rabbitmq` |
| `memcached-client` | TCP | `memcached_port` | `common` → `memcached` |
| `etcd-client` | TCP | `etcd_client_port` | `control` → `etcd` |
| `etcd-peer` | TCP | `etcd_peer_port` | `control` → `etcd` |
| `consul-http-server` | TCP | `consul_http_port` | `common` → `consul-server` |
| `consul-serf-server` | TCP | `consul_serf_lan_port` | `common` → `consul-server` |
| `consul-serf-server-udp` | UDP | `consul_serf_lan_port` | `common` → `consul-server` |
| `consul-server-rpc` | TCP | `8300` | `common` → `consul-server` |
| `consul-serf-wan` | TCP | `8302` | `control` → `consul-server` |
| `consul-serf-wan-udp` | UDP | `8302` | `control` → `consul-server` |
| `consul-dns` | TCP | `8600` | `common` → `consul-server` |
| `consul-dns-udp` | UDP | `8600` | `common` → `consul-server` |
| `consul-http-agent` | TCP | `consul_http_port` | `common` → `consul-agent` |
| `consul-serf-agent` | TCP | `consul_serf_lan_port` | `common` → `consul-agent` |
| `consul-serf-agent-udp` | UDP | `consul_serf_lan_port` | `common` → `consul-agent` |
| `consul-dns-agent` | TCP | `8600` | `common` → `consul-agent` |
| `consul-dns-agent-udp` | UDP | `8600` | `common` → `consul-agent` |
| `proxysql-admin` | TCP | `proxysql_admin_port` | `common` → `control` |
| `proxysql-mysql` | TCP | `database_port` | `loadbalancer` → `control` |
| `nova-libvirt-control` | TCP | `16509` | `control`, `compute` → `compute` |
| `nova-ssh-migration` | TCP | `8022` | `compute` → `compute` |
| `iscsi-target` | TCP | `iscsi_port` | `compute`, `control` → `storage` |
| `corosync` | UDP | `hacluster_corosync_port` | `hacluster` → `hacluster` |
| `pacemaker-remote` | TCP | `3121` | `hacluster` → `hacluster-remote` |
| `haproxy-stats` | TCP | `1984` | `monitoring` → `loadbalancer` |
| `haproxy-monitor` | TCP | `61313` | `monitoring` → `loadbalancer` |
| `fluentd-syslog` | UDP | `fluentd_syslog_port` | `common` → `common` |
| `prometheus-server` | TCP | `prometheus_listen_port` | `monitoring` → `prometheus-server` |
| `alertmanager-http` | TCP | `prometheus_alertmanager_listen_port` | `monitoring`, `loadbalancer` → `prometheus-alertmanager` |
| `alertmanager-cluster` | TCP | `prometheus_alertmanager_cluster_port` | `monitoring` → `prometheus-alertmanager` |
| `grafana-http` | TCP | `grafana_server_listen_port` | `loadbalancer`, `monitoring` → `grafana` |
| `node-exporter` | TCP | `prometheus_node_exporter_port` | `monitoring` → `prometheus-node-exporter` |
| `mysqld-exporter` | TCP | `prometheus_mysqld_exporter_port` | `monitoring` → `prometheus-mysqld-exporter` |
| `memcached-exporter` | TCP | `prometheus_memcached_exporter_port` | `monitoring` → `prometheus-memcached-exporter` |
| `libvirt-exporter` | TCP | `prometheus_libvirt_exporter_port` | `monitoring` → `prometheus-libvirt-exporter` |
| `cadvisor` | TCP | `prometheus_cadvisor_port` | `monitoring` → `prometheus-cadvisor` |
| `openstack-exporter` | TCP | `prometheus_openstack_exporter_port` | `monitoring`, `loadbalancer` → `prometheus-openstack-exporter` |
| `haproxy-exporter` | TCP | `prometheus_haproxy_exporter_port` | `monitoring` → `loadbalancer` |
| `rabbitmq-exporter` | TCP | `prometheus_rabbitmq_exporter_port` | `monitoring` → `rabbitmq` |
| `proxysql-exporter` | TCP | `proxysql_prometheus_exporter_port` | `monitoring` → `control` |
| `fluentd-prometheus` | TCP | `prometheus_fluentd_integration_port` | `monitoring` → `common` |
| `ironic-exporter` | TCP | `ironic_prometheus_exporter_port` | `monitoring` → `ironic` |

## 10. Источники и проверяемость

- Основные defaults (`kolla-ansible-pvs_1.0.0/ansible/group_vars/all.yml`), inventory-пример (`kolla-ansible-pvs_1.0.0/ansible/inventory/multinode`).
- Defaults host-firewall (`kolla-ansible-pvs_1.0.0/ansible/roles/host-firewall/defaults/main.yml`), каталог потоков (`kolla-ansible-pvs_1.0.0/ansible/roles/host-firewall/vars/catalog.yml`).
- Playbook (`kolla-ansible-pvs_1.0.0/ansible/host-firewall.yml`), модель (`kolla-ansible-pvs_1.0.0/ansible/module_utils/kolla_firewall_model.py`), правила (`kolla-ansible-pvs_1.0.0/ansible/module_utils/kolla_firewall_plan.py`), адаптер firewalld (`kolla-ansible-pvs_1.0.0/ansible/module_utils/kolla_firewall_firewalld.py`).
- Подготовка policy/recovery (`kolla-ansible-pvs_1.0.0/ansible/roles/host-firewall/tasks/prepare.yml`), транзакции (`kolla-ansible-pvs_1.0.0/ansible/module_utils/kolla_firewall_transaction.py`), проверки (`kolla-ansible-pvs_1.0.0/ansible/module_utils/kolla_firewall_verification.py`).

SHA-256 архивов:

```text
kolla-ansible: e68e98cb5ce6d2384ebf90c4ff1e6a9b779efe986ae11a83bc8cb1b556bfe004
masakari:      cf40ec62cdde2795499e7e46e6f5599fe9beb90b07c16c8a988f28d436469156
watcher:       67722deaa94b4e606620519c34a3db84f3253c492e7238f78bf0045a65c2ac0b
```

Для утверждения фактической матрицы «открыто/закрыто» к этому документу нужны результаты раздела 7 по конкретному inventory. Архивы подтверждают алгоритм и defaults; они не содержат доказательства текущего состояния работающего облака.
