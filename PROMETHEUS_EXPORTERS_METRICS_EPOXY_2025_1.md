# Метрики Prometheus exporters — OpenStack Epoxy 2025.1

Справочник по архивам из текущей папки и ванильным exporters, выбранным Kolla `stable/2025.1`.

Дата проверки: **22 сентября 2026 года**. Язык пояснений — русский; имена метрик и labels сохранены без переименования.

## Область действия и полнота

**В документе описаны метрики exporters и интеграций, упомянутых в приложенных архивах.** Основные таблицы дают назначение, тип, единицу измерения и атрибуты. В конце приведены расширенные каталоги из эталонных исходников/fixtures и указаны расхождения архивных правил с vanilla.

Это **статический справочник**, а не выгрузка работающего Prometheus. Архивы содержат Kolla-конфигурацию, rules и dashboards, но не ответы `/metrics`. Включение job не означает, что каждый возможный collector активен и каждая метрика присутствует. Для Node, MySQL, Ceph, Ironic и textfile конечный набор зависит также от версии ядра, полей API, оборудования, прав и параметров запуска. Поэтому по одним архивам нельзя честно заявить полный фактический список рядов стенда; способ его проверки приведён в конце.

В основной перечень включены все имена и шаблоны имён из незакомментированных выражений rules и запросов двух поставленных dashboards. Имена recording rules сохранены целиком, включая двоеточия. Закомментированные старые правила не считаются включённым сбором. Для exporters, не используемых непосредственно в этих запросах, приведены справочные метрики и расширенные каталоги, где их можно получить из зафиксированного источника.

| Обозначение | Что подтверждено |
|---|---|
| А | Имя используется архивным правилом или запросом дашборда. Это подтверждение зависимости, а не наличия в exporter. |
| В / А+В | Имя и схема проверены по выбранной vanilla-версии; А+В также означает наличие ссылки в архиве. |
| С | Справочное семейство для native/условной интеграции. Версия пакета или внешнего сервиса не зафиксирована одним номером Epoxy; сверить с /metrics. |
| Р | Recording rule: вычисляемый Prometheus ряд, не исходная метрика exporter. |
| Н | Отсутствующее определение, несовместимое/устаревшее имя либо опечатка. |
| А, внешний | Имя ожидается PVS-rules, но соответствующий внешний exporter не поставляется штатной ролью Kolla из архивов. |

Тип и размерность разделены: `gauge`, `counter`, `histogram`, `summary`, `untyped` — типы, а байты, секунды, проценты и количество — единицы. Тип взят из кода/экспозиции, когда он доступен. Суффикс `_total` сам по себе не доказывает TYPE=counter: в конкретных версиях встречаются gauge и untyped с накопительным смыслом.

В столбце атрибутов указаны основные **labels метрики**. Prometheus дополнительно присоединяет `job`, `instance` и target labels. `region`, `instance_hostname`, `sm_ci`, а в отдельных конфигурациях `fqdn` и `resource`, могут добавляться конфигурацией сбора/перемаркировкой. Их наличие не следует автоматически приписывать exporter. `—` означает отсутствие специфичных labels в описанной схеме, а не отсутствие `job`/`instance` в TSDB.

Для классической histogram имя семейства раскрывается в `_bucket{le=...}`, `_sum`, `_count`; summary — в ряды с `quantile` и `_sum`/`_count`. В таблицах такие семейства не размножены вручную. `rate()` и `increase()` применяют к накопительным показателям с учётом сбросов; состояния и информационные метрики ими не обрабатывают.

## Проверенные архивы и версии

| Архив | Коммит из ZIP comment | Роль в справочнике |
|---|---|---|
| kolla-ansible-enroll-ironic-patch-3.zip | `5db3c8eed90d69a85e3761ff7f55cb72d7fde94f` | Конфигурации, правила, dashboards |
| kolla-ansible-pvs_1.0.0_21.09zip.zip | `365af98421ff35db2e9ca5ee605723a1bcc8e756` | Конфигурации, правила, dashboards |
| masakari-pvs_1.0.0_21.09.zip | `702480386d63c935a6f1b143fbd65f54dba63f52` | Собственного Prometheus exporter не найдено |
| watcher-pvs_1.0.0_21.09.zip | `96eeba4c5b8ce30f29fd7d6461bdac28fdfdfa4d` | Потребитель метрик; собственного exporter не найдено |

У двух Kolla-архивов содержимое 18 PVS-файлов правил, двух dashboards и двух шаблонов `*.rules.j2` совпадает. В PVS scrape-шаблоне архив `kolla-ansible-pvs_1.0.0_21.09zip.zip` содержит 24 объявления jobs, а `kolla-ansible-enroll-ironic-patch-3.zip` — 23: в новом удалён `bird_exporter`. Это число объявлений, а не число реально работающих targets.

Версии ниже получены из [официального Kolla sources.py, stable/2025.1, зафиксированный commit](https://github.com/openstack/kolla/blob/d14cef9bbafa0db561abfb0c0299d1d6bbbf8f0c/kolla/common/sources.py). Это выбранная эталонная сборка ветки; ранний образ той же ветки или образ с override может отличаться.

| Компонент | Версия эталонной Kolla | Реализация |
|---|---|---|
| Node exporter | 1.8.2 | prometheus/node_exporter |
| OpenStack exporter | 1.7.0 | openstack-exporter/openstack-exporter |
| Libvirt exporter | 2.2.0 | inovex/prometheus-libvirt-exporter |
| mysqld_exporter | 0.16.0 | prometheus/mysqld_exporter |
| Memcached exporter | 0.15.0 | prometheus/memcached_exporter |
| Blackbox exporter | 0.25.0 | prometheus/blackbox_exporter |
| cAdvisor | 0.49.2 | google/cadvisor |
| Elasticsearch exporter | 1.8.0 | prometheus-community/elasticsearch_exporter |
| Prometheus server | 3.2.1 | prometheus/prometheus |
| Alertmanager | 0.28.1 | prometheus/alertmanager |
| Ironic Prometheus exporter | stable/2025.1 | openstack/ironic-prometheus-exporter |
| HAProxy, RabbitMQ, etcd, ProxySQL, Fluentd | Зависят от пакетов/образов | Native endpoints или plugins; это не версии отдельных Go exporters из таблицы выше |
| Ceph mgr | Версия внешнего Ceph | Внешняя интеграция, выключена в defaults |

## Источники сбора в архивах

Источник таблицы: PVS scrape-шаблон — `ansible/alerts/prometheus/templates/prometheus.yml.j2`, defaults роли — `ansible/roles/prometheus/defaults/main.yml`, общие переменные — `ansible/group_vars/all.yml`.

| Job | Что наблюдает | Условие / особенность |
|---|---|---|
| node | ОС, CPU, RAM, сеть, диски | Collectors зависят от ОС и флагов; systemd/processes/tcpstat не включаются наличием панели. |
| libvirt_exporter | ВМ со стороны libvirt | Данные памяти гостя зависят от balloon/драйвера; не мониторинг приложений внутри ВМ. |
| openstack_exporter | Ресурсы и состояния через OpenStack API | API-права и доступные сервисы определяют набор; Cinder/Designate/Octavia collectors отключаются без соответствующих сервисов. |
| mysqld | MariaDB/MySQL, Galera | Динамические поля SHOW GLOBAL STATUS и выбранные collectors. |
| haproxy | Балансировщик | В архиве native `http-request use-service prometheus-exporter`, не отдельный legacy haproxy_exporter. |
| rabbitmq_internal; rabbitmq | RabbitMQ | Оба объявления используют native endpoint; второй job условный и способен дублировать сбор. |
| memcached | Кэш | Показатели Memcached и slabs по конфигурации exporter. |
| cadvisor | Контейнеры | В defaults --docker_only; отключены percpu, referenced_memory, cpu_topology, resctrl, udp, advtcp, sched, hugetlb, memory_numa, tcp, process. |
| fluentd | Обработка журналов | prometheus_output_monitor; прикладные log counters требуют отдельных фильтров. |
| blackbox_exporter; blackbox_exporter_service_check | Доступность endpoints | Метрики `/probe`, результат проверки в probe_success. |
| elasticsearch_exporter | OpenSearch | В архиве историческое имя Elasticsearch exporter. |
| etcd | Координация/Raft | Native metrics при включённой интеграции. |
| ironic_prometheus_exporter | Датчики bare metal | Сенсорные сообщения Ironic; интервал отправки задан отдельно от scrape. |
| ceph_mgr_exporter | Внешний Ceph | Endpoints задаются отдельно; disabled по умолчанию. |
| prometheus; alertmanager | Сам мониторинг | Собственные метрики серверов, а не состояния OpenStack API. |
| proxysql | Прокси СУБД | Native endpoint; в PVS-шаблоне job дополнительно вложен в условие Alertmanager. |
| ovs_exporter; consul_exporter; multipath_exporter | Внешние расширения | Есть условные jobs/rules, но нет полного штатного описания развёртывания в prometheus_services. |
| hypervisor_exporter | Неопределённое внешнее расширение | Job есть, реализация и контракт метрик в архиве отсутствуют. |
| bird_exporter | BIRD, только старый архив | В patch-3 job удалён; полного vanilla deployment в архиве нет. |

**ProxySQL, hypervisor и BIRD:** по имеющимся архивам нет зафиксированной схемы их метрик. Не подставляется каталог случайного одноимённого exporter. Для ProxySQL подтверждена конфигурация native listener, для двух остальных — только условные jobs. OVS/Consul/multipath ниже описаны как зависимости PVS, а не часть поставки vanilla Kolla.

**Отдельные Masakari/Mistral/Watcher exporters не обнаружены.** Watcher читает Prometheus; `ceilometer_cpu` и `ceilometer_memory_usage` в этих архивах создаются recording rules. Проверка API через Blackbox даёт `probe_*`, а не произвольные внутренние метрики OpenStack-службы.

## Содержание таблиц

- [Узел: CPU и планировщик](#s1)

- [Узел: память и swap](#s2)

- [Узел: диски и файловые системы](#s3)

- [Узел: сетевые интерфейсы](#s4)

- [Узел: TCP/IP и сокеты](#s5)

- [Узел: оборудование](#s6)

- [Узел: время](#s7)

- [Узел: процессы и exporter](#s8)

- [Libvirt: ВМ](#s9)

- [OpenStack: API и ресурсы](#s10)

- [MariaDB / MySQL и Galera](#s11)

- [HAProxy](#s12)

- [RabbitMQ](#s13)

- [Blackbox: проверки доступности](#s14)

- [Consul](#s15)

- [Open vSwitch](#s16)

- [Multipath](#s17)

- [Общие: процесс и сбор](#s18)

- [Prometheus и Alertmanager](#s19)

- [cAdvisor: контейнеры](#s20)

- [Memcached](#s21)

- [Fluentd](#s22)

- [Elasticsearch exporter для OpenSearch](#s23)

- [etcd](#s24)

- [Ceph mgr](#s25)

- [Ironic: датчики bare metal](#s26)

- [Вычисляемые метрики: определения есть](#s27)

- [Несовместимые зависимости архивов](#s28)

- [Зависимости дашборда: определения отсутствуют](#s29)

- [Ошибочное имя](#s30)

- [Расширенные каталоги из эталонных источников](#reference-catalogs)
- [Ограничения совместимости и динамические семейства](#compatibility)
- [Как получить полный фактический каталог](#runtime-catalog)
- [Источники и контрольные суммы](#sources)

<a id="s1"></a>

## Узел: CPU и планировщик

Источник схемы: Node exporter 1.8.2. Временные счётчики CPU измеряются в CPU-секундах, load average — числом задач.

| Название | Описание | Тип | Единица | Основные атрибуты | Основание |
|---|---|---|---|---|---|
| `node_context_switches_total` | Переключения контекста на всём узле с момента загрузки. | counter | переключения | — | А+В |
| `node_cpu_core_throttles_total` | Количество ограничений частоты ядра из-за перегрева. | counter | события | core, package | А+В |
| `node_cpu_guest_seconds_total` | Время CPU на выполнение гостевых систем; учитывается также в соответствующих режимах основного CPU-счётчика. | counter | с | cpu, mode | А+В |
| `node_cpu_scaling_frequency_hertz` | Текущая частота по интерфейсу cpufreq ядра. | gauge | Гц | cpu | А+В |
| `node_cpu_scaling_frequency_max_hertz` | Верхняя граница частоты, разрешённая политикой cpufreq. | gauge | Гц | cpu | А+В |
| `node_cpu_scaling_frequency_min_hertz` | Нижняя граница частоты, разрешённая политикой cpufreq. | gauge | Гц | cpu | А+В |
| `node_cpu_scaling_governor` | Выбранная политика частоты: 1 для активного governor. | gauge | 0/1 | cpu, governor | А+В |
| `node_cpu_seconds_total` | Суммарное время CPU в каждом режиме. Скорость прироста показывает долю времени CPU. | counter | с | cpu, mode | А+В |
| `node_interrupts_total` | Прерывания по CPU и источнику; нужен collector interrupts. | counter | прерывания | cpu, devices, info, type | А+В |
| `node_intr_total` | Суммарное число обработанных прерываний. | counter | прерывания | — | А+В |
| `node_load1` | Среднее число выполняемых или ожидающих CPU / непрерываемый I/O задач за 1 мин. Не процент загрузки CPU. | gauge | задачи | — | А+В |
| `node_load15` | Среднее число выполняемых или ожидающих CPU / непрерываемый I/O задач за 15 мин. Не процент загрузки CPU. | gauge | задачи | — | А+В |
| `node_load5` | Среднее число выполняемых или ожидающих CPU / непрерываемый I/O задач за 5 мин. Не процент загрузки CPU. | gauge | задачи | — | А+В |
| `node_pressure_cpu_waiting_seconds_total` | PSI: суммарное время давления ресурса CPU; задержана хотя бы одна задача (some). | counter | с | — | А+В |
| `node_pressure_io_stalled_seconds_total` | PSI: суммарное время давления ресурса ввода-вывода; полная остановка соответствующей работы (full); зависит от поддержки ядром. | counter | с | — | А+В |
| `node_pressure_io_waiting_seconds_total` | PSI: суммарное время давления ресурса ввода-вывода; задержана хотя бы одна задача (some). | counter | с | — | А+В |
| `node_pressure_memory_stalled_seconds_total` | PSI: суммарное время давления ресурса памяти; полная остановка соответствующей работы (full); зависит от поддержки ядром. | counter | с | — | А+В |
| `node_pressure_memory_waiting_seconds_total` | PSI: суммарное время давления ресурса памяти; задержана хотя бы одна задача (some). | counter | с | — | А+В |
| `node_schedstat_running_seconds_total` | Время выполнения задач на CPU по данным schedstat. | counter | с | cpu | А+В |
| `node_schedstat_timeslices_total` | Количество выделенных задачам квантов CPU. | counter | кванты | cpu | А+В |
| `node_schedstat_waiting_seconds_total` | Суммарное время ожидания задач в очереди CPU. | counter | с | cpu | А+В |

<a id="s2"></a>

## Узел: память и swap

Источник — meminfo/vmstat collectors Node exporter 1.8.2. Поля зависят от версии Linux; единица HugePages — страницы, а не байты. Vmstat передаётся как untyped.

| Название | Описание | Тип | Единица | Основные атрибуты | Основание |
|---|---|---|---|---|---|
| `node_memory_Active_anon_bytes` | Активная анонимная память. | gauge | байты | — | А+В |
| `node_memory_Active_bytes` | Активно используемые страницы памяти. | gauge | байты | — | А+В |
| `node_memory_Active_file_bytes` | Активные страницы файлового кэша. | gauge | байты | — | А+В |
| `node_memory_AnonHugePages_bytes` | Анонимная память в transparent huge pages. | gauge | байты | — | А+В |
| `node_memory_AnonPages_bytes` | Анонимные страницы пользовательских процессов. | gauge | байты | — | А+В |
| `node_memory_Bounce_bytes` | Память промежуточных DMA bounce-буферов. | gauge | байты | — | А+В |
| `node_memory_Buffers_bytes` | Буферы метаданных и блочных операций ядра. | gauge | байты | — | А+В |
| `node_memory_Cached_bytes` | Файловый кэш, включая tmpfs/shmem; без SwapCached. | gauge | байты | — | А+В |
| `node_memory_CommitLimit_bytes` | Лимит резервирования виртуальной памяти при действующей политике overcommit. | gauge | байты | — | А+В |
| `node_memory_Committed_AS_bytes` | Объём виртуальной памяти, зарезервированной приложениями. | gauge | байты | — | А+В |
| `node_memory_DirectMap1G_bytes` | Память прямого отображения ядра страницами 1 GiB. | gauge | байты | — | А+В |
| `node_memory_DirectMap2M_bytes` | Память прямого отображения ядра страницами 2 MiB. | gauge | байты | — | А+В |
| `node_memory_DirectMap4k_bytes` | Память прямого отображения ядра страницами 4 KiB. | gauge | байты | — | А+В |
| `node_memory_Dirty_bytes` | Изменённые страницы, ещё не записанные на накопитель. | gauge | байты | — | А+В |
| `node_memory_HardwareCorrupted_bytes` | Память, исключённая из использования из-за аппаратных ошибок. | gauge | байты | — | А+В |
| `node_memory_HugePages_Free` | Свободные HugeTLB-страницы. | gauge | страницы | — | А+В |
| `node_memory_HugePages_Rsvd` | Зарезервированные, но ещё не выделенные HugeTLB-страницы. | gauge | страницы | — | А+В |
| `node_memory_HugePages_Surp` | HugeTLB-страницы сверх настроенного постоянного пула. | gauge | страницы | — | А+В |
| `node_memory_HugePages_Total` | Размер пула HugeTLB в страницах. | gauge | страницы | — | А+В |
| `node_memory_Hugepagesize_bytes` | Размер одной обычной HugeTLB-страницы. | gauge | байты | — | А+В |
| `node_memory_Inactive_anon_bytes` | Неактивная анонимная память. | gauge | байты | — | А+В |
| `node_memory_Inactive_bytes` | Неактивные страницы памяти. | gauge | байты | — | А+В |
| `node_memory_Inactive_file_bytes` | Неактивные страницы файлового кэша. | gauge | байты | — | А+В |
| `node_memory_KernelStack_bytes` | Память стеков ядра. | gauge | байты | — | А+В |
| `node_memory_Mapped_bytes` | Файлы, отображённые в адресные пространства процессов. | gauge | байты | — | А+В |
| `node_memory_MemAvailable_bytes` | Оценка памяти, доступной новым приложениям без swap; включает освобождаемый кэш. | gauge | байты | — | А+В |
| `node_memory_MemFree_bytes` | Полностью свободная RAM без учёта освобождаемого кэша. | gauge | байты | — | А+В |
| `node_memory_MemTotal_bytes` | RAM, доступная операционной системе. | gauge | байты | — | А+В |
| `node_memory_Mlocked_bytes` | Страницы, зафиксированные в RAM через mlock. | gauge | байты | — | А+В |
| `node_memory_NFS_Unstable_bytes` | Данные NFS, ожидающие подтверждённой записи; поле зависит от ядра. | gauge | байты | — | А+В |
| `node_memory_PageTables_bytes` | Память таблиц страниц. | gauge | байты | — | А+В |
| `node_memory_Percpu_bytes` | Память структур ядра, выделенных отдельно для каждого CPU. | gauge | байты | — | А+В |
| `node_memory_SReclaimable_bytes` | Часть slab, которую ядро может освободить. | gauge | байты | — | А+В |
| `node_memory_SUnreclaim_bytes` | Часть slab, которую ядро не может освободить при давлении памяти. | gauge | байты | — | А+В |
| `node_memory_ShmemHugePages_bytes` | Shared memory / tmpfs, размещённая в huge pages. | gauge | байты | — | А+В |
| `node_memory_ShmemPmdMapped_bytes` | Shared memory, отображённая через PMD huge pages. | gauge | байты | — | А+В |
| `node_memory_Shmem_bytes` | Общая память, включая tmpfs. | gauge | байты | — | А+В |
| `node_memory_Slab_bytes` | Память кэшей объектов ядра. | gauge | байты | — | А+В |
| `node_memory_SwapCached_bytes` | RAM страниц, копии которых ещё присутствуют в swap. | gauge | байты | — | А+В |
| `node_memory_SwapFree_bytes` | Свободный объём swap. | gauge | байты | — | А+В |
| `node_memory_SwapTotal_bytes` | Полный объём swap. | gauge | байты | — | А+В |
| `node_memory_Unevictable_bytes` | Страницы, которые нельзя вытеснить из RAM. | gauge | байты | — | А+В |
| `node_memory_VmallocChunk_bytes` | Размер крупнейшего свободного участка vmalloc; на новых ядрах может быть 0. | gauge | байты | — | А+В |
| `node_memory_VmallocTotal_bytes` | Размер виртуальной области vmalloc; это не объём физической RAM. | gauge | байты | — | А+В |
| `node_memory_VmallocUsed_bytes` | Занятая часть области vmalloc. | gauge | байты | — | А+В |
| `node_memory_WritebackTmp_bytes` | Временные буферы записи, в частности FUSE. | gauge | байты | — | А+В |
| `node_memory_Writeback_bytes` | Страницы, которые прямо сейчас записываются на накопитель. | gauge | байты | — | А+В |
| `node_vmstat_oom_kill` | Процессы, завершённые OOM killer. | untyped | события | — | А+В |
| `node_vmstat_pgfault` | Все page faults, включая minor. | untyped | события | — | А+В |
| `node_vmstat_pgmajfault` | Major page faults, потребовавшие загрузки данных. | untyped | события | — | А+В |
| `node_vmstat_pgpgin` | Объём ввода страниц с блочных устройств по счётчику ядра. | untyped | KiB | — | А+В |
| `node_vmstat_pgpgout` | Объём вывода страниц на блочные устройства по счётчику ядра. | untyped | KiB | — | А+В |
| `node_vmstat_pswpin` | Страницы, считанные из swap. | untyped | страницы | — | А+В |
| `node_vmstat_pswpout` | Страницы, записанные в swap. | untyped | страницы | — | А+В |

<a id="s3"></a>

## Узел: диски и файловые системы

| Название | Описание | Тип | Единица | Основные атрибуты | Основание |
|---|---|---|---|---|---|
| `node_disk_discard_time_seconds_total` | Суммарное время discard-запросов. | counter | с | device | А+В |
| `node_disk_discarded_sectors_total` | Отброшенные секторы по diskstats; для Linux счётчик в 512-байтных секторах. | counter | секторы | device | А+В |
| `node_disk_discards_completed_total` | Завершённые discard/TRIM-запросы. | counter | операции | device | А+В |
| `node_disk_discards_merged_total` | Объединённые discard-запросы. | counter | операции | device | А+В |
| `node_disk_flush_requests_time_seconds_total` | Суммарное время flush-запросов. | counter | с | device | А+В |
| `node_disk_flush_requests_total` | Завершённые запросы сброса кэша устройства. | counter | операции | device | А+В |
| `node_disk_io_now` | Количество операций I/O, выполняющихся в момент сбора. | gauge | операции | device | А+В |
| `node_disk_io_time_seconds_total` | Время, в течение которого устройство имело незавершённый I/O. | counter | с | device | А+В |
| `node_disk_io_time_weighted_seconds_total` | Время I/O, взвешенное числом незавершённых запросов. | counter | с | device | А+В |
| `node_disk_read_bytes_total` | Объём данных, прочитанных с блочного устройства. | counter | байты | device | А+В |
| `node_disk_read_time_seconds_total` | Сумма времени операций чтения; учитывает параллельные операции. | counter | с | device | А+В |
| `node_disk_reads_completed_total` | Завершённые операции чтения. | counter | операции | device | А+В |
| `node_disk_reads_merged_total` | Запросы чтения, объединённые блочным слоем. | counter | операции | device | А+В |
| `node_disk_write_time_seconds_total` | Сумма времени операций записи. | counter | с | device | А+В |
| `node_disk_writes_completed_total` | Завершённые операции записи. | counter | операции | device | А+В |
| `node_disk_writes_merged_total` | Запросы записи, объединённые блочным слоем. | counter | операции | device | А+В |
| `node_disk_written_bytes_total` | Объём данных, записанных на блочное устройство. | counter | байты | device | А+В |
| `node_filesystem_avail_bytes` | Место, доступное обычному пользователю. | gauge | байты | device, fstype, mountpoint; device_error в отдельных версиях | А+В |
| `node_filesystem_device_error` | 1, если exporter не смог получить статистику файловой системы. | gauge | 0/1 | device, fstype, mountpoint; device_error в отдельных версиях | А+В |
| `node_filesystem_files` | Полное число inode. | gauge | inode | device, fstype, mountpoint; device_error в отдельных версиях | А+В |
| `node_filesystem_files_free` | Число свободных inode. | gauge | inode | device, fstype, mountpoint; device_error в отдельных версиях | А+В |
| `node_filesystem_free_bytes` | Свободное место, включая резерв для привилегированных пользователей. | gauge | байты | device, fstype, mountpoint; device_error в отдельных версиях | А+В |
| `node_filesystem_readonly` | 1, если файловая система доступна только для чтения. | gauge | 0/1 | device, fstype, mountpoint; device_error в отдельных версиях | А+В |
| `node_filesystem_size_bytes` | Полная ёмкость файловой системы. | gauge | байты | device, fstype, mountpoint; device_error в отдельных версиях | А+В |
| `node_md_disks` | Количество дисков программного RAID по состоянию. | gauge | диски | device, state | А+В |

<a id="s4"></a>

## Узел: сетевые интерфейсы

| Название | Описание | Тип | Единица | Основные атрибуты | Основание |
|---|---|---|---|---|---|
| `node_arp_entries` | Количество записей ARP на интерфейсе. | gauge | записи | device | А+В |
| `node_bonding_active` | Количество активных участников bond. | gauge | интерфейсы | master | А+В |
| `node_bonding_slaves` | Количество интерфейсов-участников bond. | gauge | интерфейсы | master | А+В |
| `node_network_carrier` | Наличие физической несущей: 1 — carrier присутствует. | gauge | 0/1 | device | А+В |
| `node_network_carrier_changes_total` | Количество изменений состояния несущей. | counter | события | device | А+В |
| `node_network_info` | Метаданные сетевого интерфейса в Node exporter 1.8.2; значение 1. | gauge | 1 | device, address, broadcast, duplex, operstate, adminstate, ifalias | В |
| `node_network_mtu_bytes` | Настроенный MTU интерфейса. | gauge | байты | device | А+В |
| `node_network_receive_bytes_total` | Принятые сетевым интерфейсом данные. | counter | байты | device | А+В |
| `node_network_receive_compressed_total` | Принятые сжатые пакеты. | counter | пакеты | device | А+В |
| `node_network_receive_drop_total` | Отброшенные входящие пакеты. | counter | пакеты | device | А+В |
| `node_network_receive_errs_total` | Ошибки приёма. | counter | ошибки | device | А+В |
| `node_network_receive_fifo_total` | Ошибки FIFO приёма. | counter | ошибки | device | А+В |
| `node_network_receive_frame_total` | Ошибки выравнивания входящих кадров. | counter | ошибки | device | А+В |
| `node_network_receive_multicast_total` | Принятые multicast-пакеты. | counter | пакеты | device | А+В |
| `node_network_receive_nohandler_total` | Пакеты без подходящего обработчика протокола. | counter | пакеты | device | А+В |
| `node_network_receive_packets_total` | Принятые пакеты. | counter | пакеты | device | А+В |
| `node_network_speed_bytes` | Заявленная скорость линка; несмотря на имя, значение выражено в байтах в секунду. | gauge | байты/с | device | А+В |
| `node_network_transmit_bytes_total` | Переданные сетевым интерфейсом данные. | counter | байты | device | А+В |
| `node_network_transmit_carrier_total` | Ошибки несущей при передаче. | counter | ошибки | device | А+В |
| `node_network_transmit_colls_total` | Коллизии передачи. | counter | события | device | А+В |
| `node_network_transmit_compressed_total` | Переданные сжатые пакеты. | counter | пакеты | device | А+В |
| `node_network_transmit_drop_total` | Отброшенные исходящие пакеты. | counter | пакеты | device | А+В |
| `node_network_transmit_errs_total` | Ошибки передачи. | counter | ошибки | device | А+В |
| `node_network_transmit_fifo_total` | Ошибки FIFO передачи. | counter | ошибки | device | А+В |
| `node_network_transmit_packets_total` | Переданные пакеты. | counter | пакеты | device | А+В |
| `node_network_up` | Операционное состояние интерфейса: 1 — up. | gauge | 0/1 | device | А+В |
| `node_nf_conntrack_entries` | Текущее число записей conntrack. | gauge | записи | — | А+В |
| `node_nf_conntrack_entries_limit` | Лимит числа записей conntrack. | gauge | записи | — | А+В |
| `node_softnet_dropped_total` | Пакеты, потерянные из-за переполнения очереди softnet. | counter | события | cpu | А+В |
| `node_softnet_flow_limit_count_total` | Срабатывания ограничения отдельных потоков RPS. | counter | события | cpu | А+В |
| `node_softnet_processed_total` | Пакеты, обработанные сетевым softirq. | counter | события | cpu | А+В |
| `node_softnet_received_rps_total` | Пробуждения CPU через механизм Receive Packet Steering. | counter | события | cpu | А+В |
| `node_softnet_times_squeezed_total` | Исчерпания бюджета обработки пакетов за цикл. | counter | события | cpu | А+В |
| `node_tcp_connection_states` | Текущее число TCP-соединений по состоянию; отдельный collector tcpstat. | gauge | соединения | state | А+В |
| `node_udp_queues` | Занятость очередей UDP по направлению. | gauge | байты | ip, queue | А+В |

<a id="s5"></a>

## Узел: TCP/IP и сокеты

Netstat collector 1.8.2 публикует поля MIB как untyped, хотя большинство из них накопительные. CurrEstab и MaxConn — текущие значения. Для sockstat память в страницах и в байтах приведена отдельно.

| Название | Описание | Тип | Единица | Основные атрибуты | Основание |
|---|---|---|---|---|---|
| `node_netstat_Icmp_InErrors` | Ошибки входящих ICMP-сообщений. | untyped | шт. | — | А+В |
| `node_netstat_Icmp_InMsgs` | Все входящие ICMP-сообщения. | untyped | шт. | — | А+В |
| `node_netstat_Icmp_OutMsgs` | Все исходящие ICMP-сообщения. | untyped | шт. | — | А+В |
| `node_netstat_IpExt_InOctets` | Объём входящих IP-данных. | untyped | байты | — | А+В |
| `node_netstat_IpExt_OutOctets` | Объём исходящих IP-данных. | untyped | байты | — | А+В |
| `node_netstat_TcpExt_ListenDrops` | TCP-пакеты, отброшенные слушающими сокетами. | untyped | шт. | — | А+В |
| `node_netstat_TcpExt_ListenOverflows` | Переполнения очереди соединений слушающего TCP-сокета. | untyped | шт. | — | А+В |
| `node_netstat_TcpExt_SyncookiesFailed` | Неуспешная проверка полученных SYN cookies. | untyped | шт. | — | А+В |
| `node_netstat_TcpExt_SyncookiesRecv` | Успешно проверенные SYN cookies. | untyped | шт. | — | А+В |
| `node_netstat_TcpExt_SyncookiesSent` | Отправленные SYN cookies. | untyped | шт. | — | А+В |
| `node_netstat_TcpExt_TCPOFOQueue` | Пакеты, добавленные в очередь TCP out-of-order. | untyped | шт. | — | А+В |
| `node_netstat_TcpExt_TCPRcvQDrop` | Пакеты, отброшенные из-за ограничений очереди приёма TCP. | untyped (счётчик) | шт. | — | А+В |
| `node_netstat_TcpExt_TCPSynRetrans` | Повторные передачи TCP SYN / SYN-ACK. | untyped (счётчик) | шт. | — | А+В |
| `node_netstat_TcpExt_TCPTimeouts` | Таймауты повторной передачи TCP. | untyped | шт. | — | А+В |
| `node_netstat_Tcp_ActiveOpens` | Попытки активного открытия TCP-соединений. | untyped | шт. | — | А+В |
| `node_netstat_Tcp_CurrEstab` | Текущие TCP-соединения в ESTABLISHED или CLOSE-WAIT. | untyped | шт. | — | А+В |
| `node_netstat_Tcp_InErrs` | Ошибочные входящие TCP-сегменты. | untyped | шт. | — | А+В |
| `node_netstat_Tcp_InSegs` | Полученные TCP-сегменты. | untyped | шт. | — | А+В |
| `node_netstat_Tcp_MaxConn` | Предел TCP-соединений; -1 означает динамический предел. | untyped (значение) | шт. | — | А+В |
| `node_netstat_Tcp_OutRsts` | Отправленные TCP RST. | untyped | шт. | — | А+В |
| `node_netstat_Tcp_OutSegs` | Отправленные TCP-сегменты по счётчику MIB. | untyped | шт. | — | А+В |
| `node_netstat_Tcp_PassiveOpens` | Пассивные открытия TCP-соединений. | untyped | шт. | — | А+В |
| `node_netstat_Tcp_RetransSegs` | Повторно переданные TCP-сегменты. | untyped | шт. | — | А+В |
| `node_netstat_UdpLite_InErrors` | Ошибки входящих UDP-Lite-датаграмм. | untyped | шт. | — | А+В |
| `node_netstat_Udp_InDatagrams` | Успешно доставленные UDP-датаграммы. | untyped | шт. | — | А+В |
| `node_netstat_Udp_InErrors` | Ошибки входящих UDP-датаграмм. | untyped | шт. | — | А+В |
| `node_netstat_Udp_NoPorts` | UDP-датаграммы для портов без слушателя. | untyped | шт. | — | А+В |
| `node_netstat_Udp_OutDatagrams` | Отправленные UDP-датаграммы. | untyped | шт. | — | А+В |
| `node_netstat_Udp_RcvbufErrors` | UDP-ошибки из-за нехватки приёмного буфера. | untyped | шт. | — | А+В |
| `node_netstat_Udp_SndbufErrors` | UDP-ошибки из-за нехватки буфера передачи. | untyped | шт. | — | А+В |
| `node_sockstat_FRAG_inuse` | Очереди сборки IP-фрагментов. | gauge | очереди | — | А+В |
| `node_sockstat_FRAG_memory` | Память очередей IP-фрагментации. | gauge | байты | — | А+В |
| `node_sockstat_RAW_inuse` | Используемые RAW-сокеты. | gauge | сокеты | — | А+В |
| `node_sockstat_TCP_alloc` | Выделенные TCP-сокеты. | gauge | сокеты | — | А+В |
| `node_sockstat_TCP_inuse` | TCP-сокеты inuse. | gauge | сокеты | — | А+В |
| `node_sockstat_TCP_mem` | Память TCP по sockstat, в страницах ОС. | gauge | страницы | — | А+В |
| `node_sockstat_TCP_mem_bytes` | Память TCP, пересчитанная в байты. | gauge | байты | — | А+В |
| `node_sockstat_TCP_orphan` | TCP-сокеты без привязки к пользовательскому процессу. | gauge | сокеты | — | А+В |
| `node_sockstat_TCP_tw` | TCP-сокеты TIME_WAIT. | gauge | сокеты | — | А+В |
| `node_sockstat_UDPLITE_inuse` | Используемые UDP-Lite-сокеты. | gauge | сокеты | — | А+В |
| `node_sockstat_UDP_inuse` | Используемые UDP-сокеты. | gauge | сокеты | — | А+В |
| `node_sockstat_UDP_mem` | Память UDP по sockstat, в страницах ОС. | gauge | страницы | — | А+В |
| `node_sockstat_UDP_mem_bytes` | Память UDP, пересчитанная в байты. | gauge | байты | — | А+В |
| `node_sockstat_sockets_used` | Все используемые сокеты. | gauge | сокеты | — | А+В |

<a id="s6"></a>

## Узел: оборудование

| Название | Описание | Тип | Единица | Основные атрибуты | Основание |
|---|---|---|---|---|---|
| `node_cooling_device_cur_state` | Текущий уровень воздействия устройства охлаждения. | gauge | уровень | name, type | А+В |
| `node_cooling_device_max_state` | Максимальный уровень воздействия устройства охлаждения. | gauge | уровень | name, type | А+В |
| `node_edac_correctable_errors_total` | Исправленные ошибки памяти, зарегистрированные EDAC. | counter | ошибки | controller | А+В |
| `node_edac_uncorrectable_errors_total` | Неисправимые ошибки памяти, зарегистрированные EDAC. | counter | ошибки | controller | А+В |
| `node_entropy_available_bits` | Оценка доступной энтропии ядра. | gauge | биты | — | А+В |
| `node_entropy_pool_size_bits` | Размер пула энтропии ядра. | gauge | биты | — | А+В |
| `node_fibrechannel_error_frames_total` | Ошибочные кадры Fibre Channel. | counter | кадры | fc_host | А+В |
| `node_fibrechannel_info` | Метаданные FC-порта; значение 1. | gauge | 1 | dev_loss_tmo, fabric_name, fc_host, port_id, port_name, port_state, port_type, speed, supported_classes, supported_speeds, symbolic_name | А+В |
| `node_fibrechannel_link_failure_total` | Сбои FC-линка. | counter | события | fc_host | А+В |
| `node_fibrechannel_loss_of_signal_total` | Потери физического сигнала FC. | counter | события | fc_host | А+В |
| `node_fibrechannel_loss_of_sync_total` | Потери синхронизации FC. | counter | события | fc_host | А+В |
| `node_fibrechannel_nos_total` | Полученные FC Not Operational Sequences. | counter | события | fc_host | А+В |
| `node_fibrechannel_rx_frames_total` | Принятые FC-кадры. | counter | кадры | fc_host | А+В |
| `node_fibrechannel_tx_frames_total` | Переданные FC-кадры. | counter | кадры | fc_host | А+В |
| `node_hwmon_chip_names` | Имя аппаратного датчика / чипа; значение 1. | gauge | 1 | chip, chip_name | А+В |
| `node_hwmon_fan_min_rpm` | Нижний порог скорости вентилятора. | gauge | об/мин | chip, sensor | А+В |
| `node_hwmon_fan_rpm` | Текущая скорость вентилятора. | gauge | об/мин | chip, sensor | А+В |
| `node_hwmon_temp_celsius` | Температура датчика. | gauge | °C | chip, sensor | А+В |
| `node_hwmon_temp_crit_alarm_celsius` | Флаг критической температурной аварии. Суффикс celsius исторический; это не температура. | gauge | 0/1 | chip, sensor | А+В |
| `node_hwmon_temp_crit_celsius` | Критический порог температуры. | gauge | °C | chip, sensor | А+В |
| `node_hwmon_temp_crit_hyst_celsius` | Температура снятия критического состояния (гистерезис). | gauge | °C | — | А+В |
| `node_hwmon_temp_max_celsius` | Верхний рабочий порог температуры. | gauge | °C | chip, sensor | А+В |
| `node_power_supply_online` | Наличие внешнего питания по данным power_supply. | gauge | 0/1 | power_supply | А+В |

<a id="s7"></a>

## Узел: время

| Название | Описание | Тип | Единица | Основные атрибуты | Основание |
|---|---|---|---|---|---|
| `node_boot_time_seconds` | Время последней загрузки ОС. | gauge | Unix, с | — | А+В |
| `node_time_seconds` | Текущее системное время узла. | gauge | Unix, с | — | А+В |
| `node_timex_estimated_error_seconds` | Оценка ошибки часов. | gauge | с | — | А+В |
| `node_timex_frequency_adjustment_ratio` | Относительная поправка частоты системных часов. | gauge | доля | — | А+В |
| `node_timex_loop_time_constant` | Постоянная времени алгоритма синхронизации. | gauge | параметр | — | А+В |
| `node_timex_maxerror_seconds` | Максимальная оценка ошибки системных часов. | gauge | с | — | А+В |
| `node_timex_offset_seconds` | Оценка смещения системных часов. | gauge | с | — | А+В |
| `node_timex_pps_calibration_total` | Интервалы калибровки PPS. | counter | интервалы | — | А+В |
| `node_timex_pps_error_total` | Ошибки калибровки PPS. | counter | ошибки | — | А+В |
| `node_timex_pps_frequency_hertz` | Поправка частоты от PPS, в единицах, экспортируемых collector. | gauge | Гц | — | А+В |
| `node_timex_pps_jitter_seconds` | Разброс PPS-сигнала. | gauge | с | — | А+В |
| `node_timex_pps_jitter_total` | Срабатывания порога PPS jitter. | counter | события | — | А+В |
| `node_timex_pps_shift_seconds` | Интервал PPS, полученный из shift. | gauge | с | — | А+В |
| `node_timex_pps_stability_exceeded_total` | Превышения допустимой нестабильности PPS. | counter | события | — | А+В |
| `node_timex_pps_stability_hertz` | Оценка стабильности частоты PPS. | gauge | Гц | — | А+В |
| `node_timex_sync_status` | 1 — часы считаются синхронизированными интерфейсом timex. | gauge | 0/1 | — | А+В |
| `node_timex_tai_offset_seconds` | Смещение TAI относительно UTC. | gauge | с | — | А+В |
| `node_timex_tick_seconds` | Длительность системного тика. | gauge | с | — | А+В |

<a id="s8"></a>

## Узел: процессы и exporter

| Название | Описание | Тип | Единица | Основные атрибуты | Основание |
|---|---|---|---|---|---|
| `node_filefd_allocated` | Выделенные ядром файловые дескрипторы. | gauge | дескрипторы | — | А+В |
| `node_filefd_maximum` | Системный максимум файловых дескрипторов. | gauge | дескрипторы | — | А+В |
| `node_forks_total` | Созданные процессы/задачи с момента загрузки. | counter | задачи | — | А+В |
| `node_processes_max_processes` | Верхняя граница PID из pid_max. | gauge | PID | — | А+В |
| `node_processes_max_threads` | Системный лимит числа потоков. | gauge | потоки | — | А+В |
| `node_processes_pids` | Число текущих PID в /proc. | gauge | процессы | — | А+В |
| `node_processes_state` | Количество процессов по состоянию. | gauge | процессы | state | А+В |
| `node_processes_threads` | Число текущих потоков. | gauge | потоки | — | А+В |
| `node_procs_blocked` | Задачи в непрерываемом ожидании I/O. | gauge | задачи | — | А+В |
| `node_procs_running` | Задачи, выполняющиеся или готовые выполняться на CPU. | gauge | задачи | — | А+В |
| `node_scrape_collector_duration_seconds` | Продолжительность работы collector. | gauge | с | collector | А+В |
| `node_scrape_collector_success` | 1 — collector успешно собрал данные в последнем запросе. | gauge | 0/1 | collector | А+В |
| `node_systemd_socket_accepted_connections_total` | Соединения, принятые systemd socket unit. | counter | соединения | name | А+В |
| `node_systemd_socket_current_connections` | Активные соединения systemd socket unit. | gauge | соединения | name | А+В |
| `node_systemd_socket_refused_connections_total` | Соединения, отклонённые systemd socket unit. | counter | соединения | name | А+В |
| `node_systemd_units` | Число systemd units по состоянию. | gauge | units | state | А+В |
| `node_textfile_scrape_error` | 1 — ошибка чтения или разбора файлов textfile collector. | gauge | 0/1 | — | А+В |
| `node_uname_info` | Сведения uname об ОС/узле; значение 1. | gauge | 1 | sysname, release, version, machine, nodename, domainname | А+В |

<a id="s9"></a>

## Libvirt: ВМ

Приведены все 67 объявленных дескрипторов libvirt в коде v2.2.0. Наличие конкретного ряда зависит от доменов, драйверов и доступных DomainStats. Код важнее README: например, фактические имена domain job содержат `domain_job_info`.

| Название | Описание | Тип | Единица | Основные атрибуты | Основание |
|---|---|---|---|---|---|
| `libvirt_domain_block_stats_capacity_bytes` | Логическая ёмкость блочного устройства домена. | gauge | байты | domain, target_device | А+В |
| `libvirt_domain_block_stats_flush_requests_total` | Запросы flush блочного устройства домена. | counter | операции | domain, target_device | В |
| `libvirt_domain_block_stats_flush_time_seconds_total` | Суммарное время flush блочного устройства домена. | counter | с | domain, target_device | В |
| `libvirt_domain_block_stats_info` | Метаданные блочного устройства: bus, драйвер, источник, serial. | gauge | 1 | domain, disk_type, target_bus, driver_name, driver_type, driver_cache, driver_discard, source_file, source_protocol, target_device, serial | В |
| `libvirt_domain_block_stats_read_bytes_total` | Данные, прочитанные доменом с диска. | counter | байты | domain, target_device | А+В |
| `libvirt_domain_block_stats_read_requests_total` | Запросы чтения диска домена. | counter | операции | domain, target_device | А+В |
| `libvirt_domain_block_stats_read_time_seconds_total` | Суммарное время запросов чтения. | counter | с | domain, target_device | А+В |
| `libvirt_domain_block_stats_write_bytes_total` | Данные, записанные доменом на диск. | counter | байты | domain, target_device | А+В |
| `libvirt_domain_block_stats_write_requests_total` | Запросы записи диска домена. | counter | операции | domain, target_device | А+В |
| `libvirt_domain_block_stats_write_time_seconds_total` | Суммарное время запросов записи. | counter | с | domain, target_device | А+В |
| `libvirt_domain_info` | Метаданные ОС домена, включая архитектуру и тип машины. | gauge | 1 | domain, os_type, os_type_arch, os_type_machine | В |
| `libvirt_domain_info_cpu_time_seconds_total` | Суммарное время CPU всех vCPU домена; rate даёт занятые CPU-секунды в секунду. | counter | с | domain | А+В |
| `libvirt_domain_info_maximum_memory_bytes` | Максимальный объём памяти домена. | gauge | байты | domain | А+В |
| `libvirt_domain_info_memory_usage_bytes` | Текущий объём памяти домена по DomainInfo libvirt; не RSS приложений гостя. | gauge | байты | domain | В |
| `libvirt_domain_info_state` | Числовое состояние libvirt-домена; стандартные состояния: 1 running, 3 paused, 5 shutoff, 6 crashed. | gauge | код | domain, state_desc | А+В |
| `libvirt_domain_info_virtual_cpus` | Количество виртуальных CPU домена. | gauge | vCPU | domain | А+В |
| `libvirt_domain_interface_stats_info` | Метаданные виртуального сетевого интерфейса, включая MAC, bridge и MTU. | gauge | 1 | domain, interface_type, source_bridge, target_device, mac_address, model_type, mtu_size | В |
| `libvirt_domain_interface_stats_receive_bytes_total` | Объём данных приёма на виртуальном интерфейсе домена. | counter | байты | domain, target_device | А+В |
| `libvirt_domain_interface_stats_receive_drops_total` | Число отброшенных пакетов приёма на виртуальном интерфейсе домена. | counter | пакеты | domain, target_device | А+В |
| `libvirt_domain_interface_stats_receive_errors_total` | Число ошибок приёма на виртуальном интерфейсе домена. | counter | ошибки | domain, target_device | А+В |
| `libvirt_domain_interface_stats_receive_packets_total` | Число пакетов приёма на виртуальном интерфейсе домена. | counter | пакеты | domain, target_device | А+В |
| `libvirt_domain_interface_stats_transmit_bytes_total` | Объём данных передачи на виртуальном интерфейсе домена. | counter | байты | domain, target_device | А+В |
| `libvirt_domain_interface_stats_transmit_drops_total` | Число отброшенных пакетов передачи на виртуальном интерфейсе домена. | counter | пакеты | domain, target_device | А+В |
| `libvirt_domain_interface_stats_transmit_errors_total` | Число ошибок передачи на виртуальном интерфейсе домена. | counter | ошибки | domain, target_device | А+В |
| `libvirt_domain_interface_stats_transmit_packets_total` | Число пакетов передачи на виртуальном интерфейсе домена. | counter | пакеты | domain, target_device | А+В |
| `libvirt_domain_job_info_data_processed_bytes` | Обработанный объём всех данных текущей операции libvirt domain job. | gauge | байты | domain | В |
| `libvirt_domain_job_info_data_remaining_bytes` | Оставшийся объём всех данных текущей операции libvirt domain job. | gauge | байты | domain | В |
| `libvirt_domain_job_info_data_total_bytes` | Полный объём всех данных текущей операции libvirt domain job. | gauge | байты | domain | В |
| `libvirt_domain_job_info_file_processed_bytes` | Обработанный объём файловых данных текущей операции libvirt domain job. | gauge | байты | domain | В |
| `libvirt_domain_job_info_file_remaining_bytes` | Оставшийся объём файловых данных текущей операции libvirt domain job. | gauge | байты | domain | В |
| `libvirt_domain_job_info_file_total_bytes` | Полный объём файловых данных текущей операции libvirt domain job. | gauge | байты | domain | В |
| `libvirt_domain_job_info_memory_processed_bytes` | Обработанный объём памяти текущей операции libvirt domain job. | gauge | байты | domain | В |
| `libvirt_domain_job_info_memory_remaining_bytes` | Оставшийся объём памяти текущей операции libvirt domain job. | gauge | байты | domain | В |
| `libvirt_domain_job_info_memory_total_bytes` | Полный объём памяти текущей операции libvirt domain job. | gauge | байты | domain | В |
| `libvirt_domain_job_info_time_elapsed_seconds` | Время, прошедшее с начала domain job. | gauge | с | domain | В |
| `libvirt_domain_job_info_time_remaining_seconds` | Оценка времени до завершения domain job. | gauge | с | domain | В |
| `libvirt_domain_job_info_type` | Код типа текущей операции libvirt domain job. | gauge | код | domain | В |
| `libvirt_domain_memory_stats_available_bytes` | Общий доступный гостю объём usable RAM по статистике balloon; это не Linux MemAvailable. | gauge | байты | domain | В |
| `libvirt_domain_memory_stats_current_balloon_bytes` | Текущий размер памяти домена по balloon. | gauge | байты | domain | В |
| `libvirt_domain_memory_stats_disk_caches_bytes` | Память кэша гостя, освобождаемая без дополнительного I/O. | gauge | байты | domain | В |
| `libvirt_domain_memory_stats_hugetlb_pgalloc_total` | Успешные выделения huge pages в госте; TYPE в этой версии — gauge. | gauge | страницы | domain | В |
| `libvirt_domain_memory_stats_hugetlb_pgfail_total` | Неудачные выделения huge pages в госте; TYPE в этой версии — gauge. | gauge | события | domain | В |
| `libvirt_domain_memory_stats_last_update_timestamp_seconds` | Время последнего обновления memory stats гостя. | gauge | Unix, с | domain | В |
| `libvirt_domain_memory_stats_major_fault_total` | Major page faults гостя, потребовавшие дискового I/O. | counter | события | domain | В |
| `libvirt_domain_memory_stats_maximum_bytes` | Максимальный размер памяти домена по источнику stats. | gauge | байты | domain | В |
| `libvirt_domain_memory_stats_minor_fault_total` | Minor page faults гостя без дискового I/O. | counter | события | domain | В |
| `libvirt_domain_memory_stats_rss_bytes` | Резидентная память процесса, выполняющего домен на хосте. | gauge | байты | domain | В |
| `libvirt_domain_memory_stats_swap_in_bytes` | Объём прочитанного из swap внутри гостя; в v2.2.0 экспортируется gauge. | gauge | байты | domain | В |
| `libvirt_domain_memory_stats_swap_out_bytes` | Объём записанного в swap внутри гостя; в v2.2.0 экспортируется gauge. | gauge | байты | domain | В |
| `libvirt_domain_memory_stats_unused_bytes` | Свободная память внутри гостя. | gauge | байты | domain | В |
| `libvirt_domain_memory_stats_usable_bytes` | Память, которую гость может использовать без swap; соответствует смыслу MemAvailable. | gauge | байты | domain | В |
| `libvirt_domain_memory_stats_used_percent` | Процент используемой памяти по алгоритму exporter и данным balloon; зависит от доступных guest stats. | gauge | % | domain | А+В |
| `libvirt_domain_openstack_info` | Информационная метрика для связи libvirt-домена с ВМ, flavor, проектом и пользователем OpenStack. | gauge | 1 | domain, instance_name, instance_id, flavor_name, user_name, user_id, project_name, project_id | А+В |
| `libvirt_domain_timed_out` | Таймаут сбора статистики домена. | gauge | 0/1 | domain | В |
| `libvirt_domain_vcpu_current` | Текущее число vCPU домена по DomainStats. | gauge | vCPU | domain | В |
| `libvirt_domain_vcpu_delay_seconds_total` | Время ожидания vCPU в очереди планировщика хоста; это не прямое измерение steal внутри гостя. | counter | с | domain, vcpu | А+В |
| `libvirt_domain_vcpu_maximum` | Максимальное число vCPU домена по DomainStats. | gauge | vCPU | domain | В |
| `libvirt_domain_vcpu_state` | Код состояния отдельного vCPU. | gauge | код | domain, vcpu | В |
| `libvirt_domain_vcpu_time_seconds_total` | Время выполнения отдельного vCPU. | counter | с | domain, vcpu | А+В |
| `libvirt_domain_vcpu_wait_seconds_total` | Суммарное время ожидания vCPU, возвращённое libvirt в поле wait. | counter | с | domain, vcpu | В |
| `libvirt_domains` | Количество доменов, видимых exporter. | gauge | домены | — | В |
| `libvirt_storage_pool_allocation_bytes` | Занятая ёмкость пула хранения libvirt. | gauge | байты | storage_pool | В |
| `libvirt_storage_pool_available_bytes` | Свободная ёмкость пула хранения libvirt. | gauge | байты | storage_pool | В |
| `libvirt_storage_pool_capacity_bytes` | Полная ёмкость пула хранения libvirt. | gauge | байты | storage_pool | В |
| `libvirt_storage_pool_state` | Код состояния пула хранения libvirt. | gauge | код | storage_pool | В |
| `libvirt_storage_pool_timed_out` | Таймаут получения статистики пула хранения. | gauge | 0/1 | storage_pool | В |
| `libvirt_up` | Успешность получения данных от libvirt: 1 — сбор успешен. | gauge | 0/1 | — | А+В |

<a id="s10"></a>

## OpenStack: API и ресурсы

Приведены все 96 дескрипторов сервисных метрик v1.7.0 и служебные up/collect-time. Часть collectors относится к опциональным сервисам. Наличие collector в бинарном файле не означает наличие сервиса в данном облаке. Для agent_state в этой версии используется TYPE counter при смысловом значении 0/1.

| Название | Описание | Тип | Единица | Основные атрибуты | Основание |
|---|---|---|---|---|---|
| `openstack_cinder_agent_state` | Доступность службы Cinder; применяется отдельно к cinder-volume, scheduler и backup. В версии 1.7.0 TYPE=counter, но значение 0/1 может уменьшаться: не применять rate как к обычному счётчику. | counter | 0/1 | uuid, hostname, service, adminState, zone, disabledReason | А+В |
| `openstack_cinder_limits_backup_max_gb` | Квота объёма резервных копий Cinder. Slow collector; отсутствует при --disable-slow-metrics. | gauge | GiB | tenant, tenant_id | В |
| `openstack_cinder_limits_backup_used_gb` | Использованный объём резервных копий Cinder. Slow collector; отсутствует при --disable-slow-metrics. | gauge | GiB | tenant, tenant_id | В |
| `openstack_cinder_limits_volume_max_gb` | Квота объёма томов проекта. Slow collector; отсутствует при --disable-slow-metrics. | gauge | GiB | tenant, tenant_id | В |
| `openstack_cinder_limits_volume_used_gb` | Занятый объём томов проекта. Slow collector; отсутствует при --disable-slow-metrics. | gauge | GiB | tenant, tenant_id | В |
| `openstack_cinder_pool_capacity_free_gb` | Свободная ёмкость backend-пула Cinder по данным драйвера. | gauge | GiB по Cinder | name, volume_backend_name, vendor_name | А+В |
| `openstack_cinder_pool_capacity_total_gb` | Полная ёмкость backend-пула Cinder по данным драйвера; unknown/infinite требуют проверки преобразования exporter. | gauge | GiB по Cinder | name, volume_backend_name, vendor_name | А+В |
| `openstack_cinder_snapshots` | Количество snapshots Cinder. | gauge | шт. / код — по описанию | — | В |
| `openstack_cinder_up` | Успешность сбора метрик сервиса cinder: 1 — сбор завершён без ошибки. | gauge | 0/1 | — | В |
| `openstack_cinder_volume_gb` | Размер тома; состояние тома передаётся в status. | gauge | GiB | id, name, status, availability_zone, bootable, tenant_id, user_id, volume_type, server_id | А+В |
| `openstack_cinder_volume_status` | Устаревшая числовая метрика статуса тома, ещё присутствующая в v1.7.0 при disable-deprecated-metrics=false. Предпочтительна volume_gb с label status. Deprecated; исключается при --disable-deprecated-metrics. | gauge | код | id, name, status, bootable, tenant_id, size, volume_type, server_id | А+В |
| `openstack_cinder_volume_status_counter` | Число томов по статусу; несмотря на слово counter, TYPE — gauge. | gauge | шт. / код — по описанию | status | В |
| `openstack_cinder_volumes` | Количество томов Cinder. | gauge | шт. / код — по описанию | — | В |
| `openstack_container_infra_cluster_masters` | Количество master-узлов кластера Magnum. | gauge | шт. / код — по описанию | uuid, name, stack_id, status, node_count, project_id | В |
| `openstack_container_infra_cluster_nodes` | Количество worker-узлов кластера Magnum. | gauge | шт. / код — по описанию | uuid, name, stack_id, status, master_count, project_id | В |
| `openstack_container_infra_cluster_status` | Код состояния кластера Magnum. | gauge | шт. / код — по описанию | uuid, name, stack_id, status, node_count, master_count, project_id | В |
| `openstack_container_infra_total_clusters` | Количество кластеров Magnum. | gauge | шт. / код — по описанию | — | В |
| `openstack_container_infra_up` | Успешность сбора метрик сервиса container_infra: 1 — сбор завершён без ошибки. | gauge | 0/1 | — | В |
| `openstack_designate_recordsets` | Количество DNS recordsets. | gauge | шт. / код — по описанию | zone_id, zone_name, tenant_id | В |
| `openstack_designate_recordsets_status` | Код состояния DNS recordset. | gauge | шт. / код — по описанию | id, name, status, zone_id, zone_name, type | В |
| `openstack_designate_up` | Успешность сбора метрик сервиса designate: 1 — сбор завершён без ошибки. | gauge | 0/1 | — | В |
| `openstack_designate_zone_status` | Код состояния DNS-зоны. | gauge | шт. / код — по описанию | id, name, status, tenant_id, type | В |
| `openstack_designate_zones` | Количество DNS-зон Designate. | gauge | шт. / код — по описанию | — | В |
| `openstack_glance_image_bytes` | Размер образа Glance в байтах. Slow collector; отсутствует при --disable-slow-metrics. | gauge | байты | id, name, tenant_id | В |
| `openstack_glance_images` | Количество образов Glance. | gauge | шт. / код — по описанию | — | В |
| `openstack_glance_up` | Успешность сбора метрик сервиса glance: 1 — сбор завершён без ошибки. | gauge | 0/1 | — | В |
| `openstack_gnocchi_status_measures_to_process` | Measures Gnocchi, ожидающие обработки. | gauge | шт. / код — по описанию | — | В |
| `openstack_gnocchi_status_metric_having_measures_to_process` | Метрики Gnocchi с ожидающими обработки measures. | gauge | шт. / код — по описанию | — | В |
| `openstack_gnocchi_status_metricd_processors` | Число процессов metricd Gnocchi. | gauge | шт. / код — по описанию | — | В |
| `openstack_gnocchi_total_metrics` | Общее число метрик в Gnocchi. | gauge | шт. / код — по описанию | — | В |
| `openstack_gnocchi_up` | Успешность сбора метрик сервиса gnocchi: 1 — сбор завершён без ошибки. | gauge | 0/1 | — | В |
| `openstack_heat_stack_status` | Код состояния стека Heat; строковый статус также в labels. | gauge | шт. / код — по описанию | id, name, project_id, status | В |
| `openstack_heat_stack_status_counter` | Число стеков Heat по статусу; TYPE — gauge. | gauge | шт. / код — по описанию | status | В |
| `openstack_heat_up` | Успешность сбора метрик сервиса heat: 1 — сбор завершён без ошибки. | gauge | 0/1 | — | В |
| `openstack_identity_domains` | Количество доменов Keystone. | gauge | шт. / код — по описанию | — | В |
| `openstack_identity_groups` | Количество групп Keystone. | gauge | шт. / код — по описанию | — | В |
| `openstack_identity_project_info` | Метаданные проекта Keystone; значение информационной метрики. | gauge | шт. / код — по описанию | is_domain, description, domain_id, enabled, id, name, parent_id | В |
| `openstack_identity_projects` | Количество проектов Keystone. | gauge | шт. / код — по описанию | — | В |
| `openstack_identity_regions` | Количество регионов Keystone. | gauge | шт. / код — по описанию | — | В |
| `openstack_identity_up` | Успешность сбора метрик сервиса identity: 1 — сбор завершён без ошибки. | gauge | 0/1 | — | В |
| `openstack_identity_users` | Количество пользователей Keystone. | gauge | шт. / код — по описанию | — | В |
| `openstack_ironic_node` | Информация о bare-metal узле Ironic и его состояниях. Это API-метрика OpenStack exporter, не датчик BMC. | gauge | шт. / код — по описанию | id, name, provision_state, power_state, maintenance, console_enabled, resource_class, deploy_kernel, deploy_ramdisk | В |
| `openstack_ironic_up` | Успешность сбора метрик сервиса ironic: 1 — сбор завершён без ошибки. | gauge | 0/1 | — | В |
| `openstack_loadbalancer_amphora_status` | Состояние amphora в labels. | gauge | шт. / код — по описанию | id, loadbalancer_id, compute_id, status, role, lb_network_ip, ha_ip, cert_expiration | В |
| `openstack_loadbalancer_loadbalancer_status` | Состояние балансировщика и параметры в labels. | gauge | шт. / код — по описанию | id, name, project_id, operating_status, provisioning_status, provider, vip_address | В |
| `openstack_loadbalancer_pool_status` | Состояние пула балансировщика. | gauge | шт. / код — по описанию | id, provisioning_status, name, loadbalancers, protocol, lb_algorithm, operating_status, project_id | В |
| `openstack_loadbalancer_total_amphorae` | Количество amphorae Octavia. | gauge | шт. / код — по описанию | — | В |
| `openstack_loadbalancer_total_loadbalancers` | Количество балансировщиков Octavia. | gauge | шт. / код — по описанию | — | В |
| `openstack_loadbalancer_total_pools` | Количество pools балансировщика. | gauge | шт. / код — по описанию | — | В |
| `openstack_loadbalancer_up` | Успешность сбора метрик сервиса loadbalancer: 1 — сбор завершён без ошибки. | gauge | 0/1 | — | В |
| `openstack_metric_collect_seconds` | Длительность отдельной функции сбора из OpenStack API; публикуется при включённом collect metric time. | gauge | с | openstack_metric, openstack_service | В |
| `openstack_neutron_agent_state` | Доступность агента Neutron; adminState отражает административное включение, а значение — alive. В версии 1.7.0 TYPE=counter, но значение 0/1 может уменьшаться: не применять rate как к обычному счётчику. | counter | 0/1 | id, hostname, service, adminState, availability_zone | А+В |
| `openstack_neutron_floating_ip` | Информация о конкретном floating IP. | gauge | шт. / код — по описанию | id, floating_network_id, router_id, status, project_id, floating_ip_address | В |
| `openstack_neutron_floating_ips` | Количество floating IP. | gauge | шт. / код — по описанию | — | В |
| `openstack_neutron_floating_ips_associated_not_active` | Floating IP, привязанные к портам, но не находящиеся в ACTIVE. | gauge | шт. / код — по описанию | — | В |
| `openstack_neutron_l3_agent_of_router` | Привязка маршрутизатора к L3-агенту и его HA-состояние. | gauge | шт. / код — по описанию | router_id, l3_agent_id, ha_state, agent_alive, agent_admin_up, agent_host | В |
| `openstack_neutron_network` | Информация о сети Neutron. | gauge | шт. / код — по описанию | id, tenant_id, status, name, is_shared, is_external, provider_network_type, provider_physical_network, provider_segmentation_id, subnets, tags | В |
| `openstack_neutron_network_ip_availabilities_total` | Полный размер адресного пространства подсети по Network IP Availability. | gauge | шт. / код — по описанию | network_id, network_name, ip_version, cidr, subnet_name, project_id | В |
| `openstack_neutron_network_ip_availabilities_used` | Использованные адреса подсети по Network IP Availability. | gauge | шт. / код — по описанию | network_id, network_name, ip_version, cidr, subnet_name, project_id | В |
| `openstack_neutron_networks` | Количество сетей Neutron. | gauge | шт. / код — по описанию | — | В |
| `openstack_neutron_port` | Метаданные порта Neutron. | gauge | шт. / код — по описанию | uuid, network_id, mac_address, device_owner, status, binding_vif_type, admin_state_up, fixed_ips | В |
| `openstack_neutron_ports` | Количество портов Neutron. | gauge | шт. / код — по описанию | — | В |
| `openstack_neutron_ports_lb_not_active` | Неактивные порты балансировщика. | gauge | шт. / код — по описанию | — | В |
| `openstack_neutron_ports_no_ips` | Порты без назначенных IP. | gauge | шт. / код — по описанию | — | В |
| `openstack_neutron_router` | Метаданные маршрутизатора Neutron. | gauge | шт. / код — по описанию | id, name, project_id, admin_state_up, status, external_network_id | В |
| `openstack_neutron_routers` | Количество маршрутизаторов. | gauge | шт. / код — по описанию | — | В |
| `openstack_neutron_routers_not_active` | Маршрутизаторы не в состоянии ACTIVE. | gauge | шт. / код — по описанию | — | В |
| `openstack_neutron_security_groups` | Количество security groups, видимых соответствующему API. | gauge | шт. / код — по описанию | — | В |
| `openstack_neutron_subnet` | Метаданные подсети Neutron. | gauge | шт. / код — по описанию | id, tenant_id, name, network_id, cidr, gateway_ip, enable_dhcp, dns_nameservers, tags | В |
| `openstack_neutron_subnets` | Количество подсетей Neutron. | gauge | шт. / код — по описанию | — | В |
| `openstack_neutron_subnets_free` | Свободная ёмкость subnet pool в подсетях. | gauge | шт. / код — по описанию | ip_version, prefix, prefix_length, project_id, subnet_pool_id, subnet_pool_name | В |
| `openstack_neutron_subnets_total` | Ёмкость subnet pool в единицах подсетей выбранной длины префикса. | gauge | шт. / код — по описанию | ip_version, prefix, prefix_length, project_id, subnet_pool_id, subnet_pool_name | В |
| `openstack_neutron_subnets_used` | Использованная ёмкость subnet pool в подсетях. | gauge | шт. / код — по описанию | ip_version, prefix, prefix_length, project_id, subnet_pool_id, subnet_pool_name | В |
| `openstack_neutron_up` | Успешность сбора метрик сервиса neutron: 1 — сбор завершён без ошибки. | gauge | 0/1 | — | В |
| `openstack_nova_agent_state` | Состояние службы Nova: 1 — alive, 0 — down; административное включение хранится отдельно в adminState. В версии 1.7.0 TYPE=counter, но значение 0/1 может уменьшаться: не применять rate как к обычному счётчику. | counter | 0/1 | id, hostname, service, adminState, zone, disabledReason | А+В |
| `openstack_nova_availability_zones` | Количество зон доступности Nova. | gauge | шт. / код — по описанию | — | В |
| `openstack_nova_current_workload` | Текущие операции гипервизора по учёту Nova. | gauge | шт. / код — по описанию | hostname, availability_zone, aggregates | В |
| `openstack_nova_flavor` | Параметры flavor в labels. | gauge | шт. / код — по описанию | id, name, vcpus, ram, disk, is_public | В |
| `openstack_nova_flavors` | Количество flavors Nova. | gauge | шт. / код — по описанию | — | В |
| `openstack_nova_free_disk_bytes` | Свободный локальный диск по Nova. | gauge | байты | hostname, availability_zone, aggregates | В |
| `openstack_nova_limits_instances_max` | Квота числа экземпляров проекта. Slow collector; отсутствует при --disable-slow-metrics. | gauge | шт. / код — по описанию | tenant, tenant_id | В |
| `openstack_nova_limits_instances_used` | Число экземпляров, учтённых в квоте проекта. Slow collector; отсутствует при --disable-slow-metrics. | gauge | шт. / код — по описанию | tenant, tenant_id | В |
| `openstack_nova_limits_memory_max` | Квота RAM проекта, как возвращает compute limits API. Slow collector; отсутствует при --disable-slow-metrics. | gauge | MiB | tenant, tenant_id | В |
| `openstack_nova_limits_memory_used` | Использованная RAM проекта по compute limits API. Slow collector; отсутствует при --disable-slow-metrics. | gauge | MiB | tenant, tenant_id | В |
| `openstack_nova_limits_vcpus_max` | Квота vCPU проекта. Slow collector; отсутствует при --disable-slow-metrics. | gauge | шт. / код — по описанию | tenant, tenant_id | В |
| `openstack_nova_limits_vcpus_used` | Использованные vCPU проекта. Slow collector; отсутствует при --disable-slow-metrics. | gauge | шт. / код — по описанию | tenant, tenant_id | В |
| `openstack_nova_local_storage_available_bytes` | Общая локальная дисковая ёмкость гипервизора по Nova. | gauge | байты | hostname, availability_zone, aggregates | В |
| `openstack_nova_local_storage_used_bytes` | Занятая локальная дисковая ёмкость по Nova. | gauge | байты | hostname, availability_zone, aggregates | В |
| `openstack_nova_memory_available_bytes` | Полная RAM гипервизора по учёту Nova, до вычитания занятых ресурсов и применения allocation ratio. | gauge | байты | hostname, availability_zone, aggregates | А+В |
| `openstack_nova_memory_used_bytes` | RAM, учтённая Nova как занятая; это не фактическое использование памяти внутри ВМ. | gauge | байты | hostname, availability_zone, aggregates | А+В |
| `openstack_nova_running_vms` | Работающие ВМ по данным гипервизора. | gauge | шт. / код — по описанию | hostname, availability_zone, aggregates | В |
| `openstack_nova_security_groups` | Количество security groups, видимых соответствующему API. | gauge | шт. / код — по описанию | — | В |
| `openstack_nova_server_local_gb` | Локальный диск ВМ по отчёту Nova usage. Slow collector; отсутствует при --disable-slow-metrics. | gauge | GiB | name, id, tenant_id | В |
| `openstack_nova_server_status` | Индекс состояния ВМ в таблице exporter 1.7.0: ACTIVE=0, ERROR=4, SHUTOFF=11, PAUSED=16; неизвестное значение=-1. Для фильтров удобнее label status. | gauge | код | id, status, name, tenant_id, user_id, address_ipv4, address_ipv6, host_id, hypervisor_hostname, uuid, availability_zone, flavor_id, instance_libvirt | А+В |
| `openstack_nova_total_vms` | Общее число серверов, полученное Nova API; это региональный итог, не число ВМ одного гипервизора. | gauge | ВМ | — | А+В |
| `openstack_nova_up` | Успешность сбора метрик сервиса nova: 1 — сбор завершён без ошибки. | gauge | 0/1 | — | В |
| `openstack_nova_vcpus_available` | CPU-ёмкость гипервизора по Nova; не остаток свободных vCPU. | gauge | CPU | hostname, availability_zone, aggregates | А+В |
| `openstack_nova_vcpus_used` | Число vCPU, учтённых Nova как занятые экземплярами. | gauge | vCPU | hostname, availability_zone, aggregates | А+В |
| `openstack_object_store_bytes` | Объём объектов object storage. | gauge | байты | container_name | В |
| `openstack_object_store_objects` | Число объектов object storage для учётной записи/проекта. | gauge | шт. / код — по описанию | container_name | В |
| `openstack_object_store_up` | Успешность сбора метрик сервиса object_store: 1 — сбор завершён без ошибки. | gauge | 0/1 | — | В |
| `openstack_placement_resource_allocation_ratio` | Коэффициент допустимого overcommit для класса ресурса провайдера Placement. | gauge | коэффициент | hostname, resourcetype | А+В |
| `openstack_placement_resource_reserved` | Резерв класса ресурса провайдера Placement. | gauge | по классу ресурса | hostname, resourcetype | В |
| `openstack_placement_resource_total` | Общая ёмкость класса ресурса провайдера Placement до allocation ratio. | gauge | по классу ресурса | hostname, resourcetype | В |
| `openstack_placement_resource_usage` | Использование класса ресурса провайдера Placement. | gauge | по классу ресурса | hostname, resourcetype | В |
| `openstack_placement_up` | Успешность сбора метрик сервиса placement: 1 — сбор завершён без ошибки. | gauge | 0/1 | — | В |
| `openstack_trove_instance_status` | Состояние DB instance Trove. | gauge | шт. / код — по описанию | datastore_type, datastore_version, health_status, id, name, region, status, tenant_id | В |
| `openstack_trove_instance_volume_size_gb` | Выделенный размер диска DB instance Trove. | gauge | GiB | datastore_type, datastore_version, health_status, id, name, region, status, tenant_id | В |
| `openstack_trove_instance_volume_used_gb` | Использованный объём диска DB instance Trove. | gauge | GiB | datastore_type, datastore_version, health_status, id, name, region, status, tenant_id | В |
| `openstack_trove_total_instances` | Количество DB instances Trove. | gauge | шт. / код — по описанию | — | В |
| `openstack_trove_up` | Успешность сбора метрик сервиса trove: 1 — сбор завершён без ошибки. | gauge | 0/1 | — | В |

<a id="s11"></a>

## MariaDB / MySQL и Galera

В mysqld_exporter 0.16.0 generic SHOW GLOBAL STATUS передаётся как untyped. Это относится в том числе к wsrep и трём приведённым накопительным статусам; тип нельзя вывести только из смысла поля.

| Название | Описание | Тип | Единица | Основные атрибуты | Основание |
|---|---|---|---|---|---|
| `mysql_global_status_innodb_log_waits` | Ожидания освобождения буфера журнала InnoDB. | untyped (счётчик) | события | — | А |
| `mysql_global_status_table_locks_immediate` | Блокировки таблиц, полученные без ожидания. | untyped (счётчик) | операции | — | А |
| `mysql_global_status_table_locks_waited` | Блокировки таблиц, для получения которых пришлось ждать. | untyped (счётчик) | операции | — | А |
| `mysql_global_status_wsrep_cluster_size` | Количество участников компонента Galera. | untyped (значение) | узлы | — | А |
| `mysql_global_status_wsrep_cluster_status` | 1 — Primary, 0 — non-Primary или Disconnected в стандартном парсере mysqld_exporter. | untyped (значение) | 0/1 | — | А |
| `mysql_global_status_wsrep_connected` | Соединение узла с wsrep provider: 1 — подключён. | untyped (значение) | 0/1 | — | А |
| `mysql_global_status_wsrep_local_recv_queue` | Текущая очередь полученных write sets, ожидающих применения. | untyped (значение) | write sets | — | А |
| `mysql_global_status_wsrep_local_state` | Числовое состояние локального узла Galera; 4 — Synced. | untyped (значение) | код | — | А |
| `mysql_global_status_wsrep_ready` | Готовность узла Galera обслуживать запросы: 1 — готов. | untyped (значение) | 0/1 | — | А |
| `mysql_up` | 1 — exporter успешно подключился к СУБД и выполнил сбор. | gauge | 0/1 | — | А |

<a id="s12"></a>

## HAProxy

Схема native HAProxy зависит от версии пакета. Legacy имена `haproxy_up` и `haproxy_backend_up` вынесены в несовместимые зависимости. Семейства frontend/backend/server в native endpoint обычно используют label proxy.

| Название | Описание | Тип | Единица | Основные атрибуты | Основание |
|---|---|---|---|---|---|
| `haproxy_backend_http_responses_total` | Ответы backend по классу HTTP-кода. | counter | ответы | proxy, code | А |
| `haproxy_backend_http_total_time_average_seconds` | Скользящее среднее полного времени HTTP-запроса на backend; окно задаёт HAProxy. | gauge | с | proxy | А |
| `haproxy_frontend_http_responses_total` | Ответы frontend по классу HTTP-кода. | counter | ответы | proxy, code | А |
| `haproxy_server_check_failures_total` | Неуспешные проверки состояния backend-сервера. | counter | проверки | proxy, server | А |

<a id="s13"></a>

## RabbitMQ

Встроенный rabbitmq_prometheus по умолчанию может агрегировать статистику объектов. Наличие queue/vhost/channel labels зависит от режима и endpoint; они не гарантированы обычным `/metrics`.

| Название | Описание | Тип | Единица | Основные атрибуты | Основание |
|---|---|---|---|---|---|
| `rabbitmq_channel_messages_unroutable_dropped_total` | Не маршрутизированные и отброшенные сообщения. | counter | сообщения | channel / connection — зависит от режима | А |
| `rabbitmq_channel_messages_unroutable_returned_total` | Не маршрутизированные сообщения, возвращённые издателю. | counter | сообщения | channel / connection — зависит от режима | А |
| `rabbitmq_connections` | Открытые клиентские соединения RabbitMQ. | gauge | соединения | — | А |
| `rabbitmq_process_max_fds` | Лимит файловых дескрипторов Erlang VM. | gauge | дескрипторы | — | А |
| `rabbitmq_process_open_fds` | Открытые файловые дескрипторы Erlang VM. | gauge | дескрипторы | — | А |
| `rabbitmq_process_resident_memory_bytes` | Резидентная память процесса RabbitMQ/Erlang VM. | gauge | байты | — | А |
| `rabbitmq_queue_messages` | Сообщения в очереди: ready плюс unacknowledged. По умолчанию native endpoint может агрегировать объекты. | gauge | сообщения | vhost, queue — только при выдаче метрик по объектам | А |
| `rabbitmq_queue_messages_unacknowledged` | Доставленные, но ещё не подтверждённые сообщения. | gauge | сообщения | vhost, queue — при выдаче по объектам | А |
| `rabbitmq_resident_memory_limit_bytes` | Порог памяти RabbitMQ для срабатывания ограничения ресурсов. | gauge | байты | — | А |

<a id="s14"></a>

## Blackbox: проверки доступности

| Название | Описание | Тип | Единица | Основные атрибуты | Основание |
|---|---|---|---|---|---|
| `probe_dns_lookup_time_seconds` | Длительность разрешения имени. | gauge | с | — | С |
| `probe_duration_seconds` | Полная длительность проверки target. | gauge | с | — | С |
| `probe_http_content_length` | Объявленная длина HTTP-ответа; -1 при неизвестной длине. | gauge | байты | — | С |
| `probe_http_duration_seconds` | Длительности фаз HTTP-запроса. | gauge | с | phase | С |
| `probe_http_redirects` | Количество переходов HTTP redirect. | gauge | переходы | — | С |
| `probe_http_ssl` | Признак TLS в конечном HTTP-соединении. | gauge | 0/1 | — | С |
| `probe_http_status_code` | HTTP-код ответа при HTTP-проверке; при отсутствии ответа может быть 0. | gauge | код HTTP | — | А |
| `probe_http_version` | Версия HTTP, полученная от сервера. | gauge | номер версии | — | С |
| `probe_ip_protocol` | Использованный IP-протокол: 4 или 6. | gauge | 4/6 | — | С |
| `probe_ssl_earliest_cert_expiry` | Самое раннее время окончания действия сертификатов в проверяемой цепочке. | gauge | Unix, с | — | А |
| `probe_success` | Результат проверки конечного target: 1 — успешно, 0 — ошибка. | gauge | 0/1 | service, module, instance добавляет scrape config | А |

<a id="s15"></a>

## Consul

| Название | Описание | Тип | Единица | Основные атрибуты | Основание |
|---|---|---|---|---|---|
| `consul_catalog_service_node_healthy` | Результат проверок экземпляра сервиса в каталоге: 1 — здоров. | gauge | 0/1 | node, service_name, service_id | А, внешний |
| `consul_health_node_status` | Индикаторы статусов проверок узла; статус хранится в label status. | gauge | 0/1 | node, check, status | А, внешний |
| `consul_health_service_status` | Индикаторы статусов проверок сервиса. | gauge | 0/1 | node, service_name, service_id, check, status | А, внешний |
| `consul_raft_peers` | Число участников Raft по данным Consul. | gauge | узлы | — | А, внешний |
| `consul_serf_lan_member_status` | Код состояния участника Serf LAN; локальные правила считают 1 рабочим состоянием. | уточнить | код | member; прочие сверить | А, внешний |
| `consul_serf_wan_member_status` | Код состояния участника Serf WAN; локальные правила считают 1 рабочим состоянием. | уточнить | код | member; прочие сверить | А, внешний |
| `consul_up` | Успешность запроса exporter к Consul. | gauge | 0/1 | — | А, внешний |

<a id="s16"></a>

## Open vSwitch

| Название | Описание | Тип | Единица | Основные атрибуты | Основание |
|---|---|---|---|---|---|
| `ovs_interface_rx_crc_err` | Ошибки CRC входящих кадров интерфейса OVS. Правила применяют rate; фактический TYPE не задан архивом. | счётчик; TYPE сверить | события | name | А, внешний |
| `ovs_interface_rx_dropped` | Отброшенные пакеты приёма интерфейса OVS. Правила применяют rate; фактический TYPE не задан архивом. | счётчик; TYPE сверить | события | name | А, внешний |
| `ovs_interface_rx_errors` | Ошибки приёма интерфейса OVS. Правила применяют rate; фактический TYPE не задан архивом. | счётчик; TYPE сверить | события | name | А, внешний |
| `ovs_interface_rx_frame_err` | Ошибки выравнивания кадров интерфейса OVS. Правила применяют rate; фактический TYPE не задан архивом. | счётчик; TYPE сверить | события | name | А, внешний |
| `ovs_interface_rx_missed_errors` | Пропущенные входящие пакеты интерфейса OVS. Правила применяют rate; фактический TYPE не задан архивом. | счётчик; TYPE сверить | события | name | А, внешний |
| `ovs_interface_rx_over_err` | Переполнения приёмного буфера интерфейса OVS. Правила применяют rate; фактический TYPE не задан архивом. | счётчик; TYPE сверить | события | name | А, внешний |
| `ovs_interface_tx_dropped` | Отброшенные пакеты передачи интерфейса OVS. Правила применяют rate; фактический TYPE не задан архивом. | счётчик; TYPE сверить | события | name | А, внешний |
| `ovs_interface_tx_errors` | Ошибки передачи интерфейса OVS. Правила применяют rate; фактический TYPE не задан архивом. | счётчик; TYPE сверить | события | name | А, внешний |

<a id="s17"></a>

## Multipath

| Название | Описание | Тип | Единица | Основные атрибуты | Основание |
|---|---|---|---|---|---|
| `multipath_errors_total` | Накопленное число отказов путей, ожидаемое локальным правилом. | счётчик; TYPE сверить | события | uuid; прочие сверить | А, внешний |
| `multipath_info` | Метаданные multipath-устройства. В rules vend/prod со значением ## используются как признак проблемного DM. | уточнить | информационная | uuid, name, sysfs, vend, prod, paths | А, внешний |
| `multipath_path_status` | Состояние отдельного пути; в локальном правиле 0 означает отказ. | уточнить | 0/1 | uuid, идентификатор пути — сверить | А, внешний |
| `multipath_status` | Состояние multipath-устройства. Отсутствие путей определяется label paths="0", а не фиксированным значением метрики. | уточнить | код | uuid, paths | А, внешний |

<a id="s18"></a>

## Общие: процесс и сбор

| Название | Описание | Тип | Единица | Основные атрибуты | Основание |
|---|---|---|---|---|---|
| `process_cpu_seconds_total` | CPU-время процесса exporter/сервиса; не суммарное время CPU узла. | counter | с | — | А |
| `process_max_fds` | Лимит файловых дескрипторов процесса. | gauge | дескрипторы | — | А |
| `process_open_fds` | Открытые файловые дескрипторы процесса. | gauge | дескрипторы | — | А |
| `process_resident_memory_bytes` | Физическая память процесса, находящаяся в RAM. | gauge | байты | — | С |
| `process_start_time_seconds` | Время запуска процесса. | gauge | Unix, с | — | А |
| `process_virtual_memory_bytes` | Размер виртуального адресного пространства процесса. | gauge | байты | — | А |
| `process_virtual_memory_max_bytes` | Максимально доступный процессу объём виртуальной памяти. | gauge | байты | — | А |
| `scrape_duration_seconds` | Длительность scrape target, измеренная Prometheus. | gauge | с | job, instance | С |
| `scrape_samples_post_metric_relabeling` | Число samples после metric relabeling. | gauge | samples | job, instance | С |
| `scrape_samples_scraped` | Число samples до metric relabeling в последнем scrape. | gauge | samples | job, instance | С |
| `scrape_series_added` | Оценка числа рядов, впервые появившихся в scrape. | gauge | ряды | job, instance | С |
| `up` | Результат последнего scrape target, созданный самим Prometheus: 1 — scrape успешен. | gauge | 0/1 | job, instance | А |

<a id="s19"></a>

## Prometheus и Alertmanager

| Название | Описание | Тип | Единица | Основные атрибуты | Основание |
|---|---|---|---|---|---|
| `alertmanager_config_hash` | Числовой fingerprint загруженной конфигурации для сравнения реплик; не количество изменений. | gauge | безразмерная | — | А |
| `alertmanager_config_last_reload_successful` | Успешность последней загрузки конфигурации Alertmanager. | gauge | 0/1 | — | А |
| `alertmanager_notifications_failed_total` | Ошибки отправки уведомлений получателям. | counter | ошибки | integration; reason в отдельных версиях | А |
| `prometheus_config_last_reload_successful` | Успешность последней загрузки конфигурации Prometheus. | gauge | 0/1 | — | А |
| `prometheus_notifications_alertmanagers_discovered` | Обнаруженные Alertmanager для отправки уведомлений. | gauge | экземпляры | — | А |
| `prometheus_rule_evaluation_failures_total` | Ошибки вычисления recording/alerting rules. | counter | ошибки | rule_group | А |
| `prometheus_sd_discovered_targets` | Число targets, обнаруженных service discovery. | gauge | targets | config, name — зависит от версии | А |
| `prometheus_target_interval_length_seconds` | Распределение фактических интервалов между scrape. | summary | с | interval, quantile | А |
| `prometheus_target_scrapes_exceeded_sample_limit_total` | Scrape, отклонённые из-за превышения лимита samples. | counter | scrape | — | А |
| `prometheus_target_scrapes_sample_duplicate_timestamp_total` | Samples с конфликтующими значениями при одинаковом timestamp, отклонённые при scrape. | counter | samples | — | А |

<a id="s20"></a>

## cAdvisor: контейнеры

Представлены основные семейства cAdvisor 0.49.2. Полный upstream-перечень включает дополнительные отключённые категории; они описаны в [справочнике v0.49.2](https://github.com/google/cadvisor/blob/v0.49.2/docs/storage/prometheus.md). store_container_labels=false отключает перенос Docker labels, но не все служебные labels метрик.

| Название | Описание | Тип | Единица | Основные атрибуты | Основание |
|---|---|---|---|---|---|
| `container_cpu_cfs_periods_total` | Периоды квотирования CFS. | counter | периоды | id, name, image | С |
| `container_cpu_cfs_throttled_periods_total` | Периоды CFS с ограничением CPU. | counter | периоды | id, name, image | С |
| `container_cpu_cfs_throttled_seconds_total` | Время ограничения CPU контейнера. | counter | с | id, name, image | С |
| `container_cpu_system_seconds_total` | CPU-время контейнера в kernel mode. | counter | с | id, name, image | С |
| `container_cpu_usage_seconds_total` | CPU-время контейнера. | counter | с | id, name, image, cpu | С |
| `container_cpu_user_seconds_total` | CPU-время контейнера в user mode. | counter | с | id, name, image | С |
| `container_fs_limit_bytes` | Лимит/ёмкость файловой системы контейнера. | gauge | байты | id, name, image, device | С |
| `container_fs_reads_bytes_total` | Данные чтения контейнера с устройства. | counter | байты | id, name, image, device | С |
| `container_fs_usage_bytes` | Место, занятое файловой системой контейнера. | gauge | байты | id, name, image, device | С |
| `container_fs_writes_bytes_total` | Данные записи контейнера на устройство. | counter | байты | id, name, image, device | С |
| `container_last_seen` | Время последнего наблюдения контейнера cAdvisor. | gauge | Unix, с | id, name, image | А |
| `container_memory_cache` | Память кэша контейнера. | gauge | байты | id, name, image | С |
| `container_memory_rss` | RSS контейнера в интерпретации cAdvisor/cgroup. | gauge | байты | id, name, image | С |
| `container_memory_swap` | Использование swap контейнером. | gauge | байты | id, name, image | С |
| `container_memory_usage_bytes` | Текущее использование памяти cgroup, включая учитываемый кэш. | gauge | байты | id, name, image | С |
| `container_memory_working_set_bytes` | Working set по расчёту cAdvisor; обычно usage минус inactive_file, не чистый RSS. | gauge | байты | id, name, image | С |
| `container_network_receive_bytes_total` | Принятые данные контейнера. | counter | байты | id, name, image, interface | С |
| `container_network_receive_errors_total` | Ошибки сетевого приёма контейнера. | counter | ошибки | id, name, image, interface | С |
| `container_network_receive_packets_dropped_total` | Отброшенные входящие пакеты контейнера. | counter | пакеты | id, name, image, interface | С |
| `container_network_transmit_bytes_total` | Переданные данные контейнера. | counter | байты | id, name, image, interface | С |
| `container_network_transmit_errors_total` | Ошибки сетевой передачи контейнера. | counter | ошибки | id, name, image, interface | С |
| `container_network_transmit_packets_dropped_total` | Отброшенные исходящие пакеты контейнера. | counter | пакеты | id, name, image, interface | С |
| `container_spec_memory_limit_bytes` | Заданный предел памяти cgroup; отсутствие лимита требует отдельной интерпретации. | gauge | байты | id, name, image | С |

<a id="s21"></a>

## Memcached

| Название | Описание | Тип | Единица | Основные атрибуты | Основание |
|---|---|---|---|---|---|
| `memcached_commands_total` | Команды Memcached по типу и результату; hit/miss обычно в status, не в отдельных универсальных метриках. | counter | команды | command, status | В |
| `memcached_connections_total` | Все соединения с момента запуска. | counter | соединения | — | В |
| `memcached_current_bytes` | Объём сохранённых элементов кэша. | gauge | байты | — | В |
| `memcached_current_connections` | Текущие соединения. | gauge | соединения | — | В |
| `memcached_current_items` | Текущее число элементов кэша. | gauge | элементы | — | В |
| `memcached_items_evicted_total` | Элементы, вытесненные до истечения срока жизни. | counter | элементы | — | В |
| `memcached_items_reclaimed_total` | Истёкшие элементы, память которых повторно использована. | counter | элементы | — | В |
| `memcached_items_total` | Все сохранённые элементы с запуска. | counter | элементы | — | В |
| `memcached_limit_bytes` | Предел памяти кэша. | gauge | байты | — | В |
| `memcached_read_bytes_total` | Принятые Memcached данные. | counter | байты | — | В |
| `memcached_up` | Успешность обращения к Memcached. | gauge | 0/1 | — | В |
| `memcached_uptime_seconds` | Время работы Memcached с запуска. | counter | с | — | В |
| `memcached_written_bytes_total` | Переданные Memcached данные. | counter | байты | — | В |

<a id="s22"></a>

## Fluentd

| Название | Описание | Тип | Единица | Основные атрибуты | Основание |
|---|---|---|---|---|---|
| `fluentd_input_VM_unexpected_shutdown_records_total` | Счётчик лог-событий неожиданного выключения ВМ, ожидаемый PVS-rules. Конфигурация формирования в приложенных templates не найдена. | счётчик; TYPE сверить | события | domain / host — сверить реальную конфигурацию | А |
| `fluentd_input_amqp_errors_records_total` | Счётчик AMQP-ошибок из журналов, ожидаемый PVS-rules. Требуется соответствующий Fluentd filter/metric. | счётчик; TYPE сверить | события | labels лог-потока — сверить | А |
| `fluentd_output_status_buffer_queue_byte_size` | Объём очереди буфера. | TYPE зависит от версии | байты | plugin_id, type, Hostname | С |
| `fluentd_output_status_buffer_queue_length` | Число chunks в очереди буфера. | TYPE зависит от версии | chunks | plugin_id, type, Hostname | С |
| `fluentd_output_status_buffer_stage_byte_size` | Объём chunks, находящихся в staging. | TYPE зависит от версии | байты | plugin_id, type, Hostname | С |
| `fluentd_output_status_buffer_total_bytes` | Общий размер буфера output plugin. | TYPE зависит от версии | байты | plugin_id, type, Hostname | С |
| `fluentd_output_status_emit_count` | Вызовы emit output plugin. | счётчик; TYPE зависит от версии | вызовы | plugin_id, type, Hostname | С |
| `fluentd_output_status_emit_records` | Записи, прошедшие через output plugin. | счётчик; TYPE зависит от версии | записи | plugin_id, type, Hostname | С |
| `fluentd_output_status_flush_time_count` | Суммарная длительность flush; исходная единица — миллисекунды. | счётчик; TYPE зависит от версии | мс | plugin_id, type, Hostname | С |
| `fluentd_output_status_num_errors` | Ошибки output plugin. | счётчик; TYPE зависит от версии | ошибки | plugin_id, type, Hostname | С |
| `fluentd_output_status_retry_count` | Текущее число повторов отправки output plugin в цикле retry. | TYPE зависит от версии | попытки | plugin_id, type, Hostname | С |
| `fluentd_output_status_retry_wait` | Текущее время ожидания перед повторной отправкой. | TYPE зависит от версии | с | plugin_id, type, Hostname | С |
| `fluentd_output_status_write_count` | Операции записи output plugin. | счётчик; TYPE зависит от версии | операции | plugin_id, type, Hostname | С |

<a id="s23"></a>

## Elasticsearch exporter для OpenSearch

| Название | Описание | Тип | Единица | Основные атрибуты | Основание |
|---|---|---|---|---|---|
| `elasticsearch_cluster_health_active_primary_shards` | Число активных primary shards. | gauge | shards | cluster | В |
| `elasticsearch_cluster_health_active_shards` | Число активных shards, включая реплики. | gauge | shards | cluster | В |
| `elasticsearch_cluster_health_initializing_shards` | Число инициализирующихся shards. | gauge | shards | cluster | В |
| `elasticsearch_cluster_health_number_of_data_nodes` | Число узлов хранения данных. | gauge | узлы | cluster | В |
| `elasticsearch_cluster_health_number_of_nodes` | Число узлов кластера. | gauge | узлы | cluster | В |
| `elasticsearch_cluster_health_number_of_pending_tasks` | Задачи изменения cluster state, ожидающие выполнения. | gauge | задачи | cluster | В |
| `elasticsearch_cluster_health_relocating_shards` | Число переносимых shards. | gauge | shards | cluster | В |
| `elasticsearch_cluster_health_status` | Состояние кластера: отдельный ряд на green/yellow/red, активное состояние равно 1. | gauge | 0/1 | cluster, color | В |
| `elasticsearch_cluster_health_unassigned_shards` | Число shards, не назначенных узлам. | gauge | shards | cluster | В |
| `elasticsearch_filesystem_data_available_bytes` | Место файловой системы, доступное процессу узла. | gauge | байты | cluster, name, path | В |
| `elasticsearch_filesystem_data_size_bytes` | Размер файловой системы данных узла. | gauge | байты | cluster, name, path | В |
| `elasticsearch_jvm_memory_max_bytes` | Предел JVM-памяти узла. | gauge | байты | cluster, name, area | В |
| `elasticsearch_jvm_memory_used_bytes` | Использование JVM-памяти узла. | gauge | байты | cluster, name, area | В |

<a id="s24"></a>

## etcd

| Название | Описание | Тип | Единица | Основные атрибуты | Основание |
|---|---|---|---|---|---|
| `etcd_disk_backend_commit_duration_seconds` | Распределение времени commit backend. | histogram | с | le у bucket | С |
| `etcd_disk_wal_fsync_duration_seconds` | Распределение времени fsync WAL. | histogram | с | le у bucket | С |
| `etcd_mvcc_db_total_size_in_bytes` | Физический размер backend DB, включая свободные страницы. | gauge | байты | — | С |
| `etcd_mvcc_db_total_size_in_use_in_bytes` | Логический занятый объём backend DB. | gauge | байты | — | С |
| `etcd_server_has_leader` | 1 — участнику etcd известен лидер. | gauge | 0/1 | — | С |
| `etcd_server_is_leader` | 1 — текущий участник является лидером. | gauge | 0/1 | — | С |
| `etcd_server_leader_changes_seen_total` | Наблюдавшиеся смены лидера. | counter | события | — | С |
| `etcd_server_proposals_applied_total` | Применённые Raft proposals; накопленное значение, экспортируемое как gauge. | gauge | proposals | — | С |
| `etcd_server_proposals_committed_total` | Зафиксированные Raft proposals. В etcd исторически экспортируется как gauge. | gauge | proposals | — | С |
| `etcd_server_proposals_failed_total` | Неуспешные proposals. | counter | proposals | — | С |
| `etcd_server_proposals_pending` | Proposals, ещё ожидающие commit. | gauge | proposals | — | С |
| `etcd_server_quota_backend_bytes` | Квота размера backend DB. | gauge | байты | — | С |

<a id="s25"></a>

## Ceph mgr

| Название | Описание | Тип | Единица | Основные атрибуты | Основание |
|---|---|---|---|---|---|
| `ceph_cluster_total_bytes` | Полная raw-ёмкость кластера. | gauge | байты | — | С |
| `ceph_cluster_total_used_bytes` | Использованная ёмкость согласно соответствующему полю df Ceph; не приравнивать к логическому объёму ВМ. | gauge | байты | — | С |
| `ceph_cluster_total_used_raw_bytes` | Использованная raw-ёмкость по df Ceph. | gauge | байты | — | С |
| `ceph_health_status` | Общее состояние Ceph: 0 OK, 1 WARN, 2 ERR. | untyped | код | — | С |
| `ceph_osd_in` | Включение OSD в размещение данных: 1 — in. | untyped | 0/1 | ceph_daemon | С |
| `ceph_osd_up` | Работоспособность OSD: 1 — up. | untyped | 0/1 | ceph_daemon | С |
| `ceph_pg_total` | Количество placement groups в пуле Ceph. | gauge | PG | pool_id | С |
| `ceph_pool_bytes_used` | Использованное пространство пула по df. | gauge | байты | pool_id | С |
| `ceph_pool_max_avail` | Оценка пространства, доступного для записи в пул. | gauge | байты | pool_id | С |
| `ceph_pool_objects` | Количество объектов в пуле. | gauge | объекты | pool_id | С |
| `ceph_pool_stored` | Логический объём данных пула. | gauge | байты | pool_id | С |

<a id="s26"></a>

## Ironic: датчики bare metal

Источник — парсеры stable/2025.1, а не текущий master. В Redfish этой ветки power/fan/drive health кодируется 0 при OK и 1 иначе. Имена температур строятся из PhysicalContext, IPMI — из нормализованного имени сенсора. Таблица содержит типовые варианты, не закрытый список оборудования.

| Название | Описание | Тип | Единица | Основные атрибуты | Основание |
|---|---|---|---|---|---|
| `baremetal_current` | Электрический ток по данным IPMI. | gauge | А | node_uuid; идентификатор датчика | С |
| `baremetal_drive_status` | Состояние накопителя в Redfish-парсере stable/2025.1: 0 при health=OK, 1 при любом другом health. IPMI, где применимо, использует собственный парсер. | gauge | 0/1 | node_name, node_uuid, instance_uuid, sensor_id | С |
| `baremetal_exhaust_temp_celsius` | Температура выходящего воздуха в схеме IPMI. | gauge | °C | node_uuid; идентификатор датчика | С |
| `baremetal_fan_rpm` | Скорость вращения вентилятора в схеме IPMI. | gauge | об/мин | node_uuid; идентификатор датчика | С |
| `baremetal_fan_status` | Состояние вентилятора в Redfish-парсере stable/2025.1: 0 при health=OK, 1 при любом другом health. IPMI, где применимо, использует собственный парсер. | gauge | 0/1 | node_name, node_uuid, instance_uuid, sensor_id | С |
| `baremetal_inlet_temp_celsius` | Температура входящего воздуха в схеме IPMI. | gauge | °C | node_uuid; идентификатор датчика | С |
| `baremetal_last_payload_timestamp_seconds` | Время последнего полученного сообщения с датчиками. Позволяет отличить доступный exporter от свежих данных. | gauge | Unix, с | node_name, node_uuid, instance_uuid — по payload | С |
| `baremetal_power_status` | Состояние блока питания в Redfish-парсере stable/2025.1: 0 при health=OK, 1 при любом другом health. IPMI, где применимо, использует собственный парсер. | gauge | 0/1 | node_name, node_uuid, instance_uuid, sensor_id; зависит от парсера | С |
| `baremetal_pwr_consumption` | Потребляемая мощность по данным IPMI. | gauge | Вт | node_uuid; идентификатор датчика | С |
| `baremetal_temp_celsius` | Температура IPMI-датчика процессора/платы по нормализованному имени. | gauge | °C | node_uuid, sensor / sensor_id — зависит от парсера | С |
| `baremetal_temp_cpu_celsius` | Температура CPU в схеме Redfish; имя строится из PhysicalContext датчика. | gauge | °C | node_name, node_uuid, instance_uuid, sensor_id | С |
| `baremetal_temp_exhaust_celsius` | Температура выходящего воздуха в схеме Redfish; имя строится из PhysicalContext датчика. | gauge | °C | node_name, node_uuid, instance_uuid, sensor_id | С |
| `baremetal_temp_intake_celsius` | Температура входящего воздуха в схеме Redfish; имя строится из PhysicalContext датчика. | gauge | °C | node_name, node_uuid, instance_uuid, sensor_id | С |
| `baremetal_temp_memory_celsius` | Температура модуля памяти в схеме Redfish; имя строится из PhysicalContext датчика. | gauge | °C | node_name, node_uuid, instance_uuid, sensor_id | С |
| `baremetal_temp_powersupply_celsius` | Температура блока питания в схеме Redfish; имя строится из PhysicalContext датчика. | gauge | °C | node_name, node_uuid, instance_uuid, sensor_id | С |
| `baremetal_temp_systemboard_celsius` | Температура системной платы в схеме Redfish; имя строится из PhysicalContext датчика. | gauge | °C | node_name, node_uuid, instance_uuid, sensor_id | С |
| `baremetal_voltage_volts` | Напряжение, возвращённое IPMI-датчиком. | gauge | В | node_uuid; идентификатор датчика | С |

<a id="s27"></a>

## Вычисляемые метрики: определения есть

Все 26 уникальных recording names из PVS-rules и watcher.rules.j2. Их тип — результат PromQL, без собственного exporter TYPE. Формулы могут не выдавать ряд при отсутствующих входах или несовпадающих labels.

| Название | Описание | Тип | Единица | Основные атрибуты | Основание |
|---|---|---|---|---|---|
| `az:node_cpu_seconds_total:avg` | Средняя занятость CPU по zone: 100 минус процент idle. Это процент, хотя имя содержит seconds_total. | recording rule | % | zone | Р |
| `az:node_network_errors_total:sum` | Суммарная скорость сетевых ошибок приёма и передачи по zone. | recording rule | ошибки/с | zone | Р |
| `az:node_network_packets_drop_percent:sum` | Сумма долей потерь отдельно по передаче и приёму, умноженная на 100; не единая доля от общего трафика. | recording rule | % | zone | Р |
| `az:node_network_receive_bytes_total:avg` | Средняя скорость приёма выбранных интерфейсов по zone. | recording rule | байты/с | zone | Р |
| `az:node_network_receive_drop_total:sum` | Суммарная скорость потерь приёма выбранных интерфейсов по zone. | recording rule | пакеты/с | zone | Р |
| `az:node_network_receive_packets_total:sum` | Суммарная скорость приёма пакетов по zone. | recording rule | пакеты/с | zone | Р |
| `az:node_network_throughput_bytes_total:sum` | Сумма скоростей приёма и передачи выбранных интерфейсов по zone. | recording rule | байты/с | zone | Р |
| `az:node_network_transmit_bytes_total:avg` | Средняя скорость передачи выбранных интерфейсов по zone. | recording rule | байты/с | zone | Р |
| `az:node_network_transmit_drop_total:sum` | Суммарная скорость потерь передачи выбранных интерфейсов по zone. | recording rule | пакеты/с | zone | Р |
| `az:node_network_transmit_packets_total:sum` | Суммарная скорость передачи пакетов по zone. | recording rule | пакеты/с | zone | Р |
| `az:openstack_nova_memory_available_bytes_oversubscription:sum` | RAM-ёмкость AZ с Placement allocation ratio класса MEMORY_MB. | recording rule | байты | availability_zone | Р |
| `az:openstack_nova_memory_free:sum` | Остаток RAM-ёмкости с overcommit после вычитания занятой RAM. | recording rule | байты | availability_zone | Р |
| `az:openstack_nova_memory_used_bytes:sum` | RAM, учтённая Nova как занятая, по AZ. В файле определена дважды. | recording rule | байты | availability_zone | Р |
| `az:openstack_nova_memory_used_percent:avg` | Среднее по узлам отношение RAM used/available × 100; не взвешенное по размеру RAM. | recording rule | % | availability_zone | Р |
| `az:openstack_nova_vcpus_available_oversubscription:sum` | CPU-ёмкость по AZ с умножением на Placement allocation ratio класса VCPU. | recording rule | vCPU | availability_zone | Р |
| `az:openstack_nova_vcpus_free:sum` | Разность CPU-ёмкости с overcommit и занятых vCPU; может быть отрицательной. | recording rule | vCPU | availability_zone | Р |
| `az:openstack_nova_vcpus_used:sum` | Занятые vCPU, суммированные по availability_zone. | recording rule | vCPU | availability_zone | Р |
| `ceilometer_cpu` | Эмуляция CPU-метрики Watcher: irate времени CPU домена / число vCPU × 100. Фильтр user_name="admin" ограничивает ВМ. | recording rule | % | domain, resource, instance_id, instance_name, project_name; унаследованные labels | Р |
| `ceilometer_memory_usage` | Эмуляция RAM-метрики Watcher из used_percent libvirt; применяется тот же фильтр user_name="admin". | recording rule | % | domain, resource, instance_id, instance_name, project_name; унаследованные labels | Р |
| `domain:libvirt_domain_block_stats_latency_read_total_max:top5` | Пять ВМ с наибольшей средней задержкой чтения худшего диска; fallback может дать другую единицу. | recording rule | с/операцию; fallback — операции/с | domain, hypervisor_hostname, uuid, availability_zone | Р |
| `domain:libvirt_domain_block_stats_latency_write_total_max:top5` | Пять ВМ с наибольшей средней задержкой записи худшего диска; в выражении есть fallback на скорость запросов. | recording rule | с/операцию; fallback — операции/с | domain, hypervisor_hostname, uuid, availability_zone | Р |
| `domain:libvirt_domain_block_stats_read_block_size:max` | Максимальный по дискам средний размер чтения ВМ; fallback нарушает единство единиц. | recording rule | байты/операцию; fallback — операции/с | domain, uuid, instance_name, hypervisor_hostname, availability_zone | Р |
| `domain:libvirt_domain_block_stats_write_block_size:max` | Максимальный по дискам средний размер записи ВМ. При отсутствии положительного отношения есть fallback на скорость запросов. | recording rule | байты/операцию; fallback — операции/с | domain, uuid, instance_name, hypervisor_hostname, availability_zone | Р |
| `domain:libvirt_domain_interface_stats_bytes_total_usage_percent:sum` | Сумма RX+TX скоростей интерфейсов ВМ относительно скорости выбранного bond1/external хоста × 100. | recording rule | % | domain, instance, node_address; результат join | Р |
| `region:libvirt_domain_block_stats_capacity_bytes:sum` | Сумма ёмкостей всех видимых дисков ВМ. Выражение sum не сохраняет region и может учитывать дублирующие targets. | recording rule | байты | — | Р |
| `vm:libvirt_domain_vcpu_delay_seconds_total:rate5m` | Средняя скорость роста задержки vCPU за irate[5m], умноженная на 100 и дополненная данными Nova. | recording rule | % | domain, instance_name, uuid, availability_zone, hypervisor_hostname, name | Р |

<a id="s28"></a>

## Несовместимые зависимости архивов

Эти имена встречаются в архиве, но отсутствуют в указанной vanilla-версии либо относятся к другому exporter. Они сохранены для аудита зависимостей, а не включены в подтверждённую схему.

| Название | Описание | Тип | Единица | Основные атрибуты | Основание |
|---|---|---|---|---|---|
| `haproxy_backend_up` | Доступность backend в legacy-схеме. Для native HAProxy имя/код состояния может отличаться. | уточнить | 0/1 | backend / proxy — зависит от реализации | Н |
| `haproxy_up` | Успешность сбора в отдельном legacy haproxy_exporter. В архиве включён native endpoint HAProxy, где наличие этого имени не гарантировано. | уточнить | 0/1 | — | Н |
| `libvirt_domain_block_meta` | Метаданные диска домена: источник, устройство и параметры подключения; требуется совместимая сборка exporter. Имя не объявлено в выбранном ванильном exporter. | нет в выбранной vanilla-версии | 1 | domain, target_device, source_file; прочие зависят от версии | Н |
| `libvirt_domain_info_meta` | Метаданные домена, ожидаемые PVS-правилами; отличается от openstack_info и зависит от сборки exporter. Имя не объявлено в выбранном ванильном exporter. | нет в выбранной vanilla-версии | 1 | domain, uuid, instance_name; прочие зависят от версии | Н |
| `libvirt_domain_info_vstate` | Вариант метрики состояния домена из другого семейства libvirt exporter. Точное кодирование требует проверки. Имя не объявлено в выбранном ванильном exporter. | нет в выбранной vanilla-версии | код | domain | Н |
| `node_network_address_info` | Старое имя в дашборде. В Node exporter 1.8.2 сведения интерфейса предоставляет node_network_info. | нет в Node exporter 1.8.2 | 1 | device, address, broadcast | Н |
| `node_pressure_irq_stalled_seconds_total` | Имя из дашборда, отсутствующее в pressure collector Node exporter 1.8.2. | нет в Node exporter 1.8.2 | с | — | Н |
| `openstack_cinder_snapshot` | Метрика отдельного snapshot, ожидаемая локальными правилами; полное описание TYPE/значения в архиве отсутствует. Имя не объявлено в выбранном ванильном exporter. | нет в выбранной vanilla-версии | уточнить | id, status и другие — сверить сборку | Н |
| `openstack_nova_server_net_info` | Информация о сетевых подключениях ВМ из расширения exporter, на которую ссылается дашборд. Имя не объявлено в выбранном ванильном exporter. | нет в выбранной vanilla-версии | информационная | uuid и сетевые labels — сверить сборку | Н |
| `rabbitmq_node_mem_limit` | Лимит памяти узла в схеме стороннего/старого exporter. | уточнить | байты | node — зависит от exporter | Н |
| `rabbitmq_node_mem_used` | Память узла в схеме стороннего/старого exporter. Наличие в native endpoint не подтверждено. | уточнить | байты | node — зависит от exporter | Н |
| `rabbitmq_partitions` | Сетевые разделения кластера в ожидаемой правилами схеме. Тип/labels зависят от exporter. | уточнить | разделения | node — сверить | Н |
| `rabbitmq_running` | Признак работающего узла из ожидаемой правилами схемы; native endpoint может использовать другие метрики. | уточнить | 0/1 | node — сверить | Н |
| `rabbitmq_up` | Успешность обращения внешнего exporter к RabbitMQ; не равнозначна автоматически создаваемой метрике up. | уточнить | 0/1 | — | Н |

<a id="s29"></a>

## Зависимости дашборда: определения отсутствуют

Эти имена/шаблоны используются dashboards, но соответствующие record definitions в приложенных rules отсутствуют. Пояснения ниже — назначение, предполагаемое по имени и панели; формулы, типы и единицы не подтверждены.

| Название | Описание | Тип | Единица | Основные атрибуты | Основание |
|---|---|---|---|---|---|
| `node:cpu_oversubscription:ratio` | Предполагаемый коэффициент CPU overcommit узла. | не определён | коэффициент? | по запросам дашборда; полный набор неизвестен | Н |
| `node:cpu_usage_percent:sum` | Предполагаемая загрузка CPU узла. | не определён | %? | по запросам дашборда; полный набор неизвестен | Н |
| `node:fc_port_usage_gbit:max_tx_rx` | Предполагаемый максимум скорости FC по RX/TX. | не определён | Гбит/с? | по запросам дашборда; полный набор неизвестен | Н |
| `node:fc_port_usage_percent:max_tx_rx` | Предполагаемая относительная загрузка FC по RX/TX. | не определён | %? | по запросам дашборда; полный набор неизвестен | Н |
| `node:fc_speed:sum` | Предполагаемая агрегированная скорость FC-портов. | не определён | уточнить | по запросам дашборда; полный набор неизвестен | Н |
| `node:host_state:sum` | Предполагаемое агрегированное состояние хоста. | не определён | код? | по запросам дашборда; полный набор неизвестен | Н |
| `node:memory_total_gb:sum` | Предполагаемый полный объём RAM узла. | не определён | GB/GiB — уточнить | по запросам дашборда; полный набор неизвестен | Н |
| `node:memory_usage_percent:sum` | Предполагаемое использование RAM узла. | не определён | %? | по запросам дашборда; полный набор неизвестен | Н |
| `node:network_speed:sum` | Предполагаемая суммарная скорость сетевых линков. | не определён | уточнить | по запросам дашборда; полный набор неизвестен | Н |
| `node:network_usage_bytes:max_tx_rx` | Предполагаемый максимум сетевой скорости RX/TX. | не определён | байты/с? | по запросам дашборда; полный набор неизвестен | Н |
| `node:network_usage_percent:max_tx_rx` | Предполагаемая относительная загрузка сети по RX/TX. | не определён | %? | по запросам дашборда; полный набор неизвестен | Н |
| `node:number_running_vms:sum` | Предполагаемое число работающих ВМ на хосте. | не определён | ВМ? | по запросам дашборда; полный набор неизвестен | Н |
| `node:pcpu_count:sum` | Предполагаемое число физических CPU-потоков/ядер; точная трактовка без формулы неизвестна. | не определён | CPU? | по запросам дашборда; полный набор неизвестен | Н |
| `node:vcpu_used_count:sum` | Предполагаемое число занятых vCPU узла. | не определён | vCPU? | по запросам дашборда; полный набор неизвестен | Н |
| `openstack:nova:metadata:extended` | Предполагаемые расширенные метаданные Nova. | не определён | информационная? | по запросам дашборда; полный набор неизвестен | Н |
| `vm:libvirt_domain_block_capacity_gb:sum` | Предполагаемая суммарная ёмкость дисков ВМ. | не определён | GB/GiB — уточнить | по запросам дашборда; полный набор неизвестен | Н |
| `vm:libvirt_domain_block_stats_read_bytes_total:sum` | Предполагаемый агрегат чтения ВМ. Нельзя определить, сумма это или скорость, только по имени. | не определён | уточнить | по запросам дашборда; полный набор неизвестен | Н |
| `vm:libvirt_domain_block_stats_read_requests_total:sum` | Предполагаемый агрегат запросов чтения ВМ; формула отсутствует. | не определён | уточнить | по запросам дашборда; полный набор неизвестен | Н |
| `vm:libvirt_domain_block_stats_write_bytes_total:sum` | Предполагаемый агрегат записи ВМ; формула отсутствует. | не определён | уточнить | по запросам дашборда; полный набор неизвестен | Н |
| `vm:libvirt_domain_block_stats_write_requests_total:sum` | Предполагаемый агрегат запросов записи ВМ; формула отсутствует. | не определён | уточнить | по запросам дашборда; полный набор неизвестен | Н |
| `vm:libvirt_domain_read_latency:$operators` | Шаблон имени с подстановкой переменной Grafana $operators; это не буквальное имя готовой метрики. | не определён | уточнить | по запросам дашборда; полный набор неизвестен | Н |
| `vm:libvirt_domain_vcpu_delay_seconds_total:$operators` | Шаблон имени агрегата задержки vCPU с переменной $operators. | не определён | уточнить | по запросам дашборда; полный набор неизвестен | Н |
| `vm:libvirt_domain_vcpu_delay_seconds_total:max` | Предполагаемый максимум задержки vCPU; формула отсутствует. | не определён | уточнить | по запросам дашборда; полный набор неизвестен | Н |
| `vm:libvirt_domain_vcpu_time_seconds_total:$operators` | Шаблон имени агрегата времени vCPU с переменной $operators. | не определён | уточнить | по запросам дашборда; полный набор неизвестен | Н |
| `vm:libvirt_domain_write_latency:max` | Предполагаемая максимальная задержка записи ВМ; формула отсутствует. | не определён | с/операцию? | по запросам дашборда; полный набор неизвестен | Н |
| `vm:metadata` | Метаданные ВМ для dashboard joins; определение и генератор отсутствуют. | не определён | информационная? | по запросам дашборда; полный набор неизвестен | Н |

<a id="s30"></a>

## Ошибочное имя

Опечатка сохранена ровно в том виде, как она находится в исходном dashboard; штатным именем exporter не является.

| Название | Описание | Тип | Единица | Основные атрибуты | Основание |
|---|---|---|---|---|---|
| `node_network_trasmit_errs_total` | Опечатка в запросе дашборда: пропущена n в transmit. Правильное стандартное имя — node_network_transmit_errs_total. | ошибочное имя | — | — | Н |

<a id="reference-catalogs"></a>

## Расширенные каталоги из эталонных источников

Ниже — дополнение к русским таблицам: все **оставшиеся** имена из выбранных эталонных каталогов, без повторения уже описанных выше. Оригинальное HELP/описание сохранено на английском для точной сверки с кодом. Типы здесь — заявленные источником; пустой набор labels не достраивается по предположению.

Это не объединённая экспозиция установленного узла. В частности, Node fixture запускает широкий набор collectors на тестовых данных и не задаёт полный набор полей всех возможных Linux-ядер. Некоторые настоящие метрики (например, MemAvailable, filesystem, timex) проверены по коду и уже описаны в основной части, хотя отсутствуют в этой fixture.

### Node exporter 1.8.2 — эталонная Linux fixture

[Источник](https://github.com/prometheus/node_exporter/blob/v1.8.2/collector/fixtures/e2e-output.txt). В исходном каталоге 998 имён; здесь 798 дополнительных строк, остальные уже описаны выше.

<details>
<summary>Развернуть полный дополнительный перечень</summary>

| Название | Исходное описание / HELP | Тип | Атрибуты из источника |
|---|---|---|---|
| `node_bcache_active_journal_entries` | Number of journal entries that are newer than the index. | gauge | uuid |
| `node_bcache_average_key_size_sectors` | Average data per key in the btree (sectors). | gauge | uuid |
| `node_bcache_btree_cache_size_bytes` | Amount of memory currently used by the btree cache. | gauge | uuid |
| `node_bcache_btree_nodes` | Total nodes in the btree. | gauge | uuid |
| `node_bcache_btree_read_average_duration_seconds` | Average btree read duration. | gauge | uuid |
| `node_bcache_bypassed_bytes_total` | Amount of IO (both reads and writes) that has bypassed the cache. | counter | backing_device, uuid |
| `node_bcache_cache_available_percent` | Percentage of cache device without dirty data, usable for writeback (may contain clean cached data). | gauge | uuid |
| `node_bcache_cache_bypass_hits_total` | Hits for IO intended to skip the cache. | counter | backing_device, uuid |
| `node_bcache_cache_bypass_misses_total` | Misses for IO intended to skip the cache. | counter | backing_device, uuid |
| `node_bcache_cache_hits_total` | Hits counted per individual IO as bcache sees them. | counter | backing_device, uuid |
| `node_bcache_cache_miss_collisions_total` | Instances where data insertion from cache miss raced with write (data already present). | counter | backing_device, uuid |
| `node_bcache_cache_misses_total` | Misses counted per individual IO as bcache sees them. | counter | backing_device, uuid |
| `node_bcache_cache_read_races_total` | Counts instances where while data was being read from the cache, the bucket was reused and invalidated - i.e. where the pointer was stale after the read completed. | counter | uuid |
| `node_bcache_cache_readaheads_total` | Count of times readahead occurred. | counter | backing_device, uuid |
| `node_bcache_congested` | Congestion. | gauge | uuid |
| `node_bcache_dirty_data_bytes` | Amount of dirty data for this backing device in the cache. | gauge | backing_device, uuid |
| `node_bcache_dirty_target_bytes` | Current dirty data target threshold for this backing device in bytes. | gauge | backing_device, uuid |
| `node_bcache_io_errors` | Number of errors that have occurred, decayed by io_error_halflife. | gauge | cache_device, uuid |
| `node_bcache_metadata_written_bytes_total` | Sum of all non data writes (btree writes and all other metadata). | counter | cache_device, uuid |
| `node_bcache_priority_stats_metadata_percent` | Bcache's metadata overhead. | gauge | cache_device, uuid |
| `node_bcache_priority_stats_unused_percent` | The percentage of the cache that doesn't contain any data. | gauge | cache_device, uuid |
| `node_bcache_root_usage_percent` | Percentage of the root btree node in use (tree depth increases if too high). | gauge | uuid |
| `node_bcache_tree_depth` | Depth of the btree. | gauge | uuid |
| `node_bcache_writeback_change` | Last writeback rate change step for this backing device. | gauge | backing_device, uuid |
| `node_bcache_writeback_rate` | Current writeback rate for this backing device in bytes. | gauge | backing_device, uuid |
| `node_bcache_writeback_rate_integral_term` | Current result of integral controller, part of writeback rate | gauge | backing_device, uuid |
| `node_bcache_writeback_rate_proportional_term` | Current result of proportional controller, part of writeback rate | gauge | backing_device, uuid |
| `node_bcache_written_bytes_total` | Sum of all data that has been written to the cache. | counter | cache_device, uuid |
| `node_btrfs_allocation_ratio` | Data allocation ratio for a layout/data type | gauge | block_group_type, mode, uuid |
| `node_btrfs_device_size_bytes` | Size of a device that is part of the filesystem. | gauge | device, uuid |
| `node_btrfs_global_rsv_size_bytes` | Size of global reserve. | gauge | uuid |
| `node_btrfs_info` | Filesystem information | gauge | label, uuid |
| `node_btrfs_reserved_bytes` | Amount of space reserved for a data type | gauge | block_group_type, uuid |
| `node_btrfs_size_bytes` | Amount of space allocated for a layout/data type | gauge | block_group_type, mode, uuid |
| `node_btrfs_used_bytes` | Amount of used space by a layout/data type | gauge | block_group_type, mode, uuid |
| `node_buddyinfo_blocks` | Count of free blocks according to size. | gauge | node, size, zone |
| `node_cgroups_cgroups` | Current cgroup number of the subsystem. | gauge | subsys_name |
| `node_cgroups_enabled` | Current cgroup number of the subsystem. | gauge | subsys_name |
| `node_cpu_bug_info` | The `bugs` field of CPU information from /proc/cpuinfo taken from the first core. | gauge | bug |
| `node_cpu_flag_info` | The `flags` field of CPU information from /proc/cpuinfo taken from the first core. | gauge | flag |
| `node_cpu_info` | CPU information from /proc/cpuinfo. | gauge | cachesize, core, cpu, family, microcode, model, model_name, package, stepping, vendor |
| `node_cpu_isolated` | Whether each core is isolated, information from /sys/devices/system/cpu/isolated. | gauge | cpu |
| `node_cpu_package_throttles_total` | Number of times this CPU package has been throttled. | counter | package |
| `node_cpu_vulnerabilities_info` | Details of each CPU vulnerability reported by sysfs. The value of the series is an int encoded state of the vulnerability. The same state is stored as a string in the label | gauge | codename, mitigation, state |
| `node_disk_ata_rotation_rate_rpm` | ATA disk rotation rate in RPMs (0 for SSDs). | gauge | device |
| `node_disk_ata_write_cache` | ATA disk has a write cache. | gauge | device |
| `node_disk_ata_write_cache_enabled` | ATA disk has its write cache enabled. | gauge | device |
| `node_disk_device_mapper_info` | Info about disk device mapper. | gauge | device, lv_layer, lv_name, name, uuid, vg_name |
| `node_disk_filesystem_info` | Info about disk filesystem. | gauge | device, type, usage, uuid, version |
| `node_disk_info` | Info of /sys/block/<block_device>. | gauge | device, major, minor, model, path, revision, serial, wwn |
| `node_dmi_info` | A metric with a constant '1' value labeled by bios_date, bios_release, bios_vendor, bios_version, board_asset_tag, board_name, board_serial, board_vendor, board_version, chassis_asset_tag, chassis_serial, chassis_vendor, chassis_version, product_family, product_name, product_serial, product_sku, product_uuid, product_version, system_vendor if provided by DMI. | gauge | bios_date, bios_release, bios_vendor, bios_version, board_name, board_serial, board_vendor, board_version, chassis_asset_tag, chassis_serial, chassis_vendor, chassis_version, product_family, product_name, product_serial, product_sku, product_uuid, product_version, system_vendor |
| `node_drbd_activitylog_writes_total` | Number of updates of the activity log area of the meta data. | counter | device |
| `node_drbd_application_pending` | Number of block I/O requests forwarded to DRBD, but not yet answered by DRBD. | gauge | device |
| `node_drbd_bitmap_writes_total` | Number of updates of the bitmap area of the meta data. | counter | device |
| `node_drbd_connected` | Whether DRBD is connected to the peer. | gauge | device |
| `node_drbd_disk_read_bytes_total` | Net data read from local hard disk; in bytes. | counter | device |
| `node_drbd_disk_state_is_up_to_date` | Whether the disk of the node is up to date. | gauge | device, node |
| `node_drbd_disk_written_bytes_total` | Net data written on local hard disk; in bytes. | counter | device |
| `node_drbd_epochs` | Number of Epochs currently on the fly. | gauge | device |
| `node_drbd_local_pending` | Number of open requests to the local I/O sub-system. | gauge | device |
| `node_drbd_network_received_bytes_total` | Total number of bytes received via the network. | counter | device |
| `node_drbd_network_sent_bytes_total` | Total number of bytes sent via the network. | counter | device |
| `node_drbd_node_role_is_primary` | Whether the role of the node is in the primary state. | gauge | device, node |
| `node_drbd_out_of_sync_bytes` | Amount of data known to be out of sync; in bytes. | gauge | device |
| `node_drbd_remote_pending` | Number of requests sent to the peer, but that have not yet been answered by the latter. | gauge | device |
| `node_drbd_remote_unacknowledged` | Number of requests received by the peer via the network connection, but that have not yet been answered. | gauge | device |
| `node_edac_csrow_correctable_errors_total` | Total correctable memory errors for this csrow. | counter | controller, csrow |
| `node_edac_csrow_uncorrectable_errors_total` | Total uncorrectable memory errors for this csrow. | counter | controller, csrow |
| `node_exporter_build_info` | A metric with a constant '1' value labeled by version, revision, branch, goversion from which node_exporter was built, and the goos and goarch for the build. | gauge | — |
| `node_fibrechannel_dumped_frames_total` | Number of dumped frames | counter | fc_host |
| `node_fibrechannel_fcp_packet_aborts_total` | Number of aborted packets | counter | fc_host |
| `node_fibrechannel_invalid_crc_total` | Invalid Cyclic Redundancy Check count | counter | fc_host |
| `node_fibrechannel_invalid_tx_words_total` | Number of invalid words transmitted by host port | counter | fc_host |
| `node_fibrechannel_rx_words_total` | Number of words received by host port | counter | fc_host |
| `node_fibrechannel_seconds_since_last_reset_total` | Number of seconds since last host port reset | counter | fc_host |
| `node_fibrechannel_tx_words_total` | Number of words transmitted by host port | counter | fc_host |
| `node_hwmon_fan_alarm` | Hardware sensor alarm status (fan) | gauge | chip, sensor |
| `node_hwmon_fan_beep_enabled` | Hardware monitor sensor has beeping enabled | gauge | chip, sensor |
| `node_hwmon_fan_manual` | Hardware monitor fan element manual | gauge | chip, sensor |
| `node_hwmon_fan_max_rpm` | Hardware monitor for fan revolutions per minute (max) | gauge | chip, sensor |
| `node_hwmon_fan_output` | Hardware monitor fan element output | gauge | chip, sensor |
| `node_hwmon_fan_pulses` | Hardware monitor fan element pulses | gauge | chip, sensor |
| `node_hwmon_fan_target_rpm` | Hardware monitor for fan revolutions per minute (target) | gauge | chip, sensor |
| `node_hwmon_fan_tolerance` | Hardware monitor fan element tolerance | gauge | chip, sensor |
| `node_hwmon_in_alarm` | Hardware sensor alarm status (in) | gauge | chip, sensor |
| `node_hwmon_in_beep_enabled` | Hardware monitor sensor has beeping enabled | gauge | chip, sensor |
| `node_hwmon_in_max_volts` | Hardware monitor for voltage (max) | gauge | chip, sensor |
| `node_hwmon_in_min_volts` | Hardware monitor for voltage (min) | gauge | chip, sensor |
| `node_hwmon_in_volts` | Hardware monitor for voltage (input) | gauge | chip, sensor |
| `node_hwmon_intrusion_alarm` | Hardware sensor alarm status (intrusion) | gauge | chip, sensor |
| `node_hwmon_intrusion_beep_enabled` | Hardware monitor sensor has beeping enabled | gauge | chip, sensor |
| `node_hwmon_pwm_auto_point1_pwm` | Hardware monitor pwm element auto_point1_pwm | gauge | chip, sensor |
| `node_hwmon_pwm_auto_point1_temp` | Hardware monitor pwm element auto_point1_temp | gauge | chip, sensor |
| `node_hwmon_pwm_auto_point2_pwm` | Hardware monitor pwm element auto_point2_pwm | gauge | chip, sensor |
| `node_hwmon_pwm_auto_point2_temp` | Hardware monitor pwm element auto_point2_temp | gauge | chip, sensor |
| `node_hwmon_pwm_auto_point3_pwm` | Hardware monitor pwm element auto_point3_pwm | gauge | chip, sensor |
| `node_hwmon_pwm_auto_point3_temp` | Hardware monitor pwm element auto_point3_temp | gauge | chip, sensor |
| `node_hwmon_pwm_auto_point4_pwm` | Hardware monitor pwm element auto_point4_pwm | gauge | chip, sensor |
| `node_hwmon_pwm_auto_point4_temp` | Hardware monitor pwm element auto_point4_temp | gauge | chip, sensor |
| `node_hwmon_pwm_auto_point5_pwm` | Hardware monitor pwm element auto_point5_pwm | gauge | chip, sensor |
| `node_hwmon_pwm_auto_point5_temp` | Hardware monitor pwm element auto_point5_temp | gauge | chip, sensor |
| `node_hwmon_pwm_crit_temp_tolerance` | Hardware monitor pwm element crit_temp_tolerance | gauge | chip, sensor |
| `node_hwmon_pwm_enable` | Hardware monitor pwm element enable | gauge | chip, sensor |
| `node_hwmon_pwm_floor` | Hardware monitor pwm element floor | gauge | chip, sensor |
| `node_hwmon_pwm_mode` | Hardware monitor pwm element mode | gauge | chip, sensor |
| `node_hwmon_pwm_start` | Hardware monitor pwm element start | gauge | chip, sensor |
| `node_hwmon_pwm_step_down_time` | Hardware monitor pwm element step_down_time | gauge | chip, sensor |
| `node_hwmon_pwm_step_up_time` | Hardware monitor pwm element step_up_time | gauge | chip, sensor |
| `node_hwmon_pwm_stop_time` | Hardware monitor pwm element stop_time | gauge | chip, sensor |
| `node_hwmon_pwm_target_temp` | Hardware monitor pwm element target_temp | gauge | chip, sensor |
| `node_hwmon_pwm_temp_sel` | Hardware monitor pwm element temp_sel | gauge | chip, sensor |
| `node_hwmon_pwm_temp_tolerance` | Hardware monitor pwm element temp_tolerance | gauge | chip, sensor |
| `node_hwmon_pwm_weight_duty_base` | Hardware monitor pwm element weight_duty_base | gauge | chip, sensor |
| `node_hwmon_pwm_weight_duty_step` | Hardware monitor pwm element weight_duty_step | gauge | chip, sensor |
| `node_hwmon_pwm_weight_temp_sel` | Hardware monitor pwm element weight_temp_sel | gauge | chip, sensor |
| `node_hwmon_pwm_weight_temp_step` | Hardware monitor pwm element weight_temp_step | gauge | chip, sensor |
| `node_hwmon_pwm_weight_temp_step_base` | Hardware monitor pwm element weight_temp_step_base | gauge | chip, sensor |
| `node_hwmon_pwm_weight_temp_step_tol` | Hardware monitor pwm element weight_temp_step_tol | gauge | chip, sensor |
| `node_hwmon_sensor_label` | Label for given chip and sensor | gauge | chip, label, sensor |
| `node_infiniband_info` | Non-numeric data from /sys/class/infiniband/<device>, value is always 1. | gauge | board_id, device, firmware_version, hca_type |
| `node_infiniband_legacy_data_received_bytes_total` | Number of data octets received on all links | counter | device, port |
| `node_infiniband_legacy_data_transmitted_bytes_total` | Number of data octets transmitted on all links | counter | device, port |
| `node_infiniband_legacy_multicast_packets_received_total` | Number of multicast packets received | counter | device, port |
| `node_infiniband_legacy_multicast_packets_transmitted_total` | Number of multicast packets transmitted | counter | device, port |
| `node_infiniband_legacy_packets_received_total` | Number of data packets received on all links | counter | device, port |
| `node_infiniband_legacy_packets_transmitted_total` | Number of data packets received on all links | counter | device, port |
| `node_infiniband_legacy_unicast_packets_received_total` | Number of unicast packets received | counter | device, port |
| `node_infiniband_legacy_unicast_packets_transmitted_total` | Number of unicast packets transmitted | counter | device, port |
| `node_infiniband_link_downed_total` | Number of times the link failed to recover from an error state and went down | counter | device, port |
| `node_infiniband_link_error_recovery_total` | Number of times the link successfully recovered from an error state | counter | device, port |
| `node_infiniband_multicast_packets_received_total` | Number of multicast packets received (including errors) | counter | device, port |
| `node_infiniband_multicast_packets_transmitted_total` | Number of multicast packets transmitted (including errors) | counter | device, port |
| `node_infiniband_physical_state_id` | Physical state of the InfiniBand port (0: no change, 1: sleep, 2: polling, 3: disable, 4: shift, 5: link up, 6: link error recover, 7: phytest) | gauge | device, port |
| `node_infiniband_port_constraint_errors_received_total` | Number of packets received on the switch physical port that are discarded | counter | device, port |
| `node_infiniband_port_constraint_errors_transmitted_total` | Number of packets not transmitted from the switch physical port | counter | device, port |
| `node_infiniband_port_data_received_bytes_total` | Number of data octets received on all links | counter | device, port |
| `node_infiniband_port_data_transmitted_bytes_total` | Number of data octets transmitted on all links | counter | device, port |
| `node_infiniband_port_discards_received_total` | Number of inbound packets discarded by the port because the port is down or congested | counter | device, port |
| `node_infiniband_port_discards_transmitted_total` | Number of outbound packets discarded by the port because the port is down or congested | counter | device, port |
| `node_infiniband_port_errors_received_total` | Number of packets containing an error that were received on this port | counter | device, port |
| `node_infiniband_port_packets_received_total` | Number of packets received on all VLs by this port (including errors) | counter | device, port |
| `node_infiniband_port_packets_transmitted_total` | Number of packets transmitted on all VLs from this port (including errors) | counter | device, port |
| `node_infiniband_port_transmit_wait_total` | Number of ticks during which the port had data to transmit but no data was sent during the entire tick | counter | device, port |
| `node_infiniband_rate_bytes_per_second` | Maximum signal transfer rate | gauge | device, port |
| `node_infiniband_state_id` | State of the InfiniBand port (0: no change, 1: down, 2: init, 3: armed, 4: active, 5: act defer) | gauge | device, port |
| `node_infiniband_unicast_packets_received_total` | Number of unicast packets received (including errors) | counter | device, port |
| `node_infiniband_unicast_packets_transmitted_total` | Number of unicast packets transmitted (including errors) | counter | device, port |
| `node_ipvs_backend_connections_active` | The current active connections by local and remote address. | gauge | local_address, local_mark, local_port, proto, remote_address, remote_port |
| `node_ipvs_backend_connections_inactive` | The current inactive connections by local and remote address. | gauge | local_address, local_mark, local_port, proto, remote_address, remote_port |
| `node_ipvs_backend_weight` | The current backend weight by local and remote address. | gauge | local_address, local_mark, local_port, proto, remote_address, remote_port |
| `node_ipvs_connections_total` | The total number of connections made. | counter | — |
| `node_ipvs_incoming_bytes_total` | The total amount of incoming data. | counter | — |
| `node_ipvs_incoming_packets_total` | The total number of incoming packets. | counter | — |
| `node_ipvs_outgoing_bytes_total` | The total amount of outgoing data. | counter | — |
| `node_ipvs_outgoing_packets_total` | The total number of outgoing packets. | counter | — |
| `node_ksmd_full_scans_total` | ksmd 'full_scans' file. | counter | — |
| `node_ksmd_merge_across_nodes` | ksmd 'merge_across_nodes' file. | gauge | — |
| `node_ksmd_pages_shared` | ksmd 'pages_shared' file. | gauge | — |
| `node_ksmd_pages_sharing` | ksmd 'pages_sharing' file. | gauge | — |
| `node_ksmd_pages_to_scan` | ksmd 'pages_to_scan' file. | gauge | — |
| `node_ksmd_pages_unshared` | ksmd 'pages_unshared' file. | gauge | — |
| `node_ksmd_pages_volatile` | ksmd 'pages_volatile' file. | gauge | — |
| `node_ksmd_run` | ksmd 'run' file. | gauge | — |
| `node_ksmd_sleep_seconds` | ksmd 'sleep_millisecs' file. | gauge | — |
| `node_lnstat_allocs_total` | linux network cache stats | counter | cpu, subsystem |
| `node_lnstat_delete_list_total` | linux network cache stats | counter | cpu, subsystem |
| `node_lnstat_delete_total` | linux network cache stats | counter | cpu, subsystem |
| `node_lnstat_destroys_total` | linux network cache stats | counter | cpu, subsystem |
| `node_lnstat_drop_total` | linux network cache stats | counter | cpu, subsystem |
| `node_lnstat_early_drop_total` | linux network cache stats | counter | cpu, subsystem |
| `node_lnstat_entries_total` | linux network cache stats | counter | cpu, subsystem |
| `node_lnstat_expect_create_total` | linux network cache stats | counter | cpu, subsystem |
| `node_lnstat_expect_delete_total` | linux network cache stats | counter | cpu, subsystem |
| `node_lnstat_expect_new_total` | linux network cache stats | counter | cpu, subsystem |
| `node_lnstat_forced_gc_runs_total` | linux network cache stats | counter | cpu, subsystem |
| `node_lnstat_found_total` | linux network cache stats | counter | cpu, subsystem |
| `node_lnstat_hash_grows_total` | linux network cache stats | counter | cpu, subsystem |
| `node_lnstat_hits_total` | linux network cache stats | counter | cpu, subsystem |
| `node_lnstat_icmp_error_total` | linux network cache stats | counter | cpu, subsystem |
| `node_lnstat_ignore_total` | linux network cache stats | counter | cpu, subsystem |
| `node_lnstat_insert_failed_total` | linux network cache stats | counter | cpu, subsystem |
| `node_lnstat_insert_total` | linux network cache stats | counter | cpu, subsystem |
| `node_lnstat_invalid_total` | linux network cache stats | counter | cpu, subsystem |
| `node_lnstat_lookups_total` | linux network cache stats | counter | cpu, subsystem |
| `node_lnstat_new_total` | linux network cache stats | counter | cpu, subsystem |
| `node_lnstat_periodic_gc_runs_total` | linux network cache stats | counter | cpu, subsystem |
| `node_lnstat_rcv_probes_mcast_total` | linux network cache stats | counter | cpu, subsystem |
| `node_lnstat_rcv_probes_ucast_total` | linux network cache stats | counter | cpu, subsystem |
| `node_lnstat_res_failed_total` | linux network cache stats | counter | cpu, subsystem |
| `node_lnstat_search_restart_total` | linux network cache stats | counter | cpu, subsystem |
| `node_lnstat_searched_total` | linux network cache stats | counter | cpu, subsystem |
| `node_lnstat_table_fulls_total` | linux network cache stats | counter | cpu, subsystem |
| `node_lnstat_unresolved_discards_total` | linux network cache stats | counter | cpu, subsystem |
| `node_md_blocks` | Total number of blocks on device. | gauge | device |
| `node_md_blocks_synced` | Number of blocks synced on device. | gauge | device |
| `node_md_disks_required` | Total number of disks of device. | gauge | device |
| `node_md_state` | Indicates the state of md-device. | gauge | device, state |
| `node_memory_numa_Active` | Memory information field Active. | gauge | node |
| `node_memory_numa_Active_anon` | Memory information field Active_anon. | gauge | node |
| `node_memory_numa_Active_file` | Memory information field Active_file. | gauge | node |
| `node_memory_numa_AnonHugePages` | Memory information field AnonHugePages. | gauge | node |
| `node_memory_numa_AnonPages` | Memory information field AnonPages. | gauge | node |
| `node_memory_numa_Bounce` | Memory information field Bounce. | gauge | node |
| `node_memory_numa_Dirty` | Memory information field Dirty. | gauge | node |
| `node_memory_numa_FilePages` | Memory information field FilePages. | gauge | node |
| `node_memory_numa_HugePages_Free` | Memory information field HugePages_Free. | gauge | node |
| `node_memory_numa_HugePages_Surp` | Memory information field HugePages_Surp. | gauge | node |
| `node_memory_numa_HugePages_Total` | Memory information field HugePages_Total. | gauge | node |
| `node_memory_numa_Inactive` | Memory information field Inactive. | gauge | node |
| `node_memory_numa_Inactive_anon` | Memory information field Inactive_anon. | gauge | node |
| `node_memory_numa_Inactive_file` | Memory information field Inactive_file. | gauge | node |
| `node_memory_numa_KernelStack` | Memory information field KernelStack. | gauge | node |
| `node_memory_numa_Mapped` | Memory information field Mapped. | gauge | node |
| `node_memory_numa_MemFree` | Memory information field MemFree. | gauge | node |
| `node_memory_numa_MemTotal` | Memory information field MemTotal. | gauge | node |
| `node_memory_numa_MemUsed` | Memory information field MemUsed. | gauge | node |
| `node_memory_numa_Mlocked` | Memory information field Mlocked. | gauge | node |
| `node_memory_numa_NFS_Unstable` | Memory information field NFS_Unstable. | gauge | node |
| `node_memory_numa_PageTables` | Memory information field PageTables. | gauge | node |
| `node_memory_numa_SReclaimable` | Memory information field SReclaimable. | gauge | node |
| `node_memory_numa_SUnreclaim` | Memory information field SUnreclaim. | gauge | node |
| `node_memory_numa_Shmem` | Memory information field Shmem. | gauge | node |
| `node_memory_numa_Slab` | Memory information field Slab. | gauge | node |
| `node_memory_numa_Unevictable` | Memory information field Unevictable. | gauge | node |
| `node_memory_numa_Writeback` | Memory information field Writeback. | gauge | node |
| `node_memory_numa_WritebackTmp` | Memory information field WritebackTmp. | gauge | node |
| `node_memory_numa_interleave_hit_total` | Memory information field interleave_hit_total. | counter | node |
| `node_memory_numa_local_node_total` | Memory information field local_node_total. | counter | node |
| `node_memory_numa_numa_foreign_total` | Memory information field numa_foreign_total. | counter | node |
| `node_memory_numa_numa_hit_total` | Memory information field numa_hit_total. | counter | node |
| `node_memory_numa_numa_miss_total` | Memory information field numa_miss_total. | counter | node |
| `node_memory_numa_other_node_total` | Memory information field other_node_total. | counter | node |
| `node_mountstats_nfs_age_seconds_total` | The age of the NFS mount in seconds. | counter | export, mountaddr, protocol |
| `node_mountstats_nfs_direct_read_bytes_total` | Number of bytes read using the read() syscall in O_DIRECT mode. | counter | export, mountaddr, protocol |
| `node_mountstats_nfs_direct_write_bytes_total` | Number of bytes written using the write() syscall in O_DIRECT mode. | counter | export, mountaddr, protocol |
| `node_mountstats_nfs_event_attribute_invalidate_total` | Number of times cached inode attributes are invalidated. | counter | export, mountaddr, protocol |
| `node_mountstats_nfs_event_data_invalidate_total` | Number of times an inode cache is cleared. | counter | export, mountaddr, protocol |
| `node_mountstats_nfs_event_dnode_revalidate_total` | Number of times cached dentry nodes are re-validated from the server. | counter | export, mountaddr, protocol |
| `node_mountstats_nfs_event_inode_revalidate_total` | Number of times cached inode attributes are re-validated from the server. | counter | export, mountaddr, protocol |
| `node_mountstats_nfs_event_jukebox_delay_total` | Number of times the NFS server indicated EJUKEBOX; retrieving data from offline storage. | counter | export, mountaddr, protocol |
| `node_mountstats_nfs_event_pnfs_read_total` | Number of NFS v4.1+ pNFS reads. | counter | export, mountaddr, protocol |
| `node_mountstats_nfs_event_pnfs_write_total` | Number of NFS v4.1+ pNFS writes. | counter | export, mountaddr, protocol |
| `node_mountstats_nfs_event_short_read_total` | Number of times the NFS server gave less data than expected while reading. | counter | export, mountaddr, protocol |
| `node_mountstats_nfs_event_short_write_total` | Number of times the NFS server wrote less data than expected while writing. | counter | export, mountaddr, protocol |
| `node_mountstats_nfs_event_silly_rename_total` | Number of times a file was removed while still open by another process. | counter | export, mountaddr, protocol |
| `node_mountstats_nfs_event_truncation_total` | Number of times files have been truncated. | counter | export, mountaddr, protocol |
| `node_mountstats_nfs_event_vfs_access_total` | Number of times permissions have been checked. | counter | export, mountaddr, protocol |
| `node_mountstats_nfs_event_vfs_file_release_total` | Number of times files have been closed and released. | counter | export, mountaddr, protocol |
| `node_mountstats_nfs_event_vfs_flush_total` | Number of pending writes that have been forcefully flushed to the server. | counter | export, mountaddr, protocol |
| `node_mountstats_nfs_event_vfs_fsync_total` | Number of times fsync() has been called on directories and files. | counter | export, mountaddr, protocol |
| `node_mountstats_nfs_event_vfs_getdents_total` | Number of times directory entries have been read with getdents(). | counter | export, mountaddr, protocol |
| `node_mountstats_nfs_event_vfs_lock_total` | Number of times locking has been attempted on a file. | counter | export, mountaddr, protocol |
| `node_mountstats_nfs_event_vfs_lookup_total` | Number of times a directory lookup has occurred. | counter | export, mountaddr, protocol |
| `node_mountstats_nfs_event_vfs_open_total` | Number of times cached inode attributes are invalidated. | counter | export, mountaddr, protocol |
| `node_mountstats_nfs_event_vfs_read_page_total` | Number of pages read directly via mmap()'d files. | counter | export, mountaddr, protocol |
| `node_mountstats_nfs_event_vfs_read_pages_total` | Number of times a group of pages have been read. | counter | export, mountaddr, protocol |
| `node_mountstats_nfs_event_vfs_setattr_total` | Number of times directory entries have been read with getdents(). | counter | export, mountaddr, protocol |
| `node_mountstats_nfs_event_vfs_update_page_total` | Number of updates (and potential writes) to pages. | counter | export, mountaddr, protocol |
| `node_mountstats_nfs_event_vfs_write_page_total` | Number of pages written directly via mmap()'d files. | counter | export, mountaddr, protocol |
| `node_mountstats_nfs_event_vfs_write_pages_total` | Number of times a group of pages have been written. | counter | export, mountaddr, protocol |
| `node_mountstats_nfs_event_write_extension_total` | Number of times a file has been grown due to writes beyond its existing end. | counter | export, mountaddr, protocol |
| `node_mountstats_nfs_operations_major_timeouts_total` | Number of times a request has had a major timeout for a given operation. | counter | export, mountaddr, operation, protocol |
| `node_mountstats_nfs_operations_queue_time_seconds_total` | Duration all requests spent queued for transmission for a given operation before they were sent, in seconds. | counter | export, mountaddr, operation, protocol |
| `node_mountstats_nfs_operations_received_bytes_total` | Number of bytes received for a given operation, including RPC headers and payload. | counter | export, mountaddr, operation, protocol |
| `node_mountstats_nfs_operations_request_time_seconds_total` | Duration all requests took from when a request was enqueued to when it was completely handled for a given operation, in seconds. | counter | export, mountaddr, operation, protocol |
| `node_mountstats_nfs_operations_requests_total` | Number of requests performed for a given operation. | counter | export, mountaddr, operation, protocol |
| `node_mountstats_nfs_operations_response_time_seconds_total` | Duration all requests took to get a reply back after a request for a given operation was transmitted, in seconds. | counter | export, mountaddr, operation, protocol |
| `node_mountstats_nfs_operations_sent_bytes_total` | Number of bytes sent for a given operation, including RPC headers and payload. | counter | export, mountaddr, operation, protocol |
| `node_mountstats_nfs_operations_transmissions_total` | Number of times an actual RPC request has been transmitted for a given operation. | counter | export, mountaddr, operation, protocol |
| `node_mountstats_nfs_read_bytes_total` | Number of bytes read using the read() syscall. | counter | export, mountaddr, protocol |
| `node_mountstats_nfs_read_pages_total` | Number of pages read directly via mmap()'d files. | counter | export, mountaddr, protocol |
| `node_mountstats_nfs_total_read_bytes_total` | Number of bytes read from the NFS server, in total. | counter | export, mountaddr, protocol |
| `node_mountstats_nfs_total_write_bytes_total` | Number of bytes written to the NFS server, in total. | counter | export, mountaddr, protocol |
| `node_mountstats_nfs_transport_backlog_queue_total` | Total number of items added to the RPC backlog queue. | counter | export, mountaddr, protocol |
| `node_mountstats_nfs_transport_bad_transaction_ids_total` | Number of times the NFS server sent a response with a transaction ID unknown to this client. | counter | export, mountaddr, protocol |
| `node_mountstats_nfs_transport_bind_total` | Number of times the client has had to establish a connection from scratch to the NFS server. | counter | export, mountaddr, protocol |
| `node_mountstats_nfs_transport_connect_total` | Number of times the client has made a TCP connection to the NFS server. | counter | export, mountaddr, protocol |
| `node_mountstats_nfs_transport_idle_time_seconds` | Duration since the NFS mount last saw any RPC traffic, in seconds. | gauge | export, mountaddr, protocol |
| `node_mountstats_nfs_transport_maximum_rpc_slots` | Maximum number of simultaneously active RPC requests ever used. | gauge | export, mountaddr, protocol |
| `node_mountstats_nfs_transport_pending_queue_total` | Total number of items added to the RPC transmission pending queue. | counter | export, mountaddr, protocol |
| `node_mountstats_nfs_transport_receives_total` | Number of RPC responses for this mount received from the NFS server. | counter | export, mountaddr, protocol |
| `node_mountstats_nfs_transport_sending_queue_total` | Total number of items added to the RPC transmission sending queue. | counter | export, mountaddr, protocol |
| `node_mountstats_nfs_transport_sends_total` | Number of RPC requests for this mount sent to the NFS server. | counter | export, mountaddr, protocol |
| `node_mountstats_nfs_write_bytes_total` | Number of bytes written using the write() syscall. | counter | export, mountaddr, protocol |
| `node_mountstats_nfs_write_pages_total` | Number of pages written directly via mmap()'d files. | counter | export, mountaddr, protocol |
| `node_netstat_Icmp6_InErrors` | Statistic Icmp6InErrors. | untyped | — |
| `node_netstat_Icmp6_InMsgs` | Statistic Icmp6InMsgs. | untyped | — |
| `node_netstat_Icmp6_OutMsgs` | Statistic Icmp6OutMsgs. | untyped | — |
| `node_netstat_Ip6_InOctets` | Statistic Ip6InOctets. | untyped | — |
| `node_netstat_Ip6_OutOctets` | Statistic Ip6OutOctets. | untyped | — |
| `node_netstat_Ip_Forwarding` | Statistic IpForwarding. | untyped | — |
| `node_netstat_Udp6_InDatagrams` | Statistic Udp6InDatagrams. | untyped | — |
| `node_netstat_Udp6_InErrors` | Statistic Udp6InErrors. | untyped | — |
| `node_netstat_Udp6_NoPorts` | Statistic Udp6NoPorts. | untyped | — |
| `node_netstat_Udp6_OutDatagrams` | Statistic Udp6OutDatagrams. | untyped | — |
| `node_netstat_Udp6_RcvbufErrors` | Statistic Udp6RcvbufErrors. | untyped | — |
| `node_netstat_Udp6_SndbufErrors` | Statistic Udp6SndbufErrors. | untyped | — |
| `node_netstat_UdpLite6_InErrors` | Statistic UdpLite6InErrors. | untyped | — |
| `node_network_address_assign_type` | Network device property: address_assign_type | gauge | device |
| `node_network_carrier_down_changes_total` | Network device property: carrier_down_changes_total | counter | device |
| `node_network_carrier_up_changes_total` | Network device property: carrier_up_changes_total | counter | device |
| `node_network_device_id` | Network device property: device_id | gauge | device |
| `node_network_dormant` | Network device property: dormant | gauge | device |
| `node_network_flags` | Network device property: flags | gauge | device |
| `node_network_iface_id` | Network device property: iface_id | gauge | device |
| `node_network_iface_link` | Network device property: iface_link | gauge | device |
| `node_network_iface_link_mode` | Network device property: iface_link_mode | gauge | device |
| `node_network_name_assign_type` | Network device property: name_assign_type | gauge | device |
| `node_network_net_dev_group` | Network device property: net_dev_group | gauge | device |
| `node_network_protocol_type` | Network device property: protocol_type | gauge | device |
| `node_network_transmit_queue_length` | Network device property: transmit_queue_length | gauge | device |
| `node_nf_conntrack_stat_drop` | Number of packets dropped due to conntrack failure. | gauge | — |
| `node_nf_conntrack_stat_early_drop` | Number of dropped conntrack entries to make room for new ones, if maximum table size was reached. | gauge | — |
| `node_nf_conntrack_stat_found` | Number of searched entries which were successful. | gauge | — |
| `node_nf_conntrack_stat_ignore` | Number of packets seen which are already connected to a conntrack entry. | gauge | — |
| `node_nf_conntrack_stat_insert` | Number of entries inserted into the list. | gauge | — |
| `node_nf_conntrack_stat_insert_failed` | Number of entries for which list insertion was attempted but failed. | gauge | — |
| `node_nf_conntrack_stat_invalid` | Number of packets seen which can not be tracked. | gauge | — |
| `node_nf_conntrack_stat_search_restart` | Number of conntrack table lookups which had to be restarted due to hashtable resizes. | gauge | — |
| `node_nfs_connections_total` | Total number of NFSd TCP connections. | counter | — |
| `node_nfs_packets_total` | Total NFSd network packets (sent+received) by protocol type. | counter | protocol |
| `node_nfs_requests_total` | Number of NFS procedures invoked. | counter | method, proto |
| `node_nfs_rpc_authentication_refreshes_total` | Number of RPC authentication refreshes performed. | counter | — |
| `node_nfs_rpc_retransmissions_total` | Number of RPC transmissions performed. | counter | — |
| `node_nfs_rpcs_total` | Total number of RPCs performed. | counter | — |
| `node_nfsd_connections_total` | Total number of NFSd TCP connections. | counter | — |
| `node_nfsd_disk_bytes_read_total` | Total NFSd bytes read. | counter | — |
| `node_nfsd_disk_bytes_written_total` | Total NFSd bytes written. | counter | — |
| `node_nfsd_file_handles_stale_total` | Total number of NFSd stale file handles | counter | — |
| `node_nfsd_packets_total` | Total NFSd network packets (sent+received) by protocol type. | counter | proto |
| `node_nfsd_read_ahead_cache_not_found_total` | Total number of NFSd read ahead cache not found. | counter | — |
| `node_nfsd_read_ahead_cache_size_blocks` | How large the read ahead cache is in blocks. | gauge | — |
| `node_nfsd_reply_cache_hits_total` | Total number of NFSd Reply Cache hits (client lost server response). | counter | — |
| `node_nfsd_reply_cache_misses_total` | Total number of NFSd Reply Cache an operation that requires caching (idempotent). | counter | — |
| `node_nfsd_reply_cache_nocache_total` | Total number of NFSd Reply Cache non-idempotent operations (rename/delete/…). | counter | — |
| `node_nfsd_requests_total` | Total number NFSd Requests by method and protocol. | counter | method, proto |
| `node_nfsd_rpc_errors_total` | Total number of NFSd RPC errors by error type. | counter | error |
| `node_nfsd_server_rpcs_total` | Total number of NFSd RPCs. | counter | — |
| `node_nfsd_server_threads` | Total number of NFSd kernel threads that are running. | gauge | — |
| `node_nvme_info` | Non-numeric data from /sys/class/nvme/<device>, value is always 1. | gauge | device, firmware_revision, model, serial, state |
| `node_os_info` | A metric with a constant '1' value labeled by build_id, id, id_like, image_id, image_version, name, pretty_name, variant, variant_id, version, version_codename, version_id. | gauge | build_id, id, id_like, image_id, image_version, name, pretty_name, variant, variant_id, version, version_codename, version_id |
| `node_os_version` | Metric containing the major.minor part of the OS version. | gauge | id, id_like, name |
| `node_power_supply_capacity` | capacity value of /sys/class/power_supply/<power_supply>. | gauge | power_supply |
| `node_power_supply_cyclecount` | cyclecount value of /sys/class/power_supply/<power_supply>. | gauge | power_supply |
| `node_power_supply_energy_full` | energy_full value of /sys/class/power_supply/<power_supply>. | gauge | power_supply |
| `node_power_supply_energy_full_design` | energy_full_design value of /sys/class/power_supply/<power_supply>. | gauge | power_supply |
| `node_power_supply_energy_watthour` | energy_watthour value of /sys/class/power_supply/<power_supply>. | gauge | power_supply |
| `node_power_supply_info` | info of /sys/class/power_supply/<power_supply>. | gauge | capacity_level, manufacturer, model_name, power_supply, serial_number, status, technology, type |
| `node_power_supply_power_watt` | power_watt value of /sys/class/power_supply/<power_supply>. | gauge | power_supply |
| `node_power_supply_present` | present value of /sys/class/power_supply/<power_supply>. | gauge | power_supply |
| `node_power_supply_voltage_min_design` | voltage_min_design value of /sys/class/power_supply/<power_supply>. | gauge | power_supply |
| `node_power_supply_voltage_volt` | voltage_volt value of /sys/class/power_supply/<power_supply>. | gauge | power_supply |
| `node_qdisc_backlog` | Number of bytes currently in queue to be sent. | gauge | device, kind |
| `node_qdisc_bytes_total` | Number of bytes sent. | counter | device, kind |
| `node_qdisc_current_queue_length` | Number of packets currently in queue to be sent. | gauge | device, kind |
| `node_qdisc_drops_total` | Number of packets dropped. | counter | device, kind |
| `node_qdisc_overlimits_total` | Number of overlimit packets. | counter | device, kind |
| `node_qdisc_packets_total` | Number of packets sent. | counter | device, kind |
| `node_qdisc_requeues_total` | Number of packets dequeued, not transmitted, and requeued. | counter | device, kind |
| `node_rapl_core_joules_total` | Current RAPL core value in joules | counter | index, path |
| `node_rapl_package_joules_total` | Current RAPL package value in joules | counter | index, path |
| `node_slabinfo_active_objects` | The number of objects that are currently active (i.e., in use). | gauge | slab |
| `node_slabinfo_object_size_bytes` | The size of objects in this slab, in bytes. | gauge | slab |
| `node_slabinfo_objects` | The total number of allocated objects (i.e., objects that are both in use and not in use). | gauge | slab |
| `node_slabinfo_objects_per_slab` | The number of objects stored in each slab. | gauge | slab |
| `node_slabinfo_pages_per_slab` | The number of pages allocated for each slab. | gauge | slab |
| `node_sockstat_FRAG6_inuse` | Number of FRAG6 sockets in state inuse. | gauge | — |
| `node_sockstat_FRAG6_memory` | Number of FRAG6 sockets in state memory. | gauge | — |
| `node_sockstat_RAW6_inuse` | Number of RAW6 sockets in state inuse. | gauge | — |
| `node_sockstat_TCP6_inuse` | Number of TCP6 sockets in state inuse. | gauge | — |
| `node_sockstat_UDP6_inuse` | Number of UDP6 sockets in state inuse. | gauge | — |
| `node_sockstat_UDPLITE6_inuse` | Number of UDPLITE6 sockets in state inuse. | gauge | — |
| `node_softirqs_functions_total` | Softirq counts per CPU. | counter | cpu, type |
| `node_softirqs_total` | Number of softirq calls. | counter | vector |
| `node_softnet_backlog_len` | Softnet backlog status | gauge | cpu |
| `node_softnet_cpu_collision_total` | Number of collision occur while obtaining device lock while transmitting | counter | cpu |
| `node_sysctl_fs_file_nr` | sysctl fs.file-nr | untyped | index |
| `node_sysctl_fs_file_nr_current` | sysctl fs.file-nr, field 1 | untyped | — |
| `node_sysctl_fs_file_nr_max` | sysctl fs.file-nr, field 2 | untyped | — |
| `node_sysctl_fs_file_nr_total` | sysctl fs.file-nr, field 0 | untyped | — |
| `node_sysctl_info` | sysctl info | gauge | index, name, value |
| `node_sysctl_kernel_threads_max` | sysctl kernel.threads-max | untyped | — |
| `node_tape_io_now` | The number of I/Os currently outstanding to this device. | gauge | device |
| `node_tape_io_others_total` | The number of I/Os issued to the tape drive other than read or write commands. The time taken to complete these commands uses the following calculation io_time_seconds_total-read_time_seconds_total-write_time_seconds_total | counter | device |
| `node_tape_io_time_seconds_total` | The amount of time spent waiting for all I/O to complete (including read and write). This includes tape movement commands such as seeking between file or set marks and implicit tape movement such as when rewind on close tape devices are used. | counter | device |
| `node_tape_read_bytes_total` | The number of bytes read from the tape drive. | counter | device |
| `node_tape_read_time_seconds_total` | The amount of time spent waiting for read requests to complete. | counter | device |
| `node_tape_reads_completed_total` | The number of read requests issued to the tape drive. | counter | device |
| `node_tape_residual_total` | The number of times during a read or write we found the residual amount to be non-zero. This should mean that a program is issuing a read larger thean the block size on tape. For write not all data made it to tape. | counter | device |
| `node_tape_write_time_seconds_total` | The amount of time spent waiting for write requests to complete. | counter | device |
| `node_tape_writes_completed_total` | The number of write requests issued to the tape drive. | counter | device |
| `node_tape_written_bytes_total` | The number of bytes written to the tape drive. | counter | device |
| `node_textfile_mtime_seconds` | Unixtime mtime of textfiles successfully read. | gauge | — |
| `node_thermal_zone_temp` | Zone temperature in Celsius | gauge | type, zone |
| `node_time_clocksource_available_info` | Available clocksources read from '/sys/devices/system/clocksource'. | gauge | clocksource, device |
| `node_time_clocksource_current_info` | Current clocksource read from '/sys/devices/system/clocksource'. | gauge | clocksource, device |
| `node_time_zone_offset_seconds` | System time zone offset in seconds. | gauge | — |
| `node_watchdog_access_cs0` | Value of /sys/class/watchdog/<watchdog>/access_cs0 | gauge | name |
| `node_watchdog_bootstatus` | Value of /sys/class/watchdog/<watchdog>/bootstatus | gauge | name |
| `node_watchdog_fw_version` | Value of /sys/class/watchdog/<watchdog>/fw_version | gauge | name |
| `node_watchdog_info` | Info of /sys/class/watchdog/<watchdog> | gauge | identity, name, options, pretimeout_governor, state, status |
| `node_watchdog_nowayout` | Value of /sys/class/watchdog/<watchdog>/nowayout | gauge | name |
| `node_watchdog_pretimeout_seconds` | Value of /sys/class/watchdog/<watchdog>/pretimeout | gauge | name |
| `node_watchdog_timeleft_seconds` | Value of /sys/class/watchdog/<watchdog>/timeleft | gauge | name |
| `node_watchdog_timeout_seconds` | Value of /sys/class/watchdog/<watchdog>/timeout | gauge | name |
| `node_wifi_interface_frequency_hertz` | The current frequency a WiFi interface is operating at, in hertz. | gauge | device |
| `node_wifi_station_beacon_loss_total` | The total number of times a station has detected a beacon loss. | counter | device, mac_address |
| `node_wifi_station_connected_seconds_total` | The total number of seconds a station has been connected to an access point. | counter | device, mac_address |
| `node_wifi_station_inactive_seconds` | The number of seconds since any wireless activity has occurred on a station. | gauge | device, mac_address |
| `node_wifi_station_info` | Labeled WiFi interface station information as provided by the operating system. | gauge | bssid, device, mode, ssid |
| `node_wifi_station_receive_bits_per_second` | The current WiFi receive bitrate of a station, in bits per second. | gauge | device, mac_address |
| `node_wifi_station_receive_bytes_total` | The total number of bytes received by a WiFi station. | counter | device, mac_address |
| `node_wifi_station_signal_dbm` | The current WiFi signal strength, in decibel-milliwatts (dBm). | gauge | device, mac_address |
| `node_wifi_station_transmit_bits_per_second` | The current WiFi transmit bitrate of a station, in bits per second. | gauge | device, mac_address |
| `node_wifi_station_transmit_bytes_total` | The total number of bytes transmitted by a WiFi station. | counter | device, mac_address |
| `node_wifi_station_transmit_failed_total` | The total number of times a station has failed to send a packet. | counter | device, mac_address |
| `node_wifi_station_transmit_retries_total` | The total number of times a station has had to retry while sending a packet. | counter | device, mac_address |
| `node_xfrm_acquire_error_packets_total` | State hasn’t been fully acquired before use | counter | — |
| `node_xfrm_fwd_hdr_error_packets_total` | Forward routing of a packet is not allowed | counter | — |
| `node_xfrm_in_buffer_error_packets_total` | No buffer is left | counter | — |
| `node_xfrm_in_error_packets_total` | All errors not matched by other | counter | — |
| `node_xfrm_in_hdr_error_packets_total` | Header error | counter | — |
| `node_xfrm_in_no_pols_packets_total` | No policy is found for states e.g. Inbound SAs are correct but no SP is found | counter | — |
| `node_xfrm_in_no_states_packets_total` | No state is found i.e. Either inbound SPI, address, or IPsec protocol at SA is wrong | counter | — |
| `node_xfrm_in_pol_block_packets_total` | Policy discards | counter | — |
| `node_xfrm_in_pol_error_packets_total` | Policy error | counter | — |
| `node_xfrm_in_state_expired_packets_total` | State is expired | counter | — |
| `node_xfrm_in_state_invalid_packets_total` | State is invalid | counter | — |
| `node_xfrm_in_state_mismatch_packets_total` | State has mismatch option e.g. UDP encapsulation type is mismatch | counter | — |
| `node_xfrm_in_state_mode_error_packets_total` | Transformation mode specific error | counter | — |
| `node_xfrm_in_state_proto_error_packets_total` | Transformation protocol specific error e.g. SA key is wrong | counter | — |
| `node_xfrm_in_state_seq_error_packets_total` | Sequence error i.e. Sequence number is out of window | counter | — |
| `node_xfrm_in_tmpl_mismatch_packets_total` | No matching template for states e.g. Inbound SAs are correct but SP rule is wrong | counter | — |
| `node_xfrm_out_bundle_check_error_packets_total` | Bundle check error | counter | — |
| `node_xfrm_out_bundle_gen_error_packets_total` | Bundle generation error | counter | — |
| `node_xfrm_out_error_packets_total` | All errors which is not matched others | counter | — |
| `node_xfrm_out_no_states_packets_total` | No state is found | counter | — |
| `node_xfrm_out_pol_block_packets_total` | Policy discards | counter | — |
| `node_xfrm_out_pol_dead_packets_total` | Policy is dead | counter | — |
| `node_xfrm_out_pol_error_packets_total` | Policy error | counter | — |
| `node_xfrm_out_state_expired_packets_total` | State is expired | counter | — |
| `node_xfrm_out_state_invalid_packets_total` | State is invalid, perhaps expired | counter | — |
| `node_xfrm_out_state_mode_error_packets_total` | Transformation mode specific error | counter | — |
| `node_xfrm_out_state_proto_error_packets_total` | Transformation protocol specific error | counter | — |
| `node_xfrm_out_state_seq_error_packets_total` | Sequence error i.e. Sequence number overflow | counter | — |
| `node_xfs_allocation_btree_compares_total` | Number of allocation B-tree compares for a filesystem. | counter | device |
| `node_xfs_allocation_btree_lookups_total` | Number of allocation B-tree lookups for a filesystem. | counter | device |
| `node_xfs_allocation_btree_records_deleted_total` | Number of allocation B-tree records deleted for a filesystem. | counter | device |
| `node_xfs_allocation_btree_records_inserted_total` | Number of allocation B-tree records inserted for a filesystem. | counter | device |
| `node_xfs_block_map_btree_compares_total` | Number of block map B-tree compares for a filesystem. | counter | device |
| `node_xfs_block_map_btree_lookups_total` | Number of block map B-tree lookups for a filesystem. | counter | device |
| `node_xfs_block_map_btree_records_deleted_total` | Number of block map B-tree records deleted for a filesystem. | counter | device |
| `node_xfs_block_map_btree_records_inserted_total` | Number of block map B-tree records inserted for a filesystem. | counter | device |
| `node_xfs_block_mapping_extent_list_compares_total` | Number of extent list compares for a filesystem. | counter | device |
| `node_xfs_block_mapping_extent_list_deletions_total` | Number of extent list deletions for a filesystem. | counter | device |
| `node_xfs_block_mapping_extent_list_insertions_total` | Number of extent list insertions for a filesystem. | counter | device |
| `node_xfs_block_mapping_extent_list_lookups_total` | Number of extent list lookups for a filesystem. | counter | device |
| `node_xfs_block_mapping_reads_total` | Number of block map for read operations for a filesystem. | counter | device |
| `node_xfs_block_mapping_unmaps_total` | Number of block unmaps (deletes) for a filesystem. | counter | device |
| `node_xfs_block_mapping_writes_total` | Number of block map for write operations for a filesystem. | counter | device |
| `node_xfs_directory_operation_create_total` | Number of times a new directory entry was created for a filesystem. | counter | device |
| `node_xfs_directory_operation_getdents_total` | Number of times the directory getdents operation was performed for a filesystem. | counter | device |
| `node_xfs_directory_operation_lookup_total` | Number of file name directory lookups which miss the operating systems directory name lookup cache. | counter | device |
| `node_xfs_directory_operation_remove_total` | Number of times an existing directory entry was created for a filesystem. | counter | device |
| `node_xfs_extent_allocation_blocks_allocated_total` | Number of blocks allocated for a filesystem. | counter | device |
| `node_xfs_extent_allocation_blocks_freed_total` | Number of blocks freed for a filesystem. | counter | device |
| `node_xfs_extent_allocation_extents_allocated_total` | Number of extents allocated for a filesystem. | counter | device |
| `node_xfs_extent_allocation_extents_freed_total` | Number of extents freed for a filesystem. | counter | device |
| `node_xfs_inode_operation_attempts_total` | Number of times the OS looked for an XFS inode in the inode cache. | counter | device |
| `node_xfs_inode_operation_attribute_changes_total` | Number of times the OS explicitly changed the attributes of an XFS inode. | counter | device |
| `node_xfs_inode_operation_duplicates_total` | Number of times the OS tried to add a missing XFS inode to the inode cache, but found it had already been added by another process. | counter | device |
| `node_xfs_inode_operation_found_total` | Number of times the OS looked for and found an XFS inode in the inode cache. | counter | device |
| `node_xfs_inode_operation_missed_total` | Number of times the OS looked for an XFS inode in the cache, but did not find it. | counter | device |
| `node_xfs_inode_operation_reclaims_total` | Number of times the OS reclaimed an XFS inode from the inode cache to free memory for another purpose. | counter | device |
| `node_xfs_inode_operation_recycled_total` | Number of times the OS found an XFS inode in the cache, but could not use it as it was being recycled. | counter | device |
| `node_xfs_read_calls_total` | Number of read(2) system calls made to files in a filesystem. | counter | device |
| `node_xfs_vnode_active_total` | Number of vnodes not on free lists for a filesystem. | counter | device |
| `node_xfs_vnode_allocate_total` | Number of times vn_alloc called for a filesystem. | counter | device |
| `node_xfs_vnode_get_total` | Number of times vn_get called for a filesystem. | counter | device |
| `node_xfs_vnode_hold_total` | Number of times vn_hold called for a filesystem. | counter | device |
| `node_xfs_vnode_reclaim_total` | Number of times vn_reclaim called for a filesystem. | counter | device |
| `node_xfs_vnode_release_total` | Number of times vn_rele called for a filesystem. | counter | device |
| `node_xfs_vnode_remove_total` | Number of times vn_remove called for a filesystem. | counter | device |
| `node_xfs_write_calls_total` | Number of write(2) system calls made to files in a filesystem. | counter | device |
| `node_zfs_abd_linear_cnt` | kstat.zfs.misc.abdstats.linear_cnt | untyped | — |
| `node_zfs_abd_linear_data_size` | kstat.zfs.misc.abdstats.linear_data_size | untyped | — |
| `node_zfs_abd_scatter_chunk_waste` | kstat.zfs.misc.abdstats.scatter_chunk_waste | untyped | — |
| `node_zfs_abd_scatter_cnt` | kstat.zfs.misc.abdstats.scatter_cnt | untyped | — |
| `node_zfs_abd_scatter_data_size` | kstat.zfs.misc.abdstats.scatter_data_size | untyped | — |
| `node_zfs_abd_scatter_order_0` | kstat.zfs.misc.abdstats.scatter_order_0 | untyped | — |
| `node_zfs_abd_scatter_order_1` | kstat.zfs.misc.abdstats.scatter_order_1 | untyped | — |
| `node_zfs_abd_scatter_order_10` | kstat.zfs.misc.abdstats.scatter_order_10 | untyped | — |
| `node_zfs_abd_scatter_order_2` | kstat.zfs.misc.abdstats.scatter_order_2 | untyped | — |
| `node_zfs_abd_scatter_order_3` | kstat.zfs.misc.abdstats.scatter_order_3 | untyped | — |
| `node_zfs_abd_scatter_order_4` | kstat.zfs.misc.abdstats.scatter_order_4 | untyped | — |
| `node_zfs_abd_scatter_order_5` | kstat.zfs.misc.abdstats.scatter_order_5 | untyped | — |
| `node_zfs_abd_scatter_order_6` | kstat.zfs.misc.abdstats.scatter_order_6 | untyped | — |
| `node_zfs_abd_scatter_order_7` | kstat.zfs.misc.abdstats.scatter_order_7 | untyped | — |
| `node_zfs_abd_scatter_order_8` | kstat.zfs.misc.abdstats.scatter_order_8 | untyped | — |
| `node_zfs_abd_scatter_order_9` | kstat.zfs.misc.abdstats.scatter_order_9 | untyped | — |
| `node_zfs_abd_scatter_page_alloc_retry` | kstat.zfs.misc.abdstats.scatter_page_alloc_retry | untyped | — |
| `node_zfs_abd_scatter_page_multi_chunk` | kstat.zfs.misc.abdstats.scatter_page_multi_chunk | untyped | — |
| `node_zfs_abd_scatter_page_multi_zone` | kstat.zfs.misc.abdstats.scatter_page_multi_zone | untyped | — |
| `node_zfs_abd_scatter_sg_table_retry` | kstat.zfs.misc.abdstats.scatter_sg_table_retry | untyped | — |
| `node_zfs_abd_struct_size` | kstat.zfs.misc.abdstats.struct_size | untyped | — |
| `node_zfs_arc_anon_evictable_data` | kstat.zfs.misc.arcstats.anon_evictable_data | untyped | — |
| `node_zfs_arc_anon_evictable_metadata` | kstat.zfs.misc.arcstats.anon_evictable_metadata | untyped | — |
| `node_zfs_arc_anon_size` | kstat.zfs.misc.arcstats.anon_size | untyped | — |
| `node_zfs_arc_arc_loaned_bytes` | kstat.zfs.misc.arcstats.arc_loaned_bytes | untyped | — |
| `node_zfs_arc_arc_meta_limit` | kstat.zfs.misc.arcstats.arc_meta_limit | untyped | — |
| `node_zfs_arc_arc_meta_max` | kstat.zfs.misc.arcstats.arc_meta_max | untyped | — |
| `node_zfs_arc_arc_meta_min` | kstat.zfs.misc.arcstats.arc_meta_min | untyped | — |
| `node_zfs_arc_arc_meta_used` | kstat.zfs.misc.arcstats.arc_meta_used | untyped | — |
| `node_zfs_arc_arc_need_free` | kstat.zfs.misc.arcstats.arc_need_free | untyped | — |
| `node_zfs_arc_arc_no_grow` | kstat.zfs.misc.arcstats.arc_no_grow | untyped | — |
| `node_zfs_arc_arc_prune` | kstat.zfs.misc.arcstats.arc_prune | untyped | — |
| `node_zfs_arc_arc_sys_free` | kstat.zfs.misc.arcstats.arc_sys_free | untyped | — |
| `node_zfs_arc_arc_tempreserve` | kstat.zfs.misc.arcstats.arc_tempreserve | untyped | — |
| `node_zfs_arc_c` | kstat.zfs.misc.arcstats.c | untyped | — |
| `node_zfs_arc_c_max` | kstat.zfs.misc.arcstats.c_max | untyped | — |
| `node_zfs_arc_c_min` | kstat.zfs.misc.arcstats.c_min | untyped | — |
| `node_zfs_arc_data_size` | kstat.zfs.misc.arcstats.data_size | untyped | — |
| `node_zfs_arc_deleted` | kstat.zfs.misc.arcstats.deleted | untyped | — |
| `node_zfs_arc_demand_data_hits` | kstat.zfs.misc.arcstats.demand_data_hits | untyped | — |
| `node_zfs_arc_demand_data_misses` | kstat.zfs.misc.arcstats.demand_data_misses | untyped | — |
| `node_zfs_arc_demand_metadata_hits` | kstat.zfs.misc.arcstats.demand_metadata_hits | untyped | — |
| `node_zfs_arc_demand_metadata_misses` | kstat.zfs.misc.arcstats.demand_metadata_misses | untyped | — |
| `node_zfs_arc_duplicate_buffers` | kstat.zfs.misc.arcstats.duplicate_buffers | untyped | — |
| `node_zfs_arc_duplicate_buffers_size` | kstat.zfs.misc.arcstats.duplicate_buffers_size | untyped | — |
| `node_zfs_arc_duplicate_reads` | kstat.zfs.misc.arcstats.duplicate_reads | untyped | — |
| `node_zfs_arc_evict_l2_cached` | kstat.zfs.misc.arcstats.evict_l2_cached | untyped | — |
| `node_zfs_arc_evict_l2_eligible` | kstat.zfs.misc.arcstats.evict_l2_eligible | untyped | — |
| `node_zfs_arc_evict_l2_ineligible` | kstat.zfs.misc.arcstats.evict_l2_ineligible | untyped | — |
| `node_zfs_arc_evict_l2_skip` | kstat.zfs.misc.arcstats.evict_l2_skip | untyped | — |
| `node_zfs_arc_evict_not_enough` | kstat.zfs.misc.arcstats.evict_not_enough | untyped | — |
| `node_zfs_arc_evict_skip` | kstat.zfs.misc.arcstats.evict_skip | untyped | — |
| `node_zfs_arc_hash_chain_max` | kstat.zfs.misc.arcstats.hash_chain_max | untyped | — |
| `node_zfs_arc_hash_chains` | kstat.zfs.misc.arcstats.hash_chains | untyped | — |
| `node_zfs_arc_hash_collisions` | kstat.zfs.misc.arcstats.hash_collisions | untyped | — |
| `node_zfs_arc_hash_elements` | kstat.zfs.misc.arcstats.hash_elements | untyped | — |
| `node_zfs_arc_hash_elements_max` | kstat.zfs.misc.arcstats.hash_elements_max | untyped | — |
| `node_zfs_arc_hdr_size` | kstat.zfs.misc.arcstats.hdr_size | untyped | — |
| `node_zfs_arc_hits` | kstat.zfs.misc.arcstats.hits | untyped | — |
| `node_zfs_arc_l2_abort_lowmem` | kstat.zfs.misc.arcstats.l2_abort_lowmem | untyped | — |
| `node_zfs_arc_l2_asize` | kstat.zfs.misc.arcstats.l2_asize | untyped | — |
| `node_zfs_arc_l2_cdata_free_on_write` | kstat.zfs.misc.arcstats.l2_cdata_free_on_write | untyped | — |
| `node_zfs_arc_l2_cksum_bad` | kstat.zfs.misc.arcstats.l2_cksum_bad | untyped | — |
| `node_zfs_arc_l2_compress_failures` | kstat.zfs.misc.arcstats.l2_compress_failures | untyped | — |
| `node_zfs_arc_l2_compress_successes` | kstat.zfs.misc.arcstats.l2_compress_successes | untyped | — |
| `node_zfs_arc_l2_compress_zeros` | kstat.zfs.misc.arcstats.l2_compress_zeros | untyped | — |
| `node_zfs_arc_l2_evict_l1cached` | kstat.zfs.misc.arcstats.l2_evict_l1cached | untyped | — |
| `node_zfs_arc_l2_evict_lock_retry` | kstat.zfs.misc.arcstats.l2_evict_lock_retry | untyped | — |
| `node_zfs_arc_l2_evict_reading` | kstat.zfs.misc.arcstats.l2_evict_reading | untyped | — |
| `node_zfs_arc_l2_feeds` | kstat.zfs.misc.arcstats.l2_feeds | untyped | — |
| `node_zfs_arc_l2_free_on_write` | kstat.zfs.misc.arcstats.l2_free_on_write | untyped | — |
| `node_zfs_arc_l2_hdr_size` | kstat.zfs.misc.arcstats.l2_hdr_size | untyped | — |
| `node_zfs_arc_l2_hits` | kstat.zfs.misc.arcstats.l2_hits | untyped | — |
| `node_zfs_arc_l2_io_error` | kstat.zfs.misc.arcstats.l2_io_error | untyped | — |
| `node_zfs_arc_l2_misses` | kstat.zfs.misc.arcstats.l2_misses | untyped | — |
| `node_zfs_arc_l2_read_bytes` | kstat.zfs.misc.arcstats.l2_read_bytes | untyped | — |
| `node_zfs_arc_l2_rw_clash` | kstat.zfs.misc.arcstats.l2_rw_clash | untyped | — |
| `node_zfs_arc_l2_size` | kstat.zfs.misc.arcstats.l2_size | untyped | — |
| `node_zfs_arc_l2_write_bytes` | kstat.zfs.misc.arcstats.l2_write_bytes | untyped | — |
| `node_zfs_arc_l2_writes_done` | kstat.zfs.misc.arcstats.l2_writes_done | untyped | — |
| `node_zfs_arc_l2_writes_error` | kstat.zfs.misc.arcstats.l2_writes_error | untyped | — |
| `node_zfs_arc_l2_writes_lock_retry` | kstat.zfs.misc.arcstats.l2_writes_lock_retry | untyped | — |
| `node_zfs_arc_l2_writes_sent` | kstat.zfs.misc.arcstats.l2_writes_sent | untyped | — |
| `node_zfs_arc_memory_direct_count` | kstat.zfs.misc.arcstats.memory_direct_count | untyped | — |
| `node_zfs_arc_memory_indirect_count` | kstat.zfs.misc.arcstats.memory_indirect_count | untyped | — |
| `node_zfs_arc_memory_throttle_count` | kstat.zfs.misc.arcstats.memory_throttle_count | untyped | — |
| `node_zfs_arc_metadata_size` | kstat.zfs.misc.arcstats.metadata_size | untyped | — |
| `node_zfs_arc_mfu_evictable_data` | kstat.zfs.misc.arcstats.mfu_evictable_data | untyped | — |
| `node_zfs_arc_mfu_evictable_metadata` | kstat.zfs.misc.arcstats.mfu_evictable_metadata | untyped | — |
| `node_zfs_arc_mfu_ghost_evictable_data` | kstat.zfs.misc.arcstats.mfu_ghost_evictable_data | untyped | — |
| `node_zfs_arc_mfu_ghost_evictable_metadata` | kstat.zfs.misc.arcstats.mfu_ghost_evictable_metadata | untyped | — |
| `node_zfs_arc_mfu_ghost_hits` | kstat.zfs.misc.arcstats.mfu_ghost_hits | untyped | — |
| `node_zfs_arc_mfu_ghost_size` | kstat.zfs.misc.arcstats.mfu_ghost_size | untyped | — |
| `node_zfs_arc_mfu_hits` | kstat.zfs.misc.arcstats.mfu_hits | untyped | — |
| `node_zfs_arc_mfu_size` | kstat.zfs.misc.arcstats.mfu_size | untyped | — |
| `node_zfs_arc_misses` | kstat.zfs.misc.arcstats.misses | untyped | — |
| `node_zfs_arc_mru_evictable_data` | kstat.zfs.misc.arcstats.mru_evictable_data | untyped | — |
| `node_zfs_arc_mru_evictable_metadata` | kstat.zfs.misc.arcstats.mru_evictable_metadata | untyped | — |
| `node_zfs_arc_mru_ghost_evictable_data` | kstat.zfs.misc.arcstats.mru_ghost_evictable_data | untyped | — |
| `node_zfs_arc_mru_ghost_evictable_metadata` | kstat.zfs.misc.arcstats.mru_ghost_evictable_metadata | untyped | — |
| `node_zfs_arc_mru_ghost_hits` | kstat.zfs.misc.arcstats.mru_ghost_hits | untyped | — |
| `node_zfs_arc_mru_ghost_size` | kstat.zfs.misc.arcstats.mru_ghost_size | untyped | — |
| `node_zfs_arc_mru_hits` | kstat.zfs.misc.arcstats.mru_hits | untyped | — |
| `node_zfs_arc_mru_size` | kstat.zfs.misc.arcstats.mru_size | untyped | — |
| `node_zfs_arc_mutex_miss` | kstat.zfs.misc.arcstats.mutex_miss | untyped | — |
| `node_zfs_arc_other_size` | kstat.zfs.misc.arcstats.other_size | untyped | — |
| `node_zfs_arc_p` | kstat.zfs.misc.arcstats.p | untyped | — |
| `node_zfs_arc_prefetch_data_hits` | kstat.zfs.misc.arcstats.prefetch_data_hits | untyped | — |
| `node_zfs_arc_prefetch_data_misses` | kstat.zfs.misc.arcstats.prefetch_data_misses | untyped | — |
| `node_zfs_arc_prefetch_metadata_hits` | kstat.zfs.misc.arcstats.prefetch_metadata_hits | untyped | — |
| `node_zfs_arc_prefetch_metadata_misses` | kstat.zfs.misc.arcstats.prefetch_metadata_misses | untyped | — |
| `node_zfs_arc_size` | kstat.zfs.misc.arcstats.size | untyped | — |
| `node_zfs_dbuf_dbuf_cache_count` | kstat.zfs.misc.dbufstats.dbuf_cache_count | untyped | — |
| `node_zfs_dbuf_dbuf_cache_hiwater_bytes` | kstat.zfs.misc.dbufstats.dbuf_cache_hiwater_bytes | untyped | — |
| `node_zfs_dbuf_dbuf_cache_level_0` | kstat.zfs.misc.dbufstats.dbuf_cache_level_0 | untyped | — |
| `node_zfs_dbuf_dbuf_cache_level_0_bytes` | kstat.zfs.misc.dbufstats.dbuf_cache_level_0_bytes | untyped | — |
| `node_zfs_dbuf_dbuf_cache_level_1` | kstat.zfs.misc.dbufstats.dbuf_cache_level_1 | untyped | — |
| `node_zfs_dbuf_dbuf_cache_level_10` | kstat.zfs.misc.dbufstats.dbuf_cache_level_10 | untyped | — |
| `node_zfs_dbuf_dbuf_cache_level_10_bytes` | kstat.zfs.misc.dbufstats.dbuf_cache_level_10_bytes | untyped | — |
| `node_zfs_dbuf_dbuf_cache_level_11` | kstat.zfs.misc.dbufstats.dbuf_cache_level_11 | untyped | — |
| `node_zfs_dbuf_dbuf_cache_level_11_bytes` | kstat.zfs.misc.dbufstats.dbuf_cache_level_11_bytes | untyped | — |
| `node_zfs_dbuf_dbuf_cache_level_1_bytes` | kstat.zfs.misc.dbufstats.dbuf_cache_level_1_bytes | untyped | — |
| `node_zfs_dbuf_dbuf_cache_level_2` | kstat.zfs.misc.dbufstats.dbuf_cache_level_2 | untyped | — |
| `node_zfs_dbuf_dbuf_cache_level_2_bytes` | kstat.zfs.misc.dbufstats.dbuf_cache_level_2_bytes | untyped | — |
| `node_zfs_dbuf_dbuf_cache_level_3` | kstat.zfs.misc.dbufstats.dbuf_cache_level_3 | untyped | — |
| `node_zfs_dbuf_dbuf_cache_level_3_bytes` | kstat.zfs.misc.dbufstats.dbuf_cache_level_3_bytes | untyped | — |
| `node_zfs_dbuf_dbuf_cache_level_4` | kstat.zfs.misc.dbufstats.dbuf_cache_level_4 | untyped | — |
| `node_zfs_dbuf_dbuf_cache_level_4_bytes` | kstat.zfs.misc.dbufstats.dbuf_cache_level_4_bytes | untyped | — |
| `node_zfs_dbuf_dbuf_cache_level_5` | kstat.zfs.misc.dbufstats.dbuf_cache_level_5 | untyped | — |
| `node_zfs_dbuf_dbuf_cache_level_5_bytes` | kstat.zfs.misc.dbufstats.dbuf_cache_level_5_bytes | untyped | — |
| `node_zfs_dbuf_dbuf_cache_level_6` | kstat.zfs.misc.dbufstats.dbuf_cache_level_6 | untyped | — |
| `node_zfs_dbuf_dbuf_cache_level_6_bytes` | kstat.zfs.misc.dbufstats.dbuf_cache_level_6_bytes | untyped | — |
| `node_zfs_dbuf_dbuf_cache_level_7` | kstat.zfs.misc.dbufstats.dbuf_cache_level_7 | untyped | — |
| `node_zfs_dbuf_dbuf_cache_level_7_bytes` | kstat.zfs.misc.dbufstats.dbuf_cache_level_7_bytes | untyped | — |
| `node_zfs_dbuf_dbuf_cache_level_8` | kstat.zfs.misc.dbufstats.dbuf_cache_level_8 | untyped | — |
| `node_zfs_dbuf_dbuf_cache_level_8_bytes` | kstat.zfs.misc.dbufstats.dbuf_cache_level_8_bytes | untyped | — |
| `node_zfs_dbuf_dbuf_cache_level_9` | kstat.zfs.misc.dbufstats.dbuf_cache_level_9 | untyped | — |
| `node_zfs_dbuf_dbuf_cache_level_9_bytes` | kstat.zfs.misc.dbufstats.dbuf_cache_level_9_bytes | untyped | — |
| `node_zfs_dbuf_dbuf_cache_lowater_bytes` | kstat.zfs.misc.dbufstats.dbuf_cache_lowater_bytes | untyped | — |
| `node_zfs_dbuf_dbuf_cache_max_bytes` | kstat.zfs.misc.dbufstats.dbuf_cache_max_bytes | untyped | — |
| `node_zfs_dbuf_dbuf_cache_size` | kstat.zfs.misc.dbufstats.dbuf_cache_size | untyped | — |
| `node_zfs_dbuf_dbuf_cache_size_max` | kstat.zfs.misc.dbufstats.dbuf_cache_size_max | untyped | — |
| `node_zfs_dbuf_dbuf_cache_total_evicts` | kstat.zfs.misc.dbufstats.dbuf_cache_total_evicts | untyped | — |
| `node_zfs_dbuf_hash_chain_max` | kstat.zfs.misc.dbufstats.hash_chain_max | untyped | — |
| `node_zfs_dbuf_hash_chains` | kstat.zfs.misc.dbufstats.hash_chains | untyped | — |
| `node_zfs_dbuf_hash_collisions` | kstat.zfs.misc.dbufstats.hash_collisions | untyped | — |
| `node_zfs_dbuf_hash_dbuf_level_0` | kstat.zfs.misc.dbufstats.hash_dbuf_level_0 | untyped | — |
| `node_zfs_dbuf_hash_dbuf_level_0_bytes` | kstat.zfs.misc.dbufstats.hash_dbuf_level_0_bytes | untyped | — |
| `node_zfs_dbuf_hash_dbuf_level_1` | kstat.zfs.misc.dbufstats.hash_dbuf_level_1 | untyped | — |
| `node_zfs_dbuf_hash_dbuf_level_10` | kstat.zfs.misc.dbufstats.hash_dbuf_level_10 | untyped | — |
| `node_zfs_dbuf_hash_dbuf_level_10_bytes` | kstat.zfs.misc.dbufstats.hash_dbuf_level_10_bytes | untyped | — |
| `node_zfs_dbuf_hash_dbuf_level_11` | kstat.zfs.misc.dbufstats.hash_dbuf_level_11 | untyped | — |
| `node_zfs_dbuf_hash_dbuf_level_11_bytes` | kstat.zfs.misc.dbufstats.hash_dbuf_level_11_bytes | untyped | — |
| `node_zfs_dbuf_hash_dbuf_level_1_bytes` | kstat.zfs.misc.dbufstats.hash_dbuf_level_1_bytes | untyped | — |
| `node_zfs_dbuf_hash_dbuf_level_2` | kstat.zfs.misc.dbufstats.hash_dbuf_level_2 | untyped | — |
| `node_zfs_dbuf_hash_dbuf_level_2_bytes` | kstat.zfs.misc.dbufstats.hash_dbuf_level_2_bytes | untyped | — |
| `node_zfs_dbuf_hash_dbuf_level_3` | kstat.zfs.misc.dbufstats.hash_dbuf_level_3 | untyped | — |
| `node_zfs_dbuf_hash_dbuf_level_3_bytes` | kstat.zfs.misc.dbufstats.hash_dbuf_level_3_bytes | untyped | — |
| `node_zfs_dbuf_hash_dbuf_level_4` | kstat.zfs.misc.dbufstats.hash_dbuf_level_4 | untyped | — |
| `node_zfs_dbuf_hash_dbuf_level_4_bytes` | kstat.zfs.misc.dbufstats.hash_dbuf_level_4_bytes | untyped | — |
| `node_zfs_dbuf_hash_dbuf_level_5` | kstat.zfs.misc.dbufstats.hash_dbuf_level_5 | untyped | — |
| `node_zfs_dbuf_hash_dbuf_level_5_bytes` | kstat.zfs.misc.dbufstats.hash_dbuf_level_5_bytes | untyped | — |
| `node_zfs_dbuf_hash_dbuf_level_6` | kstat.zfs.misc.dbufstats.hash_dbuf_level_6 | untyped | — |
| `node_zfs_dbuf_hash_dbuf_level_6_bytes` | kstat.zfs.misc.dbufstats.hash_dbuf_level_6_bytes | untyped | — |
| `node_zfs_dbuf_hash_dbuf_level_7` | kstat.zfs.misc.dbufstats.hash_dbuf_level_7 | untyped | — |
| `node_zfs_dbuf_hash_dbuf_level_7_bytes` | kstat.zfs.misc.dbufstats.hash_dbuf_level_7_bytes | untyped | — |
| `node_zfs_dbuf_hash_dbuf_level_8` | kstat.zfs.misc.dbufstats.hash_dbuf_level_8 | untyped | — |
| `node_zfs_dbuf_hash_dbuf_level_8_bytes` | kstat.zfs.misc.dbufstats.hash_dbuf_level_8_bytes | untyped | — |
| `node_zfs_dbuf_hash_dbuf_level_9` | kstat.zfs.misc.dbufstats.hash_dbuf_level_9 | untyped | — |
| `node_zfs_dbuf_hash_dbuf_level_9_bytes` | kstat.zfs.misc.dbufstats.hash_dbuf_level_9_bytes | untyped | — |
| `node_zfs_dbuf_hash_elements` | kstat.zfs.misc.dbufstats.hash_elements | untyped | — |
| `node_zfs_dbuf_hash_elements_max` | kstat.zfs.misc.dbufstats.hash_elements_max | untyped | — |
| `node_zfs_dbuf_hash_hits` | kstat.zfs.misc.dbufstats.hash_hits | untyped | — |
| `node_zfs_dbuf_hash_insert_race` | kstat.zfs.misc.dbufstats.hash_insert_race | untyped | — |
| `node_zfs_dbuf_hash_misses` | kstat.zfs.misc.dbufstats.hash_misses | untyped | — |
| `node_zfs_dmu_tx_dmu_tx_assigned` | kstat.zfs.misc.dmu_tx.dmu_tx_assigned | untyped | — |
| `node_zfs_dmu_tx_dmu_tx_delay` | kstat.zfs.misc.dmu_tx.dmu_tx_delay | untyped | — |
| `node_zfs_dmu_tx_dmu_tx_dirty_delay` | kstat.zfs.misc.dmu_tx.dmu_tx_dirty_delay | untyped | — |
| `node_zfs_dmu_tx_dmu_tx_dirty_over_max` | kstat.zfs.misc.dmu_tx.dmu_tx_dirty_over_max | untyped | — |
| `node_zfs_dmu_tx_dmu_tx_dirty_throttle` | kstat.zfs.misc.dmu_tx.dmu_tx_dirty_throttle | untyped | — |
| `node_zfs_dmu_tx_dmu_tx_error` | kstat.zfs.misc.dmu_tx.dmu_tx_error | untyped | — |
| `node_zfs_dmu_tx_dmu_tx_group` | kstat.zfs.misc.dmu_tx.dmu_tx_group | untyped | — |
| `node_zfs_dmu_tx_dmu_tx_memory_reclaim` | kstat.zfs.misc.dmu_tx.dmu_tx_memory_reclaim | untyped | — |
| `node_zfs_dmu_tx_dmu_tx_memory_reserve` | kstat.zfs.misc.dmu_tx.dmu_tx_memory_reserve | untyped | — |
| `node_zfs_dmu_tx_dmu_tx_quota` | kstat.zfs.misc.dmu_tx.dmu_tx_quota | untyped | — |
| `node_zfs_dmu_tx_dmu_tx_suspended` | kstat.zfs.misc.dmu_tx.dmu_tx_suspended | untyped | — |
| `node_zfs_dnode_dnode_alloc_next_block` | kstat.zfs.misc.dnodestats.dnode_alloc_next_block | untyped | — |
| `node_zfs_dnode_dnode_alloc_next_chunk` | kstat.zfs.misc.dnodestats.dnode_alloc_next_chunk | untyped | — |
| `node_zfs_dnode_dnode_alloc_race` | kstat.zfs.misc.dnodestats.dnode_alloc_race | untyped | — |
| `node_zfs_dnode_dnode_allocate` | kstat.zfs.misc.dnodestats.dnode_allocate | untyped | — |
| `node_zfs_dnode_dnode_buf_evict` | kstat.zfs.misc.dnodestats.dnode_buf_evict | untyped | — |
| `node_zfs_dnode_dnode_hold_alloc_hits` | kstat.zfs.misc.dnodestats.dnode_hold_alloc_hits | untyped | — |
| `node_zfs_dnode_dnode_hold_alloc_interior` | kstat.zfs.misc.dnodestats.dnode_hold_alloc_interior | untyped | — |
| `node_zfs_dnode_dnode_hold_alloc_lock_misses` | kstat.zfs.misc.dnodestats.dnode_hold_alloc_lock_misses | untyped | — |
| `node_zfs_dnode_dnode_hold_alloc_lock_retry` | kstat.zfs.misc.dnodestats.dnode_hold_alloc_lock_retry | untyped | — |
| `node_zfs_dnode_dnode_hold_alloc_misses` | kstat.zfs.misc.dnodestats.dnode_hold_alloc_misses | untyped | — |
| `node_zfs_dnode_dnode_hold_alloc_type_none` | kstat.zfs.misc.dnodestats.dnode_hold_alloc_type_none | untyped | — |
| `node_zfs_dnode_dnode_hold_dbuf_hold` | kstat.zfs.misc.dnodestats.dnode_hold_dbuf_hold | untyped | — |
| `node_zfs_dnode_dnode_hold_dbuf_read` | kstat.zfs.misc.dnodestats.dnode_hold_dbuf_read | untyped | — |
| `node_zfs_dnode_dnode_hold_free_hits` | kstat.zfs.misc.dnodestats.dnode_hold_free_hits | untyped | — |
| `node_zfs_dnode_dnode_hold_free_lock_misses` | kstat.zfs.misc.dnodestats.dnode_hold_free_lock_misses | untyped | — |
| `node_zfs_dnode_dnode_hold_free_lock_retry` | kstat.zfs.misc.dnodestats.dnode_hold_free_lock_retry | untyped | — |
| `node_zfs_dnode_dnode_hold_free_misses` | kstat.zfs.misc.dnodestats.dnode_hold_free_misses | untyped | — |
| `node_zfs_dnode_dnode_hold_free_overflow` | kstat.zfs.misc.dnodestats.dnode_hold_free_overflow | untyped | — |
| `node_zfs_dnode_dnode_hold_free_refcount` | kstat.zfs.misc.dnodestats.dnode_hold_free_refcount | untyped | — |
| `node_zfs_dnode_dnode_hold_free_txg` | kstat.zfs.misc.dnodestats.dnode_hold_free_txg | untyped | — |
| `node_zfs_dnode_dnode_move_active` | kstat.zfs.misc.dnodestats.dnode_move_active | untyped | — |
| `node_zfs_dnode_dnode_move_handle` | kstat.zfs.misc.dnodestats.dnode_move_handle | untyped | — |
| `node_zfs_dnode_dnode_move_invalid` | kstat.zfs.misc.dnodestats.dnode_move_invalid | untyped | — |
| `node_zfs_dnode_dnode_move_recheck1` | kstat.zfs.misc.dnodestats.dnode_move_recheck1 | untyped | — |
| `node_zfs_dnode_dnode_move_recheck2` | kstat.zfs.misc.dnodestats.dnode_move_recheck2 | untyped | — |
| `node_zfs_dnode_dnode_move_rwlock` | kstat.zfs.misc.dnodestats.dnode_move_rwlock | untyped | — |
| `node_zfs_dnode_dnode_move_special` | kstat.zfs.misc.dnodestats.dnode_move_special | untyped | — |
| `node_zfs_dnode_dnode_reallocate` | kstat.zfs.misc.dnodestats.dnode_reallocate | untyped | — |
| `node_zfs_fm_erpt_dropped` | kstat.zfs.misc.fm.erpt-dropped | untyped | — |
| `node_zfs_fm_erpt_set_failed` | kstat.zfs.misc.fm.erpt-set-failed | untyped | — |
| `node_zfs_fm_fmri_set_failed` | kstat.zfs.misc.fm.fmri-set-failed | untyped | — |
| `node_zfs_fm_payload_set_failed` | kstat.zfs.misc.fm.payload-set-failed | untyped | — |
| `node_zfs_vdev_cache_delegations` | kstat.zfs.misc.vdev_cache_stats.delegations | untyped | — |
| `node_zfs_vdev_cache_hits` | kstat.zfs.misc.vdev_cache_stats.hits | untyped | — |
| `node_zfs_vdev_cache_misses` | kstat.zfs.misc.vdev_cache_stats.misses | untyped | — |
| `node_zfs_vdev_mirror_non_rotating_linear` | kstat.zfs.misc.vdev_mirror_stats.non_rotating_linear | untyped | — |
| `node_zfs_vdev_mirror_non_rotating_seek` | kstat.zfs.misc.vdev_mirror_stats.non_rotating_seek | untyped | — |
| `node_zfs_vdev_mirror_preferred_found` | kstat.zfs.misc.vdev_mirror_stats.preferred_found | untyped | — |
| `node_zfs_vdev_mirror_preferred_not_found` | kstat.zfs.misc.vdev_mirror_stats.preferred_not_found | untyped | — |
| `node_zfs_vdev_mirror_rotating_linear` | kstat.zfs.misc.vdev_mirror_stats.rotating_linear | untyped | — |
| `node_zfs_vdev_mirror_rotating_offset` | kstat.zfs.misc.vdev_mirror_stats.rotating_offset | untyped | — |
| `node_zfs_vdev_mirror_rotating_seek` | kstat.zfs.misc.vdev_mirror_stats.rotating_seek | untyped | — |
| `node_zfs_xuio_onloan_read_buf` | kstat.zfs.misc.xuio_stats.onloan_read_buf | untyped | — |
| `node_zfs_xuio_onloan_write_buf` | kstat.zfs.misc.xuio_stats.onloan_write_buf | untyped | — |
| `node_zfs_xuio_read_buf_copied` | kstat.zfs.misc.xuio_stats.read_buf_copied | untyped | — |
| `node_zfs_xuio_read_buf_nocopy` | kstat.zfs.misc.xuio_stats.read_buf_nocopy | untyped | — |
| `node_zfs_xuio_write_buf_copied` | kstat.zfs.misc.xuio_stats.write_buf_copied | untyped | — |
| `node_zfs_xuio_write_buf_nocopy` | kstat.zfs.misc.xuio_stats.write_buf_nocopy | untyped | — |
| `node_zfs_zfetch_bogus_streams` | kstat.zfs.misc.zfetchstats.bogus_streams | untyped | — |
| `node_zfs_zfetch_colinear_hits` | kstat.zfs.misc.zfetchstats.colinear_hits | untyped | — |
| `node_zfs_zfetch_colinear_misses` | kstat.zfs.misc.zfetchstats.colinear_misses | untyped | — |
| `node_zfs_zfetch_hits` | kstat.zfs.misc.zfetchstats.hits | untyped | — |
| `node_zfs_zfetch_misses` | kstat.zfs.misc.zfetchstats.misses | untyped | — |
| `node_zfs_zfetch_reclaim_failures` | kstat.zfs.misc.zfetchstats.reclaim_failures | untyped | — |
| `node_zfs_zfetch_reclaim_successes` | kstat.zfs.misc.zfetchstats.reclaim_successes | untyped | — |
| `node_zfs_zfetch_streams_noresets` | kstat.zfs.misc.zfetchstats.streams_noresets | untyped | — |
| `node_zfs_zfetch_streams_resets` | kstat.zfs.misc.zfetchstats.streams_resets | untyped | — |
| `node_zfs_zfetch_stride_hits` | kstat.zfs.misc.zfetchstats.stride_hits | untyped | — |
| `node_zfs_zfetch_stride_misses` | kstat.zfs.misc.zfetchstats.stride_misses | untyped | — |
| `node_zfs_zil_zil_commit_count` | kstat.zfs.misc.zil.zil_commit_count | untyped | — |
| `node_zfs_zil_zil_commit_writer_count` | kstat.zfs.misc.zil.zil_commit_writer_count | untyped | — |
| `node_zfs_zil_zil_itx_copied_bytes` | kstat.zfs.misc.zil.zil_itx_copied_bytes | untyped | — |
| `node_zfs_zil_zil_itx_copied_count` | kstat.zfs.misc.zil.zil_itx_copied_count | untyped | — |
| `node_zfs_zil_zil_itx_count` | kstat.zfs.misc.zil.zil_itx_count | untyped | — |
| `node_zfs_zil_zil_itx_indirect_bytes` | kstat.zfs.misc.zil.zil_itx_indirect_bytes | untyped | — |
| `node_zfs_zil_zil_itx_indirect_count` | kstat.zfs.misc.zil.zil_itx_indirect_count | untyped | — |
| `node_zfs_zil_zil_itx_metaslab_normal_bytes` | kstat.zfs.misc.zil.zil_itx_metaslab_normal_bytes | untyped | — |
| `node_zfs_zil_zil_itx_metaslab_normal_count` | kstat.zfs.misc.zil.zil_itx_metaslab_normal_count | untyped | — |
| `node_zfs_zil_zil_itx_metaslab_slog_bytes` | kstat.zfs.misc.zil.zil_itx_metaslab_slog_bytes | untyped | — |
| `node_zfs_zil_zil_itx_metaslab_slog_count` | kstat.zfs.misc.zil.zil_itx_metaslab_slog_count | untyped | — |
| `node_zfs_zil_zil_itx_needcopy_bytes` | kstat.zfs.misc.zil.zil_itx_needcopy_bytes | untyped | — |
| `node_zfs_zil_zil_itx_needcopy_count` | kstat.zfs.misc.zil.zil_itx_needcopy_count | untyped | — |
| `node_zfs_zpool_dataset_nread` | kstat.zfs.misc.objset.nread | untyped | dataset, zpool |
| `node_zfs_zpool_dataset_nunlinked` | kstat.zfs.misc.objset.nunlinked | untyped | dataset, zpool |
| `node_zfs_zpool_dataset_nunlinks` | kstat.zfs.misc.objset.nunlinks | untyped | dataset, zpool |
| `node_zfs_zpool_dataset_nwritten` | kstat.zfs.misc.objset.nwritten | untyped | dataset, zpool |
| `node_zfs_zpool_dataset_reads` | kstat.zfs.misc.objset.reads | untyped | dataset, zpool |
| `node_zfs_zpool_dataset_writes` | kstat.zfs.misc.objset.writes | untyped | dataset, zpool |
| `node_zfs_zpool_nread` | kstat.zfs.misc.io.nread | untyped | zpool |
| `node_zfs_zpool_nwritten` | kstat.zfs.misc.io.nwritten | untyped | zpool |
| `node_zfs_zpool_rcnt` | kstat.zfs.misc.io.rcnt | untyped | zpool |
| `node_zfs_zpool_reads` | kstat.zfs.misc.io.reads | untyped | zpool |
| `node_zfs_zpool_rlentime` | kstat.zfs.misc.io.rlentime | untyped | zpool |
| `node_zfs_zpool_rtime` | kstat.zfs.misc.io.rtime | untyped | zpool |
| `node_zfs_zpool_rupdate` | kstat.zfs.misc.io.rupdate | untyped | zpool |
| `node_zfs_zpool_state` | kstat.zfs.misc.state | gauge | state, zpool |
| `node_zfs_zpool_wcnt` | kstat.zfs.misc.io.wcnt | untyped | zpool |
| `node_zfs_zpool_wlentime` | kstat.zfs.misc.io.wlentime | untyped | zpool |
| `node_zfs_zpool_writes` | kstat.zfs.misc.io.writes | untyped | zpool |
| `node_zfs_zpool_wtime` | kstat.zfs.misc.io.wtime | untyped | zpool |
| `node_zfs_zpool_wupdate` | kstat.zfs.misc.io.wupdate | untyped | zpool |
| `node_zoneinfo_high_pages` | Zone watermark pages_high | gauge | node, zone |
| `node_zoneinfo_low_pages` | Zone watermark pages_low | gauge | node, zone |
| `node_zoneinfo_managed_pages` | Present pages managed by the buddy system | gauge | node, zone |
| `node_zoneinfo_min_pages` | Zone watermark pages_min | gauge | node, zone |
| `node_zoneinfo_nr_active_anon_pages` | Number of anonymous pages recently more used | gauge | node, zone |
| `node_zoneinfo_nr_active_file_pages` | Number of active pages with file-backing | gauge | node, zone |
| `node_zoneinfo_nr_anon_pages` | Number of anonymous pages currently used by the system | gauge | node, zone |
| `node_zoneinfo_nr_anon_transparent_hugepages` | Number of anonymous transparent huge pages currently used by the system | gauge | node, zone |
| `node_zoneinfo_nr_dirtied_total` | Page dirtyings since bootup | counter | node, zone |
| `node_zoneinfo_nr_dirty_pages` | Number of dirty pages | gauge | node, zone |
| `node_zoneinfo_nr_file_pages` | Number of file pages | gauge | node, zone |
| `node_zoneinfo_nr_free_pages` | Total number of free pages in the zone | gauge | node, zone |
| `node_zoneinfo_nr_inactive_anon_pages` | Number of anonymous pages recently less used | gauge | node, zone |
| `node_zoneinfo_nr_inactive_file_pages` | Number of inactive pages with file-backing | gauge | node, zone |
| `node_zoneinfo_nr_isolated_anon_pages` | Temporary isolated pages from anon lru | gauge | node, zone |
| `node_zoneinfo_nr_isolated_file_pages` | Temporary isolated pages from file lru | gauge | node, zone |
| `node_zoneinfo_nr_kernel_stacks` | Number of kernel stacks | gauge | node, zone |
| `node_zoneinfo_nr_mapped_pages` | Number of mapped pages | gauge | node, zone |
| `node_zoneinfo_nr_shmem_pages` | Number of shmem pages (included tmpfs/GEM pages) | gauge | node, zone |
| `node_zoneinfo_nr_slab_reclaimable_pages` | Number of reclaimable slab pages | gauge | node, zone |
| `node_zoneinfo_nr_slab_unreclaimable_pages` | Number of unreclaimable slab pages | gauge | node, zone |
| `node_zoneinfo_nr_unevictable_pages` | Number of unevictable pages | gauge | node, zone |
| `node_zoneinfo_nr_writeback_pages` | Number of writeback pages | gauge | node, zone |
| `node_zoneinfo_nr_written_total` | Page writings since bootup | counter | node, zone |
| `node_zoneinfo_numa_foreign_total` | Was intended here, hit elsewhere | counter | node, zone |
| `node_zoneinfo_numa_hit_total` | Allocated in intended node | counter | node, zone |
| `node_zoneinfo_numa_interleave_total` | Interleaver preferred this zone | counter | node, zone |
| `node_zoneinfo_numa_local_total` | Allocation from local node | counter | node, zone |
| `node_zoneinfo_numa_miss_total` | Allocated in non intended node | counter | node, zone |
| `node_zoneinfo_numa_other_total` | Allocation from other node | counter | node, zone |
| `node_zoneinfo_present_pages` | Physical pages existing within the zone | gauge | node, zone |
| `node_zoneinfo_protection_0` | Protection array 0. field | gauge | node, zone |
| `node_zoneinfo_protection_1` | Protection array 1. field | gauge | node, zone |
| `node_zoneinfo_protection_2` | Protection array 2. field | gauge | node, zone |
| `node_zoneinfo_protection_3` | Protection array 3. field | gauge | node, zone |
| `node_zoneinfo_protection_4` | Protection array 4. field | gauge | node, zone |
| `node_zoneinfo_spanned_pages` | Total pages spanned by the zone, including holes | gauge | node, zone |

</details>

### Memcached exporter 0.15.0 — тестовые экспозиции

[Источник](https://github.com/prometheus/memcached_exporter/tree/v0.15.0). В исходном каталоге 70 имён; здесь 57 дополнительных строк, остальные уже описаны выше.

<details>
<summary>Развернуть полный дополнительный перечень</summary>

| Название | Исходное описание / HELP | Тип | Атрибуты из источника |
|---|---|---|---|
| `memcached_accepting_conns` | The Memcached server is currently accepting new connections. | gauge | — |
| `memcached_connections_listener_disabled_total` | Number of times that memcached has hit its connections limit and disabled its listener. | counter | — |
| `memcached_connections_yielded_total` | Total number of connections yielded running due to hitting the memcached's -R limit. | counter | — |
| `memcached_direct_reclaims_total` | Times worker threads had to directly reclaim or evict items. | counter | — |
| `memcached_lru_crawler_enabled` | Whether the LRU crawler is enabled. | gauge | — |
| `memcached_lru_crawler_hot_max_factor` | Set idle age of HOT LRU to COLD age * this | gauge | — |
| `memcached_lru_crawler_hot_percent` | Percent of slab memory reserved for HOT LRU. | gauge | — |
| `memcached_lru_crawler_items_checked_total` | Total items examined by LRU Crawler. | counter | — |
| `memcached_lru_crawler_maintainer_thread` | Split LRU mode and background threads. | gauge | — |
| `memcached_lru_crawler_moves_to_cold_total` | Total number of items moved from HOT/WARM to COLD LRU's. | counter | — |
| `memcached_lru_crawler_moves_to_warm_total` | Total number of items moved from COLD to WARM LRU. | counter | — |
| `memcached_lru_crawler_moves_within_lru_total` | Total number of items reshuffled within HOT or WARM LRU's. | counter | — |
| `memcached_lru_crawler_reclaimed_total` | Total items freed by LRU Crawler. | counter | — |
| `memcached_lru_crawler_sleep` | Microseconds to sleep between LRU crawls. | gauge | — |
| `memcached_lru_crawler_starts_total` | Times an LRU crawler was started. | counter | — |
| `memcached_lru_crawler_to_crawl` | Max items to crawl per slab per run. | gauge | — |
| `memcached_lru_crawler_warm_max_factor` | Set idle age of WARM LRU to COLD age * this | gauge | — |
| `memcached_lru_crawler_warm_percent` | Percent of slab memory reserved for WARM LRU. | gauge | — |
| `memcached_malloced_bytes` | Number of bytes of memory allocated to slab pages. | gauge | — |
| `memcached_max_connections` | Maximum number of clients allowed. | gauge | — |
| `memcached_process_cpu_seconds_total` | Total user and system CPU time spent in seconds. | counter | — |
| `memcached_process_max_fds` | Maximum number of open file descriptors. | gauge | — |
| `memcached_process_open_fds` | Number of open file descriptors. | gauge | — |
| `memcached_process_resident_memory_bytes` | Resident memory size in bytes. | gauge | — |
| `memcached_process_start_time_seconds` | Start time of the process since unix epoch in seconds. | gauge | — |
| `memcached_process_virtual_memory_bytes` | Virtual memory size in bytes. | gauge | — |
| `memcached_slab_chunk_size_bytes` | Number of bytes allocated to each chunk within this slab class. | gauge | — |
| `memcached_slab_chunks_free` | Number of chunks not yet allocated items. | gauge | — |
| `memcached_slab_chunks_free_end` | Number of free chunks at the end of the last allocated page. | gauge | — |
| `memcached_slab_chunks_per_page` | Number of chunks within a single page for this slab class. | gauge | — |
| `memcached_slab_chunks_used` | Number of chunks allocated to an item. | gauge | — |
| `memcached_slab_cold_items` | Number of items presently stored in the COLD LRU. | gauge | — |
| `memcached_slab_commands_total` | Total number of all requests broken down by command (get, set, etc.) and status per slab. | counter | — |
| `memcached_slab_current_chunks` | Number of chunks allocated to this slab class. | gauge | — |
| `memcached_slab_current_items` | Number of items currently stored in this slab class. | gauge | — |
| `memcached_slab_current_pages` | Number of pages allocated to this slab class. | gauge | — |
| `memcached_slab_hot_age_seconds` | Age of the oldest item in HOT LRU. | gauge | — |
| `memcached_slab_hot_items` | Number of items presently stored in the HOT LRU. | gauge | — |
| `memcached_slab_items_age_seconds` | Number of seconds the oldest item has been in the slab class. | gauge | — |
| `memcached_slab_items_crawler_reclaimed_total` | Number of items freed by the LRU Crawler. | counter | — |
| `memcached_slab_items_evicted_nonzero_total` | Total number of times an item which had an explicit expire time set had to be evicted from the LRU before it expired. | counter | — |
| `memcached_slab_items_evicted_time_seconds` | Seconds since the last access for the most recent item evicted from this class. | counter | — |
| `memcached_slab_items_evicted_total` | Total number of times an item had to be evicted from the LRU before it expired. | counter | — |
| `memcached_slab_items_evicted_unfetched_total` | Total nmber of items evicted and never fetched. | counter | — |
| `memcached_slab_items_expired_unfetched_total` | Total number of valid items evicted from the LRU which were never touched after being set. | counter | — |
| `memcached_slab_items_moves_to_cold` | Number of items moved from HOT or WARM into COLD. | counter | — |
| `memcached_slab_items_moves_to_warm` | Number of items moves from COLD into WARM. | counter | — |
| `memcached_slab_items_moves_within_lru` | Number of times active items were bumped within HOT or WARM. | counter | — |
| `memcached_slab_items_outofmemory_total` | Total number of items for this slab class that have triggered an out of memory error. | counter | — |
| `memcached_slab_items_reclaimed_total` | Total number of items reclaimed. | counter | — |
| `memcached_slab_items_tailrepairs_total` | Total number of times the entries for a particular ID need repairing. | counter | — |
| `memcached_slab_lru_hits_total` | Number of get_hits to the LRU. | counter | — |
| `memcached_slab_mem_requested_bytes` | Number of bytes of memory actual items take up within a slab. | counter | — |
| `memcached_slab_warm_age_seconds` | Age of the oldest item in HOT LRU. | gauge | — |
| `memcached_slab_warm_items` | Number of items presently stored in the WARM LRU. | gauge | — |
| `memcached_time_seconds` | current UNIX time according to the server. | gauge | — |
| `memcached_version` | The version of this memcached server. | gauge | — |

</details>

### Elasticsearch exporter 1.8.0 — официальный перечень

[Источник](https://github.com/prometheus-community/elasticsearch_exporter/blob/v1.8.0/README.md). В исходном каталоге 155 имён; здесь 142 дополнительных строк, остальные уже описаны выше.

<details>
<summary>Развернуть полный дополнительный перечень</summary>

| Название | Исходное описание / HELP | Тип | Атрибуты из источника |
|---|---|---|---|
| `elasticsearch_breakers_estimated_size_bytes` | Estimated size in bytes of breaker | gauge | не перечислены источником |
| `elasticsearch_breakers_limit_size_bytes` | Limit size in bytes for breaker | gauge | не перечислены источником |
| `elasticsearch_breakers_tripped` | tripped for breaker | counter | не перечислены источником |
| `elasticsearch_cluster_health_delayed_unassigned_shards` | Shards delayed to reduce reallocation overhead | gauge | не перечислены источником |
| `elasticsearch_cluster_health_number_of_in_flight_fetch` | The number of ongoing shard info requests. | gauge | не перечислены источником |
| `elasticsearch_cluster_health_task_max_waiting_in_queue_millis` | Max time in millis that a task is waiting in queue. | gauge | не перечислены источником |
| `elasticsearch_clusterinfo_last_retrieval_success_ts` | Timestamp of the last successful cluster info retrieval | gauge | не перечислены источником |
| `elasticsearch_clusterinfo_up` | Up metric for the cluster info collector | gauge | не перечислены источником |
| `elasticsearch_clusterinfo_version_info` | Constant metric with ES version information as labels | gauge | не перечислены источником |
| `elasticsearch_clustersettings_allocation_threshold_enabled` | Is disk allocation decider enabled. | gauge | не перечислены источником |
| `elasticsearch_clustersettings_allocation_watermark_flood_stage_bytes` | Flood stage watermark as in bytes. | gauge | не перечислены источником |
| `elasticsearch_clustersettings_allocation_watermark_flood_stage_ratio` | Flood stage watermark as a ratio. | gauge | не перечислены источником |
| `elasticsearch_clustersettings_allocation_watermark_high_bytes` | High watermark for disk usage in bytes. | gauge | не перечислены источником |
| `elasticsearch_clustersettings_allocation_watermark_high_ratio` | High watermark for disk usage as a ratio. | gauge | не перечислены источником |
| `elasticsearch_clustersettings_allocation_watermark_low_bytes` | Low watermark for disk usage in bytes. | gauge | не перечислены источником |
| `elasticsearch_clustersettings_allocation_watermark_low_ratio` | Low watermark for disk usage as a ratio. | gauge | не перечислены источником |
| `elasticsearch_clustersettings_stats_max_shards_per_node` | Current maximum number of shards per node setting. | gauge | не перечислены источником |
| `elasticsearch_data_stream_backing_indices_total` | Number of backing indices for Data Stream | gauge | не перечислены источником |
| `elasticsearch_data_stream_stats_json_parse_failures` | Number of parsing failures for Data Stream stats | counter | не перечислены источником |
| `elasticsearch_data_stream_stats_total_scrapes` | Total scrapes for Data Stream stats | counter | не перечислены источником |
| `elasticsearch_data_stream_stats_up` | Up metric for Data Stream collection | gauge | не перечислены источником |
| `elasticsearch_data_stream_store_size_bytes` | Current size of data stream backing indices in bytes | gauge | не перечислены источником |
| `elasticsearch_filesystem_data_free_bytes` | Free space on block device in bytes | gauge | не перечислены источником |
| `elasticsearch_filesystem_io_stats_device_operations_count` | Count of disk operations | gauge | не перечислены источником |
| `elasticsearch_filesystem_io_stats_device_read_operations_count` | Count of disk read operations | gauge | не перечислены источником |
| `elasticsearch_filesystem_io_stats_device_read_size_kilobytes_sum` | Total kilobytes read from disk | gauge | не перечислены источником |
| `elasticsearch_filesystem_io_stats_device_write_operations_count` | Count of disk write operations | gauge | не перечислены источником |
| `elasticsearch_filesystem_io_stats_device_write_size_kilobytes_sum` | Total kilobytes written to disk | gauge | не перечислены источником |
| `elasticsearch_indices_active_queries` | The number of currently active queries | gauge | не перечислены источником |
| `elasticsearch_indices_deleted_docs_primary` | Count of deleted documents with only primary shards | gauge | не перечислены источником |
| `elasticsearch_indices_docs` | Count of documents on this node | gauge | не перечислены источником |
| `elasticsearch_indices_docs_deleted` | Count of deleted documents on this node | gauge | не перечислены источником |
| `elasticsearch_indices_docs_primary` | Count of documents with only primary shards on all nodes | gauge | не перечислены источником |
| `elasticsearch_indices_docs_total` | Count of documents with shards on all nodes | gauge | не перечислены источником |
| `elasticsearch_indices_fielddata_evictions` | Evictions from field data | counter | не перечислены источником |
| `elasticsearch_indices_fielddata_memory_size_bytes` | Field data cache memory usage in bytes | gauge | не перечислены источником |
| `elasticsearch_indices_filter_cache_evictions` | Evictions from filter cache | counter | не перечислены источником |
| `elasticsearch_indices_filter_cache_memory_size_bytes` | Filter cache memory usage in bytes | gauge | не перечислены источником |
| `elasticsearch_indices_flush_time_seconds` | Cumulative flush time in seconds | counter | не перечислены источником |
| `elasticsearch_indices_flush_total` | Total flushes | counter | не перечислены источником |
| `elasticsearch_indices_get_exists_time_seconds` | Total time get exists in seconds | counter | не перечислены источником |
| `elasticsearch_indices_get_exists_total` | Total get exists operations | counter | не перечислены источником |
| `elasticsearch_indices_get_missing_time_seconds` | Total time of get missing in seconds | counter | не перечислены источником |
| `elasticsearch_indices_get_missing_total` | Total get missing | counter | не перечислены источником |
| `elasticsearch_indices_get_time_seconds` | Total get time in seconds | counter | не перечислены источником |
| `elasticsearch_indices_get_total` | Total get | counter | не перечислены источником |
| `elasticsearch_indices_index_current` | The number of documents currently being indexed to an index | gauge | не перечислены источником |
| `elasticsearch_indices_indexing_delete_time_seconds_total` | Total time indexing delete in seconds | counter | не перечислены источником |
| `elasticsearch_indices_indexing_delete_total` | Total indexing deletes | counter | не перечислены источником |
| `elasticsearch_indices_indexing_index_time_seconds_total` | Cumulative index time in seconds | counter | не перечислены источником |
| `elasticsearch_indices_indexing_index_total` | Total index calls | counter | не перечислены источником |
| `elasticsearch_indices_mappings_stats_fields` | Count of fields currently mapped by index | gauge | не перечислены источником |
| `elasticsearch_indices_mappings_stats_json_parse_failures_total` | Number of errors while parsing JSON | counter | не перечислены источником |
| `elasticsearch_indices_mappings_stats_scrapes_total` | Current total Elasticsearch Indices Mappings scrapes | counter | не перечислены источником |
| `elasticsearch_indices_mappings_stats_up` | Was the last scrape of the Elasticsearch Indices Mappings endpoint successful | gauge | не перечислены источником |
| `elasticsearch_indices_merges_docs_total` | Cumulative docs merged | counter | не перечислены источником |
| `elasticsearch_indices_merges_total` | Total merges | counter | не перечислены источником |
| `elasticsearch_indices_merges_total_size_bytes_total` | Total merge size in bytes | counter | не перечислены источником |
| `elasticsearch_indices_merges_total_time_seconds_total` | Total time spent merging in seconds | counter | не перечислены источником |
| `elasticsearch_indices_query_cache_cache_size` | Size of query cache | gauge | не перечислены источником |
| `elasticsearch_indices_query_cache_cache_total` | Count of query cache | counter | не перечислены источником |
| `elasticsearch_indices_query_cache_count` | Count of query cache hit/miss | counter | не перечислены источником |
| `elasticsearch_indices_query_cache_evictions` | Evictions from query cache | counter | не перечислены источником |
| `elasticsearch_indices_query_cache_memory_size_bytes` | Query cache memory usage in bytes | gauge | не перечислены источником |
| `elasticsearch_indices_query_cache_total` | Size of query cache total | counter | не перечислены источником |
| `elasticsearch_indices_refresh_time_seconds_total` | Total time spent refreshing in seconds | counter | не перечислены источником |
| `elasticsearch_indices_refresh_total` | Total refreshes | counter | не перечислены источником |
| `elasticsearch_indices_request_cache_count` | Count of request cache hit/miss | counter | не перечислены источником |
| `elasticsearch_indices_request_cache_evictions` | Evictions from request cache | counter | не перечислены источником |
| `elasticsearch_indices_request_cache_memory_size_bytes` | Request cache memory usage in bytes | gauge | не перечислены источником |
| `elasticsearch_indices_search_fetch_time_seconds` | Total search fetch time in seconds | counter | не перечислены источником |
| `elasticsearch_indices_search_fetch_total` | Total number of fetches | counter | не перечислены источником |
| `elasticsearch_indices_search_query_time_seconds` | Total search query time in seconds | counter | не перечислены источником |
| `elasticsearch_indices_search_query_total` | Total number of queries | counter | не перечислены источником |
| `elasticsearch_indices_segments_count` | Count of index segments on this node | gauge | не перечислены источником |
| `elasticsearch_indices_segments_memory_bytes` | Current memory size of segments in bytes | gauge | не перечислены источником |
| `elasticsearch_indices_settings_creation_timestamp_seconds` | Timestamp of the index creation in seconds | gauge | не перечислены источником |
| `elasticsearch_indices_settings_replicas` | Index setting value for index.replicas | gauge | не перечислены источником |
| `elasticsearch_indices_settings_stats_read_only_indices` | Count of indices that have read_only_allow_delete=true | gauge | не перечислены источником |
| `elasticsearch_indices_settings_total_fields` | Index setting value for index.mapping.total_fields.limit (total allowable mapped fields in a index) | gauge | не перечислены источником |
| `elasticsearch_indices_shards_docs` | Count of documents on this shard | gauge | не перечислены источником |
| `elasticsearch_indices_shards_docs_deleted` | Count of deleted documents on each shard | gauge | не перечислены источником |
| `elasticsearch_indices_store_size_bytes` | Current size of stored index data in bytes | gauge | не перечислены источником |
| `elasticsearch_indices_store_size_bytes_primary` | Current size of stored index data in bytes with only primary shards on all nodes | gauge | не перечислены источником |
| `elasticsearch_indices_store_size_bytes_total` | Current size of stored index data in bytes with all shards on all nodes | gauge | не перечислены источником |
| `elasticsearch_indices_store_throttle_time_seconds_total` | Throttle time for index store in seconds | counter | не перечислены источником |
| `elasticsearch_indices_translog_operations` | Total translog operations | counter | не перечислены источником |
| `elasticsearch_indices_translog_size_in_bytes` | Total translog size in bytes | counter | не перечислены источником |
| `elasticsearch_indices_warmer_time_seconds_total` | Total warmer time in seconds | counter | не перечислены источником |
| `elasticsearch_indices_warmer_total` | Total warmer count | counter | не перечислены источником |
| `elasticsearch_jvm_gc_collection_seconds_count` | Count of JVM GC runs | counter | не перечислены источником |
| `elasticsearch_jvm_gc_collection_seconds_sum` | GC run time in seconds | counter | не перечислены источником |
| `elasticsearch_jvm_memory_committed_bytes` | JVM memory currently committed by area | gauge | не перечислены источником |
| `elasticsearch_jvm_memory_pool_max_bytes` | JVM memory max by pool | counter | не перечислены источником |
| `elasticsearch_jvm_memory_pool_peak_max_bytes` | JVM memory peak max by pool | counter | не перечислены источником |
| `elasticsearch_jvm_memory_pool_peak_used_bytes` | JVM memory peak used by pool | counter | не перечислены источником |
| `elasticsearch_jvm_memory_pool_used_bytes` | JVM memory currently used by pool | gauge | не перечислены источником |
| `elasticsearch_os_cpu_percent` | Percent CPU used by the OS | gauge | не перечислены источником |
| `elasticsearch_os_load1` | Shortterm load average | gauge | не перечислены источником |
| `elasticsearch_os_load15` | Longterm load average | gauge | не перечислены источником |
| `elasticsearch_os_load5` | Midterm load average | gauge | не перечислены источником |
| `elasticsearch_process_cpu_percent` | Percent CPU used by process | gauge | не перечислены источником |
| `elasticsearch_process_cpu_seconds_total` | Process CPU time in seconds | counter | не перечислены источником |
| `elasticsearch_process_mem_resident_size_bytes` | Resident memory in use by process in bytes | gauge | не перечислены источником |
| `elasticsearch_process_mem_share_size_bytes` | Shared memory in use by process in bytes | gauge | не перечислены источником |
| `elasticsearch_process_mem_virtual_size_bytes` | Total virtual memory used in bytes | gauge | не перечислены источником |
| `elasticsearch_process_open_files_count` | Open file descriptors | gauge | не перечислены источником |
| `elasticsearch_slm_stats_json_parse_failures` | JSON parse failures for SLM collector | counter | не перечислены источником |
| `elasticsearch_slm_stats_operation_mode` | SLM operation mode (Running, stopping, stopped) | gauge | не перечислены источником |
| `elasticsearch_slm_stats_retention_deletion_time_seconds` | Retention run deletion time | gauge | не перечислены источником |
| `elasticsearch_slm_stats_retention_failed_total` | Total failed retention runs | counter | не перечислены источником |
| `elasticsearch_slm_stats_retention_runs_total` | Total retention runs | counter | не перечислены источником |
| `elasticsearch_slm_stats_retention_timed_out_total` | Total retention run timeouts | counter | не перечислены источником |
| `elasticsearch_slm_stats_snapshot_deletion_failures_total` | Snapshot deletion failures by policy | counter | не перечислены источником |
| `elasticsearch_slm_stats_snapshots_deleted_total` | Snapshots deleted by policy | counter | не перечислены источником |
| `elasticsearch_slm_stats_snapshots_failed_total` | Snapshots failed by policy | counter | не перечислены источником |
| `elasticsearch_slm_stats_snapshots_taken_total` | Snapshots taken by policy | counter | не перечислены источником |
| `elasticsearch_slm_stats_total_scrapes` | Number of scrapes for SLM collector | counter | не перечислены источником |
| `elasticsearch_slm_stats_total_snapshots_deleted_total` | Total snapshots deleted | counter | не перечислены источником |
| `elasticsearch_slm_stats_total_snapshots_failed_total` | Total snapshots failed | counter | не перечислены источником |
| `elasticsearch_slm_stats_total_snapshots_taken_total` | Total snapshots taken | counter | не перечислены источником |
| `elasticsearch_slm_stats_up` | Up metric for SLM collector | gauge | не перечислены источником |
| `elasticsearch_snapshot_stats_latest_snapshot_timestamp_seconds` | Timestamp of the latest SUCCESS or PARTIAL snapshot | gauge | не перечислены источником |
| `elasticsearch_snapshot_stats_number_of_snapshots` | Total number of snapshots | gauge | не перечислены источником |
| `elasticsearch_snapshot_stats_oldest_snapshot_timestamp` | Oldest snapshot timestamp | gauge | не перечислены источником |
| `elasticsearch_snapshot_stats_snapshot_end_time_timestamp` | Last snapshot end timestamp | gauge | не перечислены источником |
| `elasticsearch_snapshot_stats_snapshot_failed_shards` | Last snapshot failed shards | gauge | не перечислены источником |
| `elasticsearch_snapshot_stats_snapshot_number_of_failures` | Last snapshot number of failures | gauge | не перечислены источником |
| `elasticsearch_snapshot_stats_snapshot_number_of_indices` | Last snapshot number of indices | gauge | не перечислены источником |
| `elasticsearch_snapshot_stats_snapshot_start_time_timestamp` | Last snapshot start timestamp | gauge | не перечислены источником |
| `elasticsearch_snapshot_stats_snapshot_successful_shards` | Last snapshot successful shards | gauge | не перечислены источником |
| `elasticsearch_snapshot_stats_snapshot_total_shards` | Last snapshot total shard | gauge | не перечислены источником |
| `elasticsearch_thread_pool_active_count` | Thread Pool threads active | gauge | не перечислены источником |
| `elasticsearch_thread_pool_completed_count` | Thread Pool operations completed | counter | не перечислены источником |
| `elasticsearch_thread_pool_largest_count` | Thread Pool largest threads count | gauge | не перечислены источником |
| `elasticsearch_thread_pool_queue_count` | Thread Pool operations queued | gauge | не перечислены источником |
| `elasticsearch_thread_pool_rejected_count` | Thread Pool operations rejected | counter | не перечислены источником |
| `elasticsearch_thread_pool_threads_count` | Thread Pool current threads count | gauge | не перечислены источником |
| `elasticsearch_transport_rx_packets_total` | Count of packets received | counter | не перечислены источником |
| `elasticsearch_transport_rx_size_bytes_total` | Total number of bytes received | counter | не перечислены источником |
| `elasticsearch_transport_tx_packets_total` | Count of packets sent | counter | не перечислены источником |
| `elasticsearch_transport_tx_size_bytes_total` | Total number of bytes sent | counter | не перечислены источником |

</details>

<a id="compatibility"></a>

## Ограничения совместимости и динамические семейства

### Что требует внимания именно с vanilla Epoxy

1. **Libvirt:** `libvirt_domain_block_meta` отсутствует; метаданные диска предоставляет `libvirt_domain_block_stats_info`. `libvirt_domain_info_meta` отсутствует; для связи с OpenStack есть `libvirt_domain_openstack_info` с `instance_id`, а не автоматически эквивалентным `uuid`. Простое переименование без проверки labels не воспроизводит старый join. `libvirt_domain_info_vstate` отсутствует, состояние находится в `libvirt_domain_info_state`. Метрики `libvirt_domain_vcpu_time_seconds_total` и `libvirt_domain_vcpu_delay_seconds_total` в 2.2.0 **есть**.
2. **OpenStack:** `openstack_nova_server_net_info` и `openstack_cinder_snapshot` отсутствуют в 1.7.0. `openstack_cinder_snapshots` — количество snapshots и не заменяет метаданные отдельного snapshot. Старые примеры README могут расходиться с кодом; labels и TYPE в этом документе сверены по descriptors и месту выдачи.
3. **Node:** `node_network_address_info` из старого dashboard заменяется по смыслу `node_network_info`. `node_pressure_irq_stalled_seconds_total` отсутствует в pressure collector 1.8.2. `node_network_trasmit_errs_total` — опечатка. Наличие панели systemd/EDAC/FC/interrupts не включает collector и не создаёт оборудование.
4. **HAProxy/RabbitMQ:** часть PVS-rules использует имена из старых сторонних exporters, тогда как архивы подключают native endpoints. Прикладной `rabbitmq_up` и `haproxy_up` не подменяются автоматически общей метрикой `up` — у них различается смысл.
5. **Recording rules:** в `sber-metrics.rules` дважды определено `az:openstack_nova_memory_used_bytes:sum`. Несколько правил среднего размера блока и latency используют `or rate(...requests_total...)` как fallback; на этой ветке выражения единица меняется. Это описано по существующему коду; правила при подготовке справочника не исправлялись.
6. **Watcher:** CPU/RAM recording rules фильтруют `libvirt_domain_openstack_info{user_name="admin"}`. Это ограничивает охват ВМ. Требования Watcher к `fqdn` и `resource` также должны быть согласованы с фактическим scrape/relabel config.

### Семейства, которые нельзя замкнуть конечным списком по архиву

| Exporter / семейство | Как образуется набор | Как читать |
|---|---|---|
| Node meminfo: `node_memory_<поле>` | Поля /proc/meminfo; KiB-поля переводятся в bytes, счётчики страниц остаются без bytes | Сверять имя поля и единицу; HugePages_* и Hugepagesize_bytes имеют разные единицы. |
| Node netstat/vmstat: `node_netstat_<протокол>_<поле>`, `node_vmstat_<поле>` | Поля ядра /proc/net/netstat, /proc/net/snmp, /proc/vmstat, фильтры collectors | В 1.8.2 generic TYPE=untyped; не всякое поле является накопительным счётчиком. |
| Node textfile | Произвольные .prom файлы | В архиве нет полного набора таких файлов; они могут добавлять любое корректное имя. |
| MySQL: `mysql_global_status_<поле>` | SHOW GLOBAL STATUS после нормализации имени | Generic поля — untyped. com/handler/connection_errors/innodb_* часть полей группируется в отдельные семейства и labels. |
| MySQL: `mysql_global_variables_<поле>` | SHOW GLOBAL VARIABLES и включённые дополнительные collectors | Набор меняется по версии/плагинам СУБД; полное описание даёт экспозиция конкретного сервера. |
| Blackbox: `probe_*` | HTTP/TCP/DNS/ICMP/gRPC module, результат проверки и наличие TLS | HTTP-метрики не обязаны появляться для TCP/ICMP. probe_* на /probe отделены от self-metrics на /metrics. |
| Ironic: `baremetal_<сенсор>`, `baremetal_temp_<PhysicalContext>_celsius` | Поля сообщения от BMC, IPMI/Redfish-парсер | Набор сенсоров и labels определяется оборудованием. Не смешивать с отдельным redfish_exporter. |
| Ceph: `ceph_*` | Версия mgr, topology, пулы и включённые perf counters | Внешний Ceph не получает версию из OpenStack Epoxy; справочные строки не фиксируют схему всех его демонов. |
| Fluentd: произвольные имена metric | prometheus input/filter/output и пользовательская обработка логов | Счётчики событий VM/AMQP из правил требуют определения в конфигурации Fluentd. |
| Go/Python runtime, `process_*`, `go_*`, `python_*`, `promhttp_*`, `*_build_info` | Версия SDK, сборки и регистрация collectors | Не одинаковый обязательный набор для всех exporters. Метрики process_swap_bytes/process_threads и прочие из изображения не считаются автоматически доступными без проверки реализации. |

<a id="runtime-catalog"></a>

## Как получить полный фактический каталог

Для точного перечня нужно объединить успешные экспозиции **всех активных targets**, сохранив `# HELP`, `# TYPE`, имена семейств и labels. Один Node exporter не охватывает оборудование всех узлов. Для Blackbox нужны `/probe` для используемых модулей/targets, для native RabbitMQ — именно настроенный endpoint и режим детализации.

Ниже только примеры чтения; при подготовке документа команды к стенду не запускались. Подставить фактический URL, CA и учётную запись. `--user admin` запросит пароль интерактивно.

```bash
curl --fail --silent --show-error --user admin \
  --cacert /path/to/internal-ca.pem \
  'https://prometheus.example.org:9091/api/v1/targets?state=active' \
  -o prometheus-targets.json

curl --fail --silent --show-error --user admin \
  --cacert /path/to/internal-ca.pem \
  'https://prometheus.example.org:9091/api/v1/targets/metadata' \
  -o prometheus-target-metadata.json

curl --fail --silent --show-error --user admin \
  --cacert /path/to/internal-ca.pem \
  'https://prometheus.example.org:9091/api/v1/metadata' \
  -o prometheus-metadata.json
```

`/targets/metadata` — вспомогательный API с метаданными по target; его полнота зависит от успешного сбора и версии Prometheus. `/metadata` агрегирует метаданные по имени, поэтому одинаковое имя у разных реализаций может иметь несколько TYPE/HELP. Эти методы не заменяют перечень реально наблюдавшихся label names и значений: их сверяют с `/metrics`/`/probe` и при необходимости с `/api/v1/series` в ограниченном интервале. Recording rules и автоматически создаваемые scrape-метрики нужно учитывать отдельно — у них может не быть exporter HELP/TYPE.

`/api/v1/label/__name__/values` полезен для инвентаризации имён, но может включать исторические ряды: наличие имени не доказывает текущий сбор. Проверить `health`, `lastError`, время последнего scrape и свежесть значений. Для Ironic дополнительно сравнить время последнего сенсорного payload, поскольку доступный exporter может отдавать старые данные.

Документация: [HTTP API Prometheus](https://prometheus.io/docs/prometheus/latest/querying/api/), [формат экспозиции](https://prometheus.io/docs/instrumenting/exposition_formats/).

<a id="sources"></a>

## Источники и контрольные суммы

### Локальные источники

- PVS scrape jobs — `ansible/alerts/prometheus/templates/prometheus.yml.j2`

- Роль Prometheus — `ansible/roles/prometheus/defaults/main.yml`

- PVS alerting/recording rules — `ansible/alerts/prometheus/rules`

- Node dashboard — `ansible/alerts/grafana/dashboards/node-exporter.json`

- Sber dashboard — `ansible/alerts/grafana/dashboards/sber-dashboard.json`

- Watcher recording rules — `ansible/roles/prometheus/templates/watcher.rules.j2`

- Fluentd monitor — `ansible/roles/common/templates/conf/input/08-prometheus.conf.j2`

- Native HAProxy endpoint — `ansible/roles/loadbalancer/templates/haproxy/haproxy_main.cfg.j2`

- Native ProxySQL listener — `ansible/roles/loadbalancer/templates/proxysql/proxysql.yaml.j2`

Пути выше указаны относительно корня Kolla-архива. ZIP и распакованные исходники не публикуются вместе с Markdown; monitoring rules/dashboards сверены непосредственно с обоими ZIP. Исходные архивы и существующие руководства не изменены.

### Первичные источники схем

- [Kolla: версия и URL каждого exporter](https://github.com/openstack/kolla/blob/d14cef9bbafa0db561abfb0c0299d1d6bbbf8f0c/kolla/common/sources.py)

- [Node 1.8.2: collectors](https://github.com/prometheus/node_exporter/tree/v1.8.2/collector)

- [OpenStack 1.7.0: сервисные дескрипторы и TYPE](https://github.com/openstack-exporter/openstack-exporter/tree/v1.7.0/exporters)

- [Libvirt 2.2.0: полный код метрик](https://github.com/inovex/prometheus-libvirt-exporter/blob/v2.2.0/pkg/exporter/prometheus-libvirt-exporter.go)

- [MySQL 0.16.0: collectors](https://github.com/prometheus/mysqld_exporter/tree/v0.16.0/collector)

- [Memcached 0.15.0](https://github.com/prometheus/memcached_exporter/tree/v0.15.0)

- [Blackbox 0.25.0: probers](https://github.com/prometheus/blackbox_exporter/tree/v0.25.0/prober)

- [cAdvisor 0.49.2: таблица всех категорий](https://github.com/google/cadvisor/blob/v0.49.2/docs/storage/prometheus.md)

- [Elasticsearch exporter 1.8.0](https://github.com/prometheus-community/elasticsearch_exporter/blob/v1.8.0/README.md)

- [Ironic exporter stable/2025.1: IPMI и Redfish](https://github.com/openstack/ironic-prometheus-exporter/tree/stable/2025.1/ironic_prometheus_exporter/parsers)

- [RabbitMQ native Prometheus plugin и режимы выдачи](https://www.rabbitmq.com/docs/prometheus)

- [Native HAProxy: справочник метрик](https://www.haproxy.com/documentation/haproxy-configuration-tutorials/alerts-and-monitoring/prometheus/)

- [etcd 3.5: метрики](https://etcd.io/docs/v3.5/metrics/)

- [Fluentd prometheus_output_monitor](https://github.com/fluent/fluent-plugin-prometheus#prometheus_output_monitor-input-plugin)

- [Ceph Squid: определения метрик mgr](https://github.com/ceph/ceph/blob/squid/src/pybind/mgr/prometheus/module.py)

- [ProxySQL: native endpoint](https://proxysql.com/documentation/prometheus-exporter/)

Внешние native-документы применены для объяснения справочных семейств, а не для утверждения версии пакетов на стенде. Исходные HELP в приложениях относятся к указанным upstream-проектам; проекты распространяются со своими лицензиями, включая Apache-2.0.

### SHA-256 исследованных архивов

| Архив | SHA-256 |
|---|---|
| kolla-ansible-enroll-ironic-patch-3.zip | `12403a06d810cbdfe560bc104472f6fe3b1f38b572f9c9e59212329ab6a37db3` |
| kolla-ansible-pvs_1.0.0_21.09zip.zip | `e68e98cb5ce6d2384ebf90c4ff1e6a9b779efe986ae11a83bc8cb1b556bfe004` |
| masakari-pvs_1.0.0_21.09.zip | `cf40ec62cdde2795499e7e46e6f5599fe9beb90b07c16c8a988f28d436469156` |
| watcher-pvs_1.0.0_21.09.zip | `67722deaa94b4e606620519c34a3db84f3253c492e7238f78bf0045a65c2ac0b` |

### Проверка охвата документа

| Проверка | Результат |
|---|---|
| Зависимости архивных PromQL/rules/dashboard queries | 407 уникальных имён и шаблонов; все отражены в основных таблицах, включая отсутствующие определения и ошибочное имя |
| Recording rules | 26 уникальных имён; вычисляемые показатели отделены от exporters |
| Основные таблицы | 660 строк с русскими пояснениями |
| Расширенные каталоги | 997 дополнительных имён с исходным HELP/описанием; имена основных таблиц повторно не включены |
| Live-проверка | Не выполнялась; полнота реальной экспозиции/TSDB не заявляется |
