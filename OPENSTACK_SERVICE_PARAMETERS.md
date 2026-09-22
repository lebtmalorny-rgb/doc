# Важные параметры Mistral, Masakari, Watcher, Consul и Ironic

Дата сверки: 22.09.2026. Документ предназначен для администратора данного форка Kolla-Ansible: где найти параметр, какое значение задано исходниками, куда записать переопределение и как проверить результат.

## Краткий вывод

Для настройки окружения используйте `/etc/kolla/globals.yml` или отдельные файлы `/etc/kolla/globals.d/*.yml`. В исходниках defaults сервисов обычно находятся в `ansible/roles/<service>/defaults/main.yml`, а общие переключатели и часть параметров этого форка — в `ansible/group_vars/all.yml`. Переносить все настройки роли в `all.yml` не требуется. Если default подходит, повторять его в `globals.yml` необязательно.

У параметров есть два разных механизма переопределения: Ansible-переменные влияют на шаблон, а native INI options задаются через поддерживаемые ролью файлы в `node_custom_config`. При merge такой INI override может перекрыть значение, уже сформированное из `globals.yml`. Для Consul нужно отдельно учитывать HCL-шаблон: общий INI-механизм на него автоматически не распространяется.

Все значения ниже — **подтверждённые defaults/выражения и связи в исходниках**, а не считанные настройки действующего облака. Фактические `globals.yml`, inventory, config overrides, образы и загруженные конфиги вашего стенда здесь не проверялись. Некоторые переменные в форке объявлены, но не связаны с кодом или шаблоном; они явно отмечены.

Навигация: [слои настройки](#общие-правила-где-определять-и-где-менять) · [Mistral](#mistral) · [Masakari](#masakari) · [Watcher](#watcher) · [Consul](#consul) · [Ironic](#ironic) · [проверка значений](#как-проверить-какое-значение-действительно-используется).

## Источники и обозначения

| Метка | Исходный материал |
|---|---|
| `K:` | `kolla-ansible-enroll-ironic-patch-3.zip`, ZIP commit `5db3c8eed90d69a85e3761ff7f55cb72d7fde94f`, **с применённым Kolla-патчем VMClone v1**. Номера строк относятся к этому состоянию. |
| `M:` | `mistral-integration-powerops-mistral-2025.1.zip`, ZIP commit `99514c4e11fa2dfdc00dd8de5aa7f5ca07300514`, **с применённым Mistral-патчем VMClone v1**. |
| `A:` | `masakari-pvs_1.0.0_21.09.zip`, ZIP commit `702480386d63c935a6f1b143fbd65f54dba63f52`. |
| `W:` | `watcher-pvs_1.0.0_21.09.zip`, ZIP commit `96eeba4c5b8ce30f29fd7d6461bdac28fdfdfa4d`. |

Запись `K:ansible/group_vars/all.yml:1050` означает файл и строку относительно корня соответствующего дерева. Исходные архивы в репозиторий документации не включены. Распакованные Masakari и Watcher побайтно сверены с архивами; Kolla/Mistral после VMClone сверены при replay патчей. Перечень параметров выборочный: включение функций, интервалы, таймауты, ограничения, recovery, источники метрик и управление питанием.

VMClone — дополнение, которого нет в исходных ZIP до применения патчей. Комплект и подробный порядок эксплуатации: [mistral_live_cloning](https://github.com/lebtmalorny-rgb/mistral_live_cloning/tree/02e07a20bc6fdd2102e91fe5d7fe5c6331afaabe), [руководство администратора](https://github.com/lebtmalorny-rgb/mistral_live_cloning/blob/02e07a20bc6fdd2102e91fe5d7fe5c6331afaabe/docs/ADMIN_GUIDE.md).

SHA256 исходных ZIP:

```text
12403a06d810cbdfe560bc104472f6fe3b1f38b572f9c9e59212329ab6a37db3  kolla-ansible-enroll-ironic-patch-3.zip
71f28efd2c97bbd82f1b5ecd2fdbaa3dd6fb4de69cb2c36469fa2b86308a0a55  mistral-integration-powerops-mistral-2025.1.zip
cf40ec62cdde2795499e7e46e6f5599fe9beb90b07c16c8a988f28d436469156  masakari-pvs_1.0.0_21.09.zip
67722deaa94b4e606620519c34a3db84f3253c492e7238f78bf0045a65c2ac0b  watcher-pvs_1.0.0_21.09.zip
```

## Общие правила: где определять и где менять

| Уровень | Назначение и приоритет |
|---|---|
| `ansible/roles/<role>/defaults/main.yml` | Низкоприоритетные defaults роли. Подходящее место для новых параметров, относящихся только к этой роли. |
| `ansible/group_vars/all.yml` | Общие переменные исходного Kolla и межсервисные переключатели; перекрывают role defaults. В этом форке сюда также помещены PowerOps и часть Consul/Masakari настроек. |
| Inventory `group_vars` / `host_vars` | Групповые/узловые настройки, например интерфейсы сетей и BMC-атрибуты конкретного узла. Не заменяют все правила более приоритетных extra vars. |
| `/etc/kolla/globals.yml` | Настройки окружения. CLI передаёт файл как Ansible `-e @...`; он перекрывает defaults и inventory vars. |
| `/etc/kolla/globals.d/90-service.yml` | Та же область настроек окружения. CLI загружает читаемые `.yml`, `.yaml`, `.json` в алфавитном порядке после `globals.yml`. При повторе переменной побеждает более позднее определение. |
| `node_custom_config` | Отдельный этап объединения native конфигов: INI options, для которых нет Ansible-переменной, либо осознанные overrides. Поддерживаемые пути определяются задачами каждой роли. |
| Конфиг внутри контейнера | Результат доставки и merge. Ручная правка не является постоянным источником настройки и может быть перезаписана Kolla. Отсутствующий в INI ключ может использовать default Python-пакета. |

Порядок загрузки файлов подтверждён `K:kolla_ansible/ansible.py:213` и `K:kolla_ansible/ansible.py:250`; приоритет role defaults и group vars — [официальной документацией Ansible](https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks_variables.html#understanding-variable-precedence). Дополнительные `-e` и служебные переменные CLI могут иметь более поздний приоритет. Не размещайте одни и те же настройки сразу во всех слоях.

Три похожих пути имеют разный смысл (`K:ansible/group_vars/all.yml:7`):

- `node_config` — каталог конфигурации на deploy host, обычно `/etc/kolla`; при `--configdir` используется выбранный каталог.
- `node_custom_config` — обычно `{{ node_config }}/config`, например `/etc/kolla/config` на deploy host.
- `node_config_directory` — каталог сгенерированных файлов на целевом узле, по умолчанию `/etc/kolla`; это не каталог пользовательских overrides.

`merge_configs` читает sources по порядку и заменяет совпадающие section/key более поздним значением (`K:ansible/action_plugins/merge_configs.py:99`, `K:ansible/action_plugins/merge_configs.py:181`). Поэтому надо проверять одновременно Ansible var и все native overrides. Изменения вступают в действие после соответствующего штатного reconfigure/deploy и обработки контейнеров; сохранение YAML само по себе не меняет работающий процесс.

### Общие переключатели и образы

| Параметр | Default данного форка | Где определён / важное следствие |
|---|---|---|
| `enable_mistral` | `yes` | `K:ansible/group_vars/all.yml:1180`. Включение роли не включает VMClone/PowerOps автоматически. |
| `enable_masakari` | `yes` | `K:ansible/group_vars/all.yml:1176`. Monitors имеют дополнительные переключатели. |
| `enable_watcher` | `yes` | `K:ansible/group_vars/all.yml:1262`. Возможность запускать audit зависит также от метрик и стратегии. |
| `enable_consul` | `yes` | `K:ansible/group_vars/all.yml:953`. Конкретные сети и процессы определяются отдельными настройками. |
| `enable_ironic` | `yes` | `K:ansible/group_vars/all.yml:1156`. Наличие Ironic не означает, что BMC nodes уже зарегистрированы. |
| `enable_etcd` | `no` | `K:ansible/group_vars/all.yml:1127`. PowerOps/VMClone требуют отдельно подготовленного общего etcd. |
| `openstack_service_workers` | `min(processor_vcpus, 5)` | `K:ansible/group_vars/all.yml:875`. Наследуется рядом API worker settings; не является универсальным лимитом операций recovery. |
| `default_container_healthcheck_interval / timeout / retries / start_period` | `60` секунд при одном inventory host, иначе `30`; `30 / 3 / 5` | `K:ansible/group_vars/all.yml:271`. Container healthcheck отличается от detection/recovery и application polling. |

Образы определяются `*_image`, `*_tag`, `*_image_full` в defaults соответствующих ролей. При переопределении `image_full` изменение только `image`/`tag` может не изменить итоговую ссылку. Наличие переменной/секции ещё не означает, что установленный образ умеет её читать. Для дополнительных функций должны совпадать версии Kolla-шаблонов и Python-кода сервисов.

## Mistral

Mistral выполняет workflow и actions. В этой поставке PowerOps управляет плановыми операциями compute-host, а VMClone создаёт копию ВМ через OpenStack API. Их таймауты, авторизация и журналы имеют разные настройки.

### VMClone: новые defaults роли

Все Ansible-переменные этой таблицы задаются через `globals.yml`/`globals.d`. Шаблон записывает их в `[vmclone]` без префикса `vmclone_` для API/engine/executor (`K:ansible/roles/mistral/templates/mistral.conf.j2:130`).

| Параметр | Default | Смысл, единица / источник |
|---|---|---|
| `enable_vmclone` | `no` | Явное включение actions; `K:ansible/group_vars/all.yml:1050`. Native `[vmclone] enabled` тоже false по умолчанию. |
| `vmclone_request_timeout` | `30` | Таймаут отдельного HTTP-запроса, секунды. `K:ansible/roles/mistral/defaults/main.yml:220`; `M:mistral/actions/vmclone/options.py:27`. |
| `vmclone_wait_timeout` | `900` | Лимит одного ожидания ресурса, секунды. Это не общий лимит workflow: ожидания нескольких ресурсов могут суммироваться. `K:ansible/roles/mistral/defaults/main.yml:221`; `M:mistral/actions/vmclone/service.py:294`. |
| `vmclone_poll_interval` | `5` | Пауза между проверками ресурса, секунды; не интервал запуска новых clone operations. `K:ansible/roles/mistral/defaults/main.yml:222`. |
| `vmclone_max_disks` | `16` | Максимальное число всех Cinder-дисков источника, включая root; допустимый диапазон `1…64`. Диски сверх лимита не пропускаются — план отклоняется. `K:ansible/roles/mistral/defaults/main.yml:223`; `M:mistral/actions/vmclone/options.py:30`. |
| `vmclone_allowed_roles` | `[admin, member]` | Allowlist ролей доверенного RPC-контекста; дополнительно действуют права API и user/project scope журнала. `K:ansible/roles/mistral/defaults/main.yml:224`; `M:mistral/actions/vmclone/actions.py:32`. |
| `vmclone_auth_url / region_name / interface / cafile` | Keystone internal v3 / `openstack_region_name` / `internal` / `openstack_cacert` | Клиентские подключения к OpenStack, не параметры гостя. `K:ansible/roles/mistral/defaults/main.yml:212`. |
| `vmclone_etcd_url / vmclone_etcd_cafile` | Внутренний HTTP(S) VIP/FQDN + `etcd_client_port`; `openstack_cacert` | Общий постоянный журнал всех executor. URL здесь обычный HTTP(S), а не PowerOps `etcd3+...`. `K:ansible/roles/mistral/defaults/main.yml:218`. |

При подходящих defaults и уже подготовленных образах/зависимостях достаточно файла окружения:

```yaml
# /etc/kolla/globals.d/90-vmclone.yml
enable_vmclone: "yes"
```

Например, для изменения только ожидания и allowed roles:

```yaml
enable_vmclone: "yes"
vmclone_wait_timeout: 1800
vmclone_allowed_roles: [admin]
```

Остальные значения наследуются из роли. Перенос этих пяти defaults в `ansible/group_vars/all.yml` не нужен. `operation_id`, `source_root_vol_id`, `allow_inconsistent_disks` и `confirm` относятся к входу конкретного workflow/action и задаются при CLI-запуске, а не через глобальный YAML.

### PowerOps: общие defaults в group_vars

В отличие от VMClone, перечисленные PowerOps defaults уже расположены в `ansible/group_vars/all.yml`. Это существующая структура данного форка, не указание переносить туда все параметры остальных сервисов. Для окружения переопределяйте их через `globals.yml`/`globals.d`. Native mapping `[powerops]` показан в `K:ansible/roles/mistral/templates/mistral.conf.j2:112`.

| Параметр | Default | Смысл / источник |
|---|---|---|
| `enable_powerops` | `no` | Включает плановые host power actions; не включает VMClone. `K:ansible/group_vars/all.yml:1024`. |
| `powerops_coordination_url` | `etcd3+<internal_protocol>://<internal_fqdn>:<etcd_client_port>?api_version=v3` с CA при настройке | Координация host locks; требует доступного общего backend. `K:ansible/group_vars/all.yml:1025`. Полное выражение надо брать из файла. |
| `powerops_host_lock_timeout` | `30` с | Ожидание захвата host lock, не срок всей операции. `K:ansible/group_vars/all.yml:1033`; `M:mistral/config.py:648`. |
| `powerops_power_timeout` | `180` с | Ожидание физического перехода питания. `K:ansible/group_vars/all.yml:1036`; `M:mistral/config.py:654`. |
| `powerops_poll_interval / stable_observations` | `5` с / `3` наблюдения | Интервал и число последовательных наблюдений устойчивого состояния. `K:ansible/group_vars/all.yml:1037`; `M:mistral/config.py:659`. |
| `powerops_graceful_shutdown_timeout` | `300` с | Ожидание graceful shutdown хоста; разрешение hard-off задаётся отдельно. `K:ansible/group_vars/all.yml:1039`. |
| `powerops_vm_action_timeout` | `600` с | Ожидание одной операции над instance. `K:ansible/group_vars/all.yml:1040`; `M:mistral/config.py:678`. |
| `powerops_service_timeout` | `300` с | Ожидание нужного состояния compute service. `K:ansible/group_vars/all.yml:1041`. |
| `powerops_instance_interval` | `5` с | Пауза между последовательными instance operations PowerOps. Это не Masakari evacuation pacing. `K:ansible/group_vars/all.yml:1042`; `M:mistral/actions/powerops/clients.py:466`. |
| `powerops_allowed_project_names / allowed_user_names` | Имена из `openstack_auth.project_name / username` | Для не-admin требуются роль `powerops_operator` и обе allowlists. Admin проходит отдельной веткой; hard-off требует admin. Native defaults без Kolla — пустые списки. `K:ansible/group_vars/all.yml:1027`; `M:mistral/services/powerops.py:25`. |
| `powerops_reconcile_workbook / powerops_validate_registration` | `yes / yes` | Поведение deployment роли при регистрации PowerOps workbook/проверке каталога; не runtime интервалы и не регистрация VMClone. `K:ansible/group_vars/all.yml:1043`; `K:ansible/roles/mistral/tasks/powerops.yml:64`. |

`instance_policy`, `allow_hard_off`, `stopped_instance_ids` и `stale_domains_checked` — входные параметры PowerOps actions/workflows. Значение таймаута в globals не разрешает принудительное выключение и не заменяет эксплуатационные проверки.

### Нативные настройки Mistral без отдельной Kolla-переменной

Их задают в поддерживаемом INI override, обычно `/etc/kolla/config/mistral.conf`. Не придумывайте Ansible-переменную по имени native option: без использования в шаблоне она не попадёт в конфиг.

| Секция и ключ | Native default | Назначение / источник |
|---|---|---|
| `[legacy_action_provider] load_action_plugins` | `true` | Загрузка Python entry points, включая custom actions. `M:mistral/config.py:91`. |
| `[legacy_action_provider] allowlist / denylist` | Пустые списки | Ограничение загрузки actions, отдельное от RBAC пользователя; allowlist имеет приоритет. `M:mistral/config.py:118`. |
| `[engine] execution_field_size_limit_kb` | `1024` КБ | Ограничение больших текстовых полей execution; `-1` снимает лимит. `M:mistral/config.py:265`. |
| `[engine] execution_integrity_check_delay` | `20` с | Задержка до проверки RUNNING task с завершившимися дочерними actions/workflows; не таймаут облачной операции. `M:mistral/config.py:271`. |
| `[action_heartbeat] check_interval / max_missed_heartbeats` | `20` с / `15` | Период проверки и допустимое число пропусков heartbeat. Ноль отключает соответствующий механизм. Не заменяют `vmclone_wait_timeout`. `M:mistral/config.py:547`. |
| `[action_heartbeat] first_heartbeat_timeout` | `3600` с | Ожидание первого heartbeat, в том числе при нехватке executor. `M:mistral/config.py:576`. |
| `[execution_expiration_policy] evaluation_interval / older_than` | Не заданы | Период оценки и возраст завершённых execution **в минутах**. Это удаление истории Mistral, не cloud cleanup и не очистка журнала VMClone. `M:mistral/config.py:503`. |
| `[execution_expiration_policy] max_finished_executions` | `0` | Ограничение количества сохранённых завершённых workflow; `0` не применяет этот лимит. `M:mistral/config.py:520`. |
| `[coordination] heartbeat_interval` | `5.0` с, deprecated | В этом Mistral явно помечен как неиспользуемый и не влияющий на поведение. Не настраивайте им PowerOps polling. `M:mistral/config.py:731`. |

Пример native override с явной секцией:

```ini
# /etc/kolla/config/mistral.conf
[legacy_action_provider]
load_action_plugins = true
```

Kolla также задаёт `mistral_api_workers = openstack_service_workers` (`K:ansible/roles/mistral/defaults/main.yml:207`) и `[api] api_workers` шаблоном. Это число API workers, а не количество параллельных клонов.

### Путь конфигурации Mistral

Порядок merge: шаблон → `{{ node_custom_config }}/global.conf` → `mistral.conf` → `mistral/<service>.conf` → `mistral/<inventory_hostname>/mistral.conf`. Последний совпадающий section/key имеет приоритет. `<service>` — например `mistral-executor`; точные пути: `K:ansible/roles/mistral/tasks/config.yml:43`.

Результат на узле: `/etc/kolla/mistral-executor/mistral.conf` при стандартном `node_config_directory`; внутри контейнера `mistral_executor`: `/etc/mistral/mistral.conf`. Аналогично для API/engine/event-engine, но `[vmclone]` и `[powerops]` шаблон формирует только для API/engine/executor. Доставка подтверждена `K:ansible/roles/mistral/templates/mistral-executor.json.j2:2`.

## Masakari

Для Masakari подтверждены и Kolla-шаблоны (`K`), и регистрация/использование native-параметров в исходниках `masakari-pvs_1.0.0` (`A`). Значение из Python ниже — default при отсутствии настройки в итоговом конфиге, а не показание работающего контейнера. Исходников `masakari-monitors` в исследованном комплекте нет: для hostmonitor подтверждены выдаваемые Kolla ключи и матрица, но не внутренний алгоритм драйвера или его дополнительные defaults.

Переопределения в таблице: **G** — Ansible-переменная в `/etc/kolla/globals.yml` или `globals.d/*.yml`; **E** — native INI в `/etc/kolla/config/masakari/masakari-engine.conf`; **H** — native INI в `/etc/kolla/config/masakari/masakari-hostmonitor.conf`. Пути приведены для стандартных `node_config` и `node_custom_config`. Для общей настройки API и Engine предусмотрен `/etc/kolla/config/masakari.conf`.

| Параметр и слой | Значение в исследованном исходнике | Что регулирует | Где определён и куда попадает; переопределение |
|---|---|---|---|
| `enable_masakari`; `enable_masakari_instancemonitor`, `enable_masakari_hostmonitor`, `enable_masakari_processmonitor` — Ansible | `"yes"`; каждый monitor наследует `enable_masakari \| bool` | Включение компонента и отдельных мониторов; размещение дополнительно определяется inventory | `K:ansible/group_vars/all.yml:1176`; `K:ansible/roles/masakari/defaults/main.yml:35`. Управляют `masakari_services.*.enabled`, не INI-ключом. **G**. |
| `masakari_api_workers` — Ansible | `{{ openstack_service_workers }}`, где `openstack_service_workers = min(processor_vcpus, 5)` | Число процессов Apache WSGI для API, не число recovery-потоков | `K:ansible/roles/masakari/defaults/main.yml:165`; `K:ansible/group_vars/all.yml:875` → `WSGIDaemonProcess ... processes=... threads=1`, `K:ansible/roles/masakari/templates/wsgi-masakari.conf.j2:34`. **G**. |
| `masakari_logging_debug` — Ansible | `{{ openstack_logging_debug }}`, общий default `"False"` | Отладочное логирование API, Engine и monitors | `K:ansible/roles/masakari/defaults/main.yml:159`; `K:ansible/group_vars/all.yml:862` → `[DEFAULT] debug`, `K:ansible/roles/masakari/templates/masakari.conf.j2:2`, `K:ansible/roles/masakari/templates/masakari-monitors.conf.j2:2`. **G**. |
| `masakari_hostmonitor_driver` — Ansible | **`"consul"` в group_vars**; более низкий role default — `"default"` | Выбор ветки шаблона: Consul или Pacemaker. Precheck допускает только `default`/`consul` | `K:ansible/group_vars/all.yml:1100`; `K:ansible/roles/masakari/defaults/main.yml:225`; `K:ansible/roles/masakari/tasks/precheck.yml:81` → `[host] monitoring_driver = consul`, `K:ansible/roles/masakari/templates/masakari-monitors.conf.j2:43`. **G**. |
| `masakari_hostmonitor_monitoring_interval`, `masakari_hostmonitor_monitoring_samples` — Ansible | `60`, `1` | Интервал мониторинга и число samples, передаваемые hostmonitor. Точный момент recovery по произведению этих чисел без кода monitors не устанавливается | `K:ansible/group_vars/all.yml:1101` → `[host] monitoring_interval`, `monitoring_samples`, `K:ansible/roles/masakari/templates/masakari-monitors.conf.j2:45`. **G**; при прямом INI — **H**. Единицы interval в Kolla не документированы, Python-регистрация monitors отсутствует. |
| `masakari_hostmonitor_consul_use_loopback` — Ansible | `true` | Выбирает loopback либо адрес соответствующей сети Consul для каждого `agent_*` | `K:ansible/roles/masakari/defaults/main.yml:231` → `[consul] agent_manage`, `agent_tenant`, `agent_storage`: `127.0.0.1:<consul_http_port>` либо `kolla_address(...):<consul_http_port>`, `K:ansible/roles/masakari/templates/masakari-monitors.conf.j2:50`. **G**. См. ограничение нескольких агентов в разделе Consul. |
| `masakari_consul_matrix_policy` — Ansible | `"all_down"` | `all_down`: recovery при падении всех участвующих сетей; `majority_down`: строго больше половины; `threshold`: не меньше заданного числа; `custom`: точное совпадение указанного состояния | `K:ansible/group_vars/all.yml:1109`; алгоритм `K:kolla_ansible/masakari_consul.py:198` → `matrix.yaml` (`sequence`, `matrix[].health`, `matrix[].action`), `K:ansible/roles/masakari/templates/matrix.yaml.j2:1`. **G**. |
| `masakari_consul_down_threshold` — Ansible | `null` | Число сетей в состоянии `down`, достаточное для recovery при `policy=threshold`; требуется целое от `1` до количества участвующих сетей | `K:ansible/group_vars/all.yml:1111`; проверка `K:kolla_ansible/masakari_consul.py:167` → та же `matrix.yaml`. **G**. |
| `masakari_consul_custom_recovery_states` — Ansible | `[]` | Список точных комбинаций `up`/`down` для `policy=custom`. Ключи каждой записи должны точно совпадать с текущим `sequence`; пустой список не создаёт recovery-состояний | `K:ansible/group_vars/all.yml:1123`; `K:kolla_ansible/masakari_consul.py:112`, `:207` → та же `matrix.yaml`. **G**. |
| `[host_failure] evacuate_all_instances`, `ha_enabled_instance_metadata_key` — native | `True`, `HA_Enabled` | `True`: эвакуировать все ВМ, сначала отмеченные HA; `False`: только ВМ с выбранным metadata-ключом со значением `True` | `A:masakari/conf/engine_driver.py:48`, `:63`. Kolla не выводит эти ключи; используются native defaults или **E**. |
| `[host_failure] ignore_instances_in_error_state` — native | `False` | Исключать ли из эвакуации ВМ в ERROR. Default включает их в кандидаты | `A:masakari/conf/engine_driver.py:72`. Native default или **E**. |
| `[host_failure] add_reserved_host_to_aggregate` — native | `False` | Добавлять ли резервный compute в aggregate отказавшего хоста при восстановлении на reserved host | `A:masakari/conf/engine_driver.py:81`; использование `A:masakari/engine/drivers/taskflow/host_failure.py:392`. Native default или **E**. |
| `[instance_failure] process_all_instances`, `ha_enabled_instance_metadata_key` — native | `False`, `HA_Enabled` | Для события отказа отдельной ВМ: default разрешает восстановление только ВМ с выбранной HA-меткой. Это отдельная политика от `[host_failure]` | `A:masakari/conf/engine_driver.py:95`, `:109`. Native defaults или **E**. |
| `[DEFAULT] host_failure_recovery_threads` — native | `3`, минимум `1` | Размер GreenPool эвакуации/подтверждения **в ветке без PowerOps**. При `[powerops] enabled=True` код использует последовательный цикл с общей блокировкой | `A:masakari/conf/engine.py:107`; ветвление `A:masakari/engine/drivers/taskflow/host_failure.py:432`. Native default или **E**. |
| `[DEFAULT] wait_period_after_service_update` — native | `180` с | Максимальное ожидание подтверждения изменения состояния Nova service | `A:masakari/conf/engine.py:71`. Native default или **E**. |
| `[DEFAULT] wait_period_after_evacuation`, `verify_interval` — native | `90` с, `1` с | Ожидание подтверждения эвакуации одной ВМ и шаг повторной проверки; увеличение timeout не увеличивает параллелизм | `A:masakari/conf/engine.py:75`; применение `A:masakari/engine/drivers/taskflow/host_failure.py:264`. Native defaults или **E**. |
| `[DEFAULT] wait_period_after_power_off`, `wait_period_after_power_on` — native | `180` с, `60` с | Ожидание выключения/включения **ВМ** в recovery-flow. Это не таймаут физического fencing хоста | `A:masakari/conf/engine.py:81`; пример ожидания остановки ВМ — `A:masakari/engine/drivers/taskflow/host_failure.py:184`. Native defaults или **E**. |
| `[DEFAULT] duplicate_notification_detection_interval` — native | `180` с, минимум `0` | Окно подавления одинаковых уведомлений, когда предыдущее находится в `new` или `running` | `A:masakari/conf/engine.py:60`. Native default или **E**; общая настройка API/Engine — `/etc/kolla/config/masakari.conf`. |
| `[DEFAULT] process_unfinished_notifications_interval`, `retry_notification_new_status_interval` — native | `120` с, `60` с | Период обработки незавершённых уведомлений и минимальный возраст `new` для повторной обработки. Периодическая задача также обрабатывает `error`; повторный `error` переводит в `failed` | `A:masakari/conf/engine.py:87`; фактическое поведение `A:masakari/engine/manager.py:353`. Native defaults или **E**. Это не счётчик бесконечных повторов. |
| `[DEFAULT] check_expired_notifications_interval`, `notifications_expired_interval` — native | `600` с, `86400` с | Период проверки и допустимый возраст уведомления. Код проверяет `running`, `error`, `new` и переводит просроченное в `failed` | `A:masakari/conf/engine.py:100`; `A:masakari/engine/manager.py:391`. Native defaults или **E**. |
| `enable_powerops` — Ansible; `[powerops] enabled`; `[taskflow_driver_recovery_flows] host_auto_failure_recovery_tasks`, `host_rh_failure_recovery_tasks` | `"no"`; native `False`. При включении Kolla задаёт `enabled=true` и добавляет `ironic_fence` после `disable_compute_service_task` в `pre` обеих host-flow | Включает fencing через Ironic до эвакуации и PowerOps coordination. Одна настройка `[powerops] enabled` без согласованного состава flow не заменяет Kolla-включение | `K:ansible/group_vars/all.yml:1024`; `K:ansible/roles/masakari/templates/masakari.conf.j2:88`; native defaults `A:masakari/conf/powerops.py:19`, `A:masakari/conf/engine_driver.py:126`. **G**. Precheck требует Ironic, Masakari, Mistral, etcd: `K:ansible/roles/masakari/tasks/precheck.yml:2`. |
| `powerops_coordination_url`; `masakari_coordination_backend` — Ansible → `[coordination] backend_url` | PowerOps: `etcd3+{{ internal_protocol }}://{{ kolla_internal_fqdn }}:{{ etcd_client_port }}?api_version=v3` с `&ca_cert=...` при наличии CA. Без PowerOps: backend выбирается `redis` при `enable_redis`, иначе `etcd` при `enable_etcd`, иначе пустая строка | Общая распределённая координация. PowerOps выводит URL для API **и** Engine; обычная ветка шаблона задаёт coordination только API | `K:ansible/group_vars/all.yml:1025`, `:641`; `K:ansible/roles/masakari/templates/masakari.conf.j2:88`, `:110`. **G**. Native default URL — `None`: `A:masakari/conf/coordination.py:19`. |
| `powerops_host_lock_timeout`, `powerops_evacuation_lock_timeout` — Ansible → `[powerops] host_lock_timeout`, `evacuation_lock_timeout` | `30` с, `3600` с; native `30.0`, `3600.0` | Время ожидания **получения** блокировки хоста и общей блокировки эвакуации. Это не TTL блокировки и не deadline всего recovery | `K:ansible/group_vars/all.yml:1033` → `K:ansible/roles/masakari/templates/masakari.conf.j2:97`; `A:masakari/conf/powerops.py:20`; `acquire(blocking=timeout)` — `A:masakari/powerops/coordination.py:168`. **G**. |
| `powerops_evacuation_interval` — Ansible → `[powerops] evacuation_interval` | `5` с; native минимум `0` | Пауза после подтверждённой успешной эвакуации внутри общей блокировки. PowerOps держит эту блокировку на эвакуации, подтверждении и паузе | `K:ansible/group_vars/all.yml:1035` → `K:ansible/roles/masakari/templates/masakari.conf.j2:99`; `A:masakari/conf/powerops.py:22`; `A:masakari/engine/drivers/taskflow/host_failure.py:432`. **G**. |
| `powerops_power_timeout`, `powerops_poll_interval`, `powerops_stable_observations`; `[powerops] nova_down_timeout` | Ansible `180` с, `5` с, `3` наблюдения → native `power_timeout`, `poll_interval`, `stable_off_observations`. `nova_down_timeout` — только native default `180` с | Бюджет Ironic fencing; интервал проверок; число последовательных подтверждений `power off`; затем отдельный бюджет ожидания Nova `disabled/down`. `stable_off_observations` минимум `2`; `nova_down_timeout` минимум `1` | `K:ansible/group_vars/all.yml:1036` → `K:ansible/roles/masakari/templates/masakari.conf.j2:100`; `A:masakari/conf/powerops.py:23`; алгоритм `A:masakari/powerops/ironic.py:124`, ожидание Nova `A:masakari/engine/drivers/taskflow/powerops.py:69`. Первые три — **G**, `nova_down_timeout` — **E**; Ansible-переменной для последнего в шаблоне нет. |

Последовательность merge для API/Engine: template → `config/global.conf` → `config/masakari.conf` → `config/masakari/<service_name>.conf` → `config/masakari/<inventory_hostname>/masakari.conf` (`K:ansible/roles/masakari/tasks/config.yml:115`). Для monitors: template → `config/global.conf` → `config/masakari/<service_name>.conf` → **`config/masakari/masakari-monitors.conf`** → `config/masakari/<inventory_hostname>/masakari-monitors.conf` (`K:ansible/roles/masakari/tasks/config.yml:134`). Поэтому общий monitors override в этом исходнике имеет приоритет над файлом отдельного monitor. Поздний источник заменяет совпавший ключ: `K:ansible/action_plugins/merge_configs.py:96`, `:181`.

| Файл на узле после генерации | Файл внутри контейнера | Подтверждение |
|---|---|---|
| `/etc/kolla/masakari-engine/masakari.conf` | `/etc/masakari/masakari.conf` | `K:ansible/roles/masakari/templates/masakari-engine.json.j2:2` |
| `/etc/kolla/masakari-hostmonitor/masakari-monitors.conf` | `/etc/masakari-monitors/masakari-monitors.conf` | `K:ansible/roles/masakari/templates/masakari-hostmonitor.json.j2:2` |
| `/etc/kolla/masakari-hostmonitor/matrix.yaml` | `/etc/masakari-monitors/matrix.yaml` | `K:ansible/roles/masakari/tasks/config.yml:154`; `K:ansible/roles/masakari/templates/masakari-hostmonitor.json.j2:15` |

Изменения применяются через Kolla reconfigure/deploy: роль заново формирует конфиги, проверяет контейнеры и выполняет handlers (`K:ansible/roles/masakari/tasks/reconfigure.yml:2`; `K:ansible/roles/masakari/tasks/deploy.yml:4`). Редактирование итогового файла контейнера не является устойчивым override. Матрица генерируется непосредственно из Ansible-переменных, без merge с пользовательским `matrix.yaml`.

Важные границы: `masakari_consul_monitoring_interval=30` и `masakari_consul_monitoring_samples=3` объявлены в `K:ansible/group_vars/all.yml:642` и `K:ansible/roles/masakari/defaults/main.yml:218`, но исследованный шаблон их не читает: он использует `masakari_hostmonitor_monitoring_*`. Значение `masakari_hostmonitor_driver=default` из role defaults также нельзя выдавать за итоговый Kolla default. Recovery method сегмента (`auto`, `reserved_host` и т. п.) — состояние API-объекта сегмента; это не одноимённая универсальная настройка `masakari.conf` и не параметр вызова Mistral.

Две проверки без изменения состояния, выполняемые администратором на соответствующем узле; вывод ограничен указанными несекретными полями:

```bash
# Native-настройки Engine, явно присутствующие в конфиге контейнера.
docker exec masakari_engine python3 -c 'import configparser; c=configparser.ConfigParser(interpolation=None); c.read("/etc/masakari/masakari.conf"); keys={"DEFAULT":["host_failure_recovery_threads","wait_period_after_evacuation","verify_interval"],"powerops":["enabled","host_lock_timeout","evacuation_lock_timeout","evacuation_interval","power_timeout","poll_interval","stable_off_observations","nova_down_timeout"]}; [print("[{}] {}={}".format(s,k,c.get(s,k,fallback="<не задано явно>"))) for s,ks in keys.items() for k in ks]'
# Только локальная матрица решений, без auth-секции monitors.
docker exec masakari_hostmonitor cat /etc/masakari-monitors/matrix.yaml
```

Отсутствие ключа в первом выводе означает, что он не записан явно; применимый default определяется именно версией установленного Masakari. Здесь команды не выполнялись против стенда.

## Watcher

В этом Kolla `enable_watcher: "yes"`, порт API `9322`; это значения `ansible/group_vars/all.yml`, хотя пример `etc/kolla/globals.yml` содержит закомментированное `enable_watcher: "no"` (`K:ansible/group_vars/all.yml:1262`, `K:ansible/group_vars/all.yml:829`, `K:etc/kolla/globals.yml:456`). Администратор меняет Kolla-переменные в `globals.yml`/подключаемом `globals.d`, а native INI-опции — в custom config.

Для таблицы «Watcher INI» означает `/etc/kolla/config/watcher.conf`; при ограничении одним процессом — `/etc/kolla/config/watcher/watcher-engine.conf` или `watcher-applier.conf`. Порядок слияния, от меньшего приоритета к большему: шаблон → `config/global.conf` → `config/watcher.conf` → `config/watcher/<service>.conf` → `config/watcher/<inventory_hostname>/watcher.conf`. Результат на узле: `/etc/kolla/<service>/watcher.conf`, в контейнере: `/etc/watcher/watcher.conf`. Источники: `K:ansible/roles/watcher/tasks/config.yml:43`, `K:ansible/roles/watcher/templates/watcher-engine.json.j2:2`, `K:ansible/roles/watcher/templates/watcher-applier.json.j2:2`, `K:ansible/roles/watcher/templates/watcher-api.json.j2:2`. Пути предполагают стандартный `node_custom_config`.

| Параметр | Значение в данном снимке и mapping | Назначение / единицы | Где менять | Точное определение / потребитель |
|---|---|---|---|---|
| `watcher_datasources_list` | `prometheus` → `[watcher_datasources] datasources` | Разрешённые источники метрик; исключает переход к другим datasource из общего списка | `globals.yml` | `K:ansible/roles/watcher/defaults/main.yml:239`; `K:ansible/roles/watcher/templates/watcher.conf.j2:41`; `W:watcher/conf/datasources.py:30` |
| `watcher_prometheus_client_host` | Первый после сортировки `ansible_host` из `control`, fallback `kolla_internal_vip_address` → `[prometheus_client] host` для API/engine | Адрес Prometheus; это не обязательно первый узел inventory | `globals.yml` | `K:ansible/roles/watcher/defaults/main.yml:218`; `K:ansible/roles/watcher/templates/watcher.conf.j2:23` |
| `watcher_applier_prometheus_client_host` | `kolla_internal_vip_address` → `[prometheus_client] host` только applier | Независимый endpoint Prometheus для applier | `globals.yml` | `K:ansible/roles/watcher/defaults/main.yml:222`; `K:ansible/roles/watcher/templates/watcher.conf.j2:24` |
| `watcher_prometheus_client_port` | `prometheus_port`, здесь `9091` → `[prometheus_client] port` | TCP-порт Prometheus | `globals.yml` | `K:ansible/roles/watcher/defaults/main.yml:223`; `K:ansible/group_vars/all.yml:737`; `K:ansible/roles/watcher/templates/watcher.conf.j2:28` |
| `watcher_prometheus_client_scheme` | `http` → `[prometheus_client] scheme` | **Только рендер Kolla:** в данном Watcher опция не зарегистрирована и не читается; изменение не доказывает переключение HTTP/TLS | Не считать рабочим переключателем без проверки образа | `K:ansible/roles/watcher/defaults/main.yml:224`; `K:ansible/roles/watcher/templates/watcher.conf.j2:29`; `W:watcher/conf/prometheus_client.py:24`; `W:watcher/decision_engine/datasources/prometheus.py:120` |
| `watcher_prometheus_client_fqdn_label` | `fqdn` → `[prometheus_client] fqdn_label` | Label с именем compute; не `instance`, обычно содержащий `host:port` | `globals.yml` | `K:ansible/roles/watcher/defaults/main.yml:229`; `K:ansible/roles/watcher/templates/watcher.conf.j2:15`; `W:watcher/decision_engine/datasources/prometheus.py:139` |
| `watcher_prometheus_client_instance_uuid_label` | `resource` → `[prometheus_client] instance_uuid_label` | Label с UUID ВМ, используемый в PromQL | `globals.yml` | `K:ansible/roles/watcher/defaults/main.yml:230`; `K:ansible/roles/watcher/templates/watcher.conf.j2:31`; `W:watcher/decision_engine/datasources/prometheus.py:296` |
| `watcher_prometheus_client_username`, `watcher_prometheus_client_password`, `watcher_prometheus_client_cafile` | `admin`, ссылка `prometheus_password`, пустой CA path → одноимённые `[prometheus_client]` опции | Basic auth и путь к CA внутри контейнера; helper включает auth только при наличии обоих значений | Несекретные настройки — `globals.yml`; пароль — принятый secret backend; обеспечить доступность CA в контейнере | `K:ansible/roles/watcher/defaults/main.yml:234`; `K:ansible/roles/watcher/templates/watcher.conf.j2:32`; `W:watcher/decision_engine/datasources/prometheus.py:123` |
| `watcher_cdm_periodic_task_interval` | `300` → `[watcher_cluster_data_model_collector] periodic_task_interval` | **Только рендер Kolla:** у предоставленного Watcher период синхронизации задаётся другой опцией, следующей строкой | Не считать действующим периодом CDM | `K:ansible/roles/watcher/defaults/main.yml:248`; `K:ansible/roles/watcher/templates/watcher.conf.j2:45`; `W:watcher/decision_engine/model/collector/base.py:174` |
| `[watcher_cluster_data_model_collectors.compute] period` | Native default `3600` с; Kolla его не переопределяет | Период полного обновления compute CDM и лимит времени одной синхронизации; для `storage`/`baremetal` отдельные группы того же namespace | Watcher INI, обычно `watcher-engine.conf` | `W:watcher/decision_engine/model/collector/base.py:176`; `W:setup.cfg:108`; `W:watcher/common/loader/default.py:64`; `W:watcher/decision_engine/scheduling.py:47` |
| `watcher_audit_coalesce`, `watcher_audit_misfire_grace_time` | `yes` → `[audit] coalesce=true`; `600` → `[audit] misfire_grace_time` | **Только рендер Kolla:** регистрация и чтение этих опций в данном Watcher отсутствуют; нельзя обещать объединение пропущенных запусков и grace 600 с | Сначала проверить реализацию образа | `K:ansible/roles/watcher/defaults/main.yml:249`; `K:ansible/roles/watcher/templates/watcher.conf.j2:48`; `W:watcher/decision_engine/audit/continuous.py:119` |
| `[watcher_datasources] query_max_retries` | `10`, минимум `1`; Kolla не задаёт | Число итераций query retry; исключения, указанные как ignored, не повторяются | Watcher INI | `W:watcher/conf/datasources.py:38`; `W:watcher/decision_engine/datasources/base.py:80`; `W:watcher/decision_engine/datasources/prometheus.py:419` |
| `[watcher_datasources] query_timeout` | `1` с, минимум `0`; Kolla не задаёт | Пауза между повторными запросами, **не HTTP request timeout** | Watcher INI | `W:watcher/conf/datasources.py:44`; `W:watcher/decision_engine/datasources/base.py:96` |
| `[collector] collector_plugins` | `compute`; Kolla не задаёт | Какие модели собирать: доступны также `storage` и `baremetal`; включённый Ironic сам по себе не включает baremetal collector | Watcher INI | `W:watcher/conf/collector.py:24`; `W:watcher/decision_engine/model/collector/manager.py:33` |
| `[watcher_decision_engine] max_audit_workers`, `max_general_workers` | `2` и `4`; Kolla не задаёт | Число потоков аудитов и общих задач соответственно; не кластерный лимит миграций | Watcher INI | `W:watcher/conf/decision_engine.py:43` |
| `[watcher_decision_engine] action_plan_expiry`, `check_periodic_interval` | `24` ч и `1800` с; Kolla не задаёт | Срок годности плана и период проверки истечения | Watcher INI | `W:watcher/conf/decision_engine.py:55`; `W:watcher/decision_engine/scheduling.py:81` |
| `[watcher_decision_engine] continuous_audit_interval` | `10` с; Kolla не задаёт | Период поиска/постановки continuous audits; не индивидуальный интервал выполнения аудита | Watcher INI | `W:watcher/conf/decision_engine.py:79`; `W:watcher/decision_engine/audit/continuous.py:222` |
| `[watcher_applier] workers` | `1`, минимум `1`; Kolla не задаёт | Число workers applier; само по себе не устанавливает одну миграцию на host | Watcher INI | `W:watcher/conf/applier.py:26` |
| `[watcher_workflow_engines.taskflow] max_workers` | `processutils.get_worker_count()`, минимум `1`; Kolla не задаёт | Параллелизм действий в TaskFlow; engine по умолчанию `taskflow`, учитывает связи родителей в плане | Watcher INI, обычно `watcher-applier.conf` | `W:watcher/conf/applier.py:40`; `W:watcher/applier/workflow_engine/default.py:61`; `W:watcher/applier/workflow_engine/default.py:106`; `W:setup.cfg:100` |
| `[watcher_applier] rollback_when_actionplan_failed` | `false`; Kolla не задаёт | Включение rollback неуспешного плана | Watcher INI | `W:watcher/conf/applier.py:47` |
| `workload_balance`: `metrics`, `threshold` | `instance_cpu_usage`; `25.0` % | Метрика (`instance_cpu_usage`/`instance_ram_usage`) и порог нагрузки для стратегии | Параметры audit через Watcher API, не `globals.yml` | `W:watcher/decision_engine/strategy/strategies/workload_balance.py:96`; `W:watcher/decision_engine/strategy/strategies/workload_balance.py:276` |
| `workload_balance`: `period`, `granularity` | Оба `300` с | `period` — окно метрик; `granularity` есть в схеме стратегии, но в этом Prometheus `statistic_aggregation` не используется для построения запроса | Параметры audit через Watcher API | `W:watcher/decision_engine/strategy/strategies/workload_balance.py:112`; `W:watcher/decision_engine/datasources/prometheus.py:381`; `W:watcher/decision_engine/datasources/prometheus.py:411` |
| Audit `interval`, `auto_trigger` | `interval` задаёт администратор; `auto_trigger=false` | Интервал continuous audit в секундах либо cron; автоматический запуск полученного плана | Поля audit через Watcher API | `W:watcher/api/controllers/v1/audit.py:353`; `W:watcher/decision_engine/audit/continuous.py:192`; `W:watcher/decision_engine/audit/base.py:136` |
| `[DEFAULT] service_down_time` | `90` с; Kolla не задаёт | Возраст последнего heartbeat для статуса сервиса; heartbeat в данном коде поставлен каждые `60` с, литералом | Watcher INI | `W:watcher/conf/service.py:37`; `W:watcher/api/controllers/v1/service.py:81`; `W:watcher/common/service.py:132` |

Для миграции важны также ограничения, не являющиеся настройками `watcher.conf`. Action `migrate` принимает `migration_type=live/cold`, `resource_id`, `source_node`, `destination_node` (`W:watcher/applier/actions/migration.py:69`). Helper live migration имеет аргумент `retry=120` и паузу polling `1` с; action не передаёт иной retry. Это предел итераций ожидания, а не гарантированный timeout 120 с с учётом API-вызовов и раннего выхода (`W:watcher/common/nova_helper.py:310`, `W:watcher/common/nova_helper.py:364`, `W:watcher/applier/actions/migration.py:119`).

Модифицированный `workload_balance` способен сформировать несколько миграций за один audit; в коде стоит `MAX_ITERATIONS=32`, это не параметр администратора и не обещание 32 миграций (`W:watcher/decision_engine/strategy/strategies/workload_balance.py:281`). Общего cooldown, межсервисного guard с Masakari/Mistral и координации через Consul в исследованных Watcher/Kolla Watcher исходниках не обнаружено. Проверка наличия `ONGOING` action plans перед audit есть, но её обходит `audit.force`; она не доказывает общую блокировку с HA (`W:watcher/decision_engine/audit/base.py:116`).

Проверка только выбранных несекретных полей сгенерированного конфигурационного файла; её можно повторить для `watcher_applier`:

```sh
docker exec watcher_engine python3 -c 'import configparser; p=configparser.ConfigParser(interpolation=None); p.read("/etc/watcher/watcher.conf"); keys={"watcher_datasources":["datasources","query_max_retries","query_timeout"],"prometheus_client":["host","port","fqdn_label","instance_uuid_label"],"watcher_cluster_data_model_collectors.compute":["period"]}; [(print("["+s+"] "+k+"="+p.get(s,k,fallback="<not set; check source default>"))) for s,ks in keys.items() for k in ks]'
```

Чтение INI подтверждает содержание файла; для отмеченных несовпадений Kolla/Watcher оно не подтверждает, что процесс использует опцию. Подробнее: [получение метрик Watcher и настройка Prometheus](WATCHER_PROMETHEUS_FIX_GUIDE.md). Сверяйте указанную там базовую версию Kolla с вашим checkout.

## Consul

Эта роль создаёт до трёх отдельных агентов/кластеров: `management`, `customer`, `storage`. Подтверждены Ansible-значения и выдаваемый HCL; исходников Consul и `masakari-monitors`, а также подтверждённой версии исполняемого Consul в комплекте нет. В таблице **G** означает globals; **I** — inventory/host_vars для адреса конкретного хоста. Нативные HCL-ключи без Ansible-переменной отдельно помечены: автоматического пользовательского HCL override в роли нет.

| Параметр и слой | Значение/формула в исходнике | Что регулирует | Где определён и куда попадает; переопределение |
|---|---|---|---|
| `enable_consul` — Ansible | `"yes"` | Общее включение роли. Запуск конкретного контейнера также требует включённой сети и членства хоста в server/client group | `K:ansible/group_vars/all.yml:953`; `K:ansible/roles/consul/defaults/main.yml:9`. Управляет deployment, не HCL-ключом. **G**. |
| `consul_management_enabled`, `consul_customer_enabled`, `consul_storage_enabled`; `consul_networks.<name>.enabled` — Ansible | Кандидаты первоначально `default(true)`; роль пересчитывает `enabled` на каждом хосте | Management требует непустого `network_interface`; customer/storage дополнительно требуют, чтобы значение имени интерфейса отличалось от `network_interface`. При общих default-интерфейсах customer/storage отключаются | `K:ansible/group_vars/all.yml:974`; фактическая формула `K:ansible/roles/consul/tasks/main.yml:11`; интерфейсы `K:ansible/group_vars/all.yml:355`, `:370`. **G**/ **I**. Сравниваются строки имён интерфейсов, а не IP/L2-доступность. |
| `consul_networks.<name>.kolla_network`, `.interface_var`, `.address_override_var` — Ansible | management: `api` / `network_interface` / `consul_management_address`; customer: `tunnel` / `tunnel_interface` / `consul_customer_address`; storage: `storage` / `storage_interface` / `consul_storage_address` | Выбор Kolla-сети для адреса и inventory-переменной для автоотбора. Явные `consul_*_address` задаются по хостам | `K:ansible/group_vars/all.yml:979`, `:993`, `:1007` → HCL `bind_addr`, `advertise_addr` через `kolla_address`, `K:ansible/roles/consul/templates/consul.hcl.j2:5`, `:30`. Карта — **G**, адрес хоста — **I**. |
| `consul_networks.<name>.datacenter` — Ansible | `management`, `customer`, `storage` соответственно | Имя datacenter отдельного Consul-агента/кластера | `K:ansible/group_vars/all.yml:978`, `:992`, `:1006` → HCL `datacenter`, `K:ansible/roles/consul/templates/consul.hcl.j2:15`. **G**. |
| `consul_networks.<name>.server_group`, `.client_group` — Ansible | `consul-management-server`, `consul-customer-server`, `consul-storage-server`; общий client group `consul-client` | Server/client-роль, состав join и вычисление bootstrap. `site.yml` формирует server groups по `api→control`, `tunnel→network`, `storage→storage`; клиентов — из `compute` и `masakari-hostmonitor` | `K:ansible/group_vars/all.yml:982`, `:996`, `:1010`; `K:ansible/site.yml:99`, `:125` → HCL `server`, `retry_join`, `bootstrap_expect`, `K:ansible/roles/consul/templates/consul.hcl.j2:1`, `:67`, `:85`. Inventory + **G** согласованно. |
| `consul_networks.<name>.masakari_monitor`, `.masakari_name`, `.masakari_order` — Ansible | Для всех `true`; имена `manage`, `tenant`, `storage`; порядок `10`, `20`, `30` | Участие сети и порядок колонок в Masakari matrix, имя `agent_*`. Учитываются только сети с `enabled=true`; допустимы три указанных имени без повторов | `K:ansible/group_vars/all.yml:986`, `:1000`, `:1014`; `K:kolla_ansible/masakari_consul.py:67` → `[consul] agent_*` и `matrix.yaml.sequence`. **G**. |
| `consul_client_addr` — Ansible | `"127.0.0.1"` | Адрес клиентских интерфейсов агента, в том числе HTTP API. Общий для всех сетевых сервисов на хосте | `K:ansible/group_vars/all.yml:1072` → HCL `client_addr`, `K:ansible/roles/consul/templates/consul.hcl.j2:34`. **G**; учитывать общий host network и конфликты нескольких агентов. |
| `consul_server_port`, `consul_serf_lan_port`, `consul_serf_wan_port`, `consul_http_port`; отключённые интерфейсы | `8300`, `8301`, `8302`, `8500`; `consul_dns_port`, `consul_https_port`, `consul_grpc_port`, `consul_grpc_tls_port` — `-1` | Порты server RPC, LAN/WAN gossip и HTTP; остальные интерфейсы отключены в шаблонной конфигурации | `K:ansible/group_vars/all.yml:1059` → HCL `ports { server, serf_lan, serf_wan, http, https, dns, grpc, grpc_tls }`, `K:ansible/roles/consul/templates/consul.hcl.j2:103`. **G**. Это общие, не отдельные per-network переменные. |
| `consul_min_server_count`, `consul_require_odd_server_count` — Ansible | `3`, `true` | Минимум серверов и нечётность состава при precheck; не самостоятельный механизм формирования quorum | `K:ansible/group_vars/all.yml:1067`; проверка `K:ansible/roles/consul/tasks/precheck.yml:14`. HCL-ключа нет. Проверка пропускает пустую server group (`:33`). **G**. |
| HCL `bootstrap_expect`, `retry_join` — производные | `bootstrap_expect = length(groups[server_group])` только для server; `retry_join` — адреса всех серверов соответствующей сети с `:<consul_serf_lan_port>` | Ожидаемый размер bootstrap и адреса присоединения. Отдельные native defaults `retry_interval`/`retry_max` этот исходник не задаёт | `K:ansible/roles/consul/templates/consul.hcl.j2:67`, `:85`. Меняются составом inventory и сетевой картой; `consul_server_bootstrap_expect` этот шаблон не читает. |
| HCL `node_name`; объявленная Ansible `consul_node_name` | Фактически `{{ ansible_fqdn }}`; переменная объявлена как `{{ inventory_hostname }}`, но не используется шаблоном | Имя узла в Consul; важно для сопоставления узлов Masakari/Nova/Ironic. Изменение одной `consul_node_name` сейчас не меняет HCL | `K:ansible/roles/consul/templates/consul.hcl.j2:13`; неиспользуемая переменная `K:ansible/roles/consul/defaults/main.yml:114`. Поддержанного отдельного override имени через эту переменную нет. |
| `consul_require_gossip_key`; `consul_networks.<name>.gossip_encrypt_key` — Ansible | `true`; ссылка на `consul_management_gossip_key` / `consul_customer_gossip_key` / `consul_storage_gossip_key`, defaults пустые | Precheck требует непустой ключ у включённой сети; непустое значение выводится как HCL `encrypt`. Проверка в этой роли проверяет наличие, а не длину декодированного ключа | `K:ansible/group_vars/all.yml:959`, `:1074`; `K:ansible/roles/consul/tasks/precheck.yml:61`; `K:ansible/roles/consul/templates/consul.hcl.j2:76`. Флаг — **G**, значения секретов — предусмотренное хранилище secrets/passwords, без публикации в справочнике. |
| `consul_acl_enabled`, `consul_acl_default_policy`, `consul_acl_down_policy` — Ansible | `false`, `"deny"`, `"extend-cache"` | Включение ACL, policy по умолчанию и policy при недоступности ACL-источника. Опции policy записываются и при выключенном ACL | `K:ansible/group_vars/all.yml:1080` → HCL `acl.enabled`, `acl.default_policy`, `acl.down_policy`, `K:ansible/roles/consul/templates/consul.hcl.j2:41`. **G**. Одно включение флага не подтверждает готовность выдачи/доставки ACL-токенов. |
| `consul_acl_token_ttl` — Ansible | `"30s"` | Значение native `acl.token_ttl` для кэширования ACL-токенов | `K:ansible/group_vars/all.yml:1083` → HCL `acl.token_ttl`, `K:ansible/roles/consul/templates/consul.hcl.j2:45`. **G**. |
| `consul_tls_enabled`, `consul_tls_verify_incoming`, `consul_tls_verify_outgoing`, `consul_tls_verify_server_hostname` — Ansible | `false`; три verify-флага — `true` | Включение выдачи TLS-настроек и проверок сертификатов. Выключенный TLS-флаг убирает этот блок из HCL | `K:ansible/group_vars/all.yml:1086`, `:1090` → HCL `verify_incoming`, `verify_outgoing`, `verify_server_hostname`, `K:ansible/roles/consul/templates/consul.hcl.j2:53`. **G**. |
| `consul_tls_ca_file`, `consul_tls_cert_file`, `consul_tls_key_file` — Ansible | `/etc/consul.d/ca.pem`, `/etc/consul.d/consul.pem`, `/etc/consul.d/consul-key.pem` | Пути внутри контейнера к TLS-материалам. Это ссылки на файлы, не механизм их доставки | `K:ansible/group_vars/all.yml:1087` → HCL `ca_file`, `cert_file`, `key_file`, `K:ansible/roles/consul/templates/consul.hcl.j2:57`. **G**; роль копирует только `consul.hcl`, `K:ansible/roles/consul/templates/consul.json.j2:11`. |
| `consul_log_level` — Ansible | `"INFO"` | Уровень логирования агента | `K:ansible/group_vars/all.yml:1058` → HCL `log_level`, `K:ansible/roles/consul/templates/consul.hcl.j2:19`. **G**. |
| HCL `gossip_lan.probe_interval` — фиксированный template | `"1s"` | Заданный шаблоном интервал probe LAN gossip | `K:ansible/roles/consul/templates/consul.hcl.j2:118`. Не связан с `consul_probe_interval`; поддержанного **G**/custom-HCL override в роли нет. |
| HCL `gossip_lan.probe_timeout` — фиксированный template | `"1s"` | Заданный шаблоном timeout probe LAN gossip | `K:ansible/roles/consul/templates/consul.hcl.j2:119`. Не связан с `consul_probe_timeout`; комментарий `500ms` в примере globals не является действующим значением. |
| HCL `gossip_lan.suspicion_mult` — фиксированный template | `6` | Заданный шаблоном множитель suspicion. Это не гарантированный срок обнаружения отказа в секундах | `K:ansible/roles/consul/templates/consul.hcl.j2:120`. Не связан с `consul_suspicion_mult`; итоговый алгоритм и допустимость HCL должны проверяться на установленной версии Consul. |

Роль использует `template`, а не `merge_configs`: вход `K:ansible/roles/consul/templates/consul.hcl.j2`, результат `/etc/kolla/consul-<network>/consul.hcl` (`K:ansible/roles/consul/tasks/config.yml:31`), внутри контейнера `/etc/consul.d/consul.hcl`, команда `consul agent -config-dir=/etc/consul.d` (`K:ansible/roles/consul/templates/consul.json.j2:2`). Поэтому добавление `/etc/kolla/config/consul.hcl` или `config/consul/...` не создаёт override в данной реализации. Поддержанные переменные меняют через globals/inventory; изменение фиксированных HCL-настроек требует отдельного изменения шаблона/роли. Reconfigure импортирует deploy, повторно генерирует конфиг и запускает handlers перезапуска (`K:ansible/roles/consul/tasks/reconfigure.yml:2`; `K:ansible/roles/consul/tasks/deploy.yml:3`; `K:ansible/roles/consul/handlers/main.yml:3`).

Ограничения, которые необходимо учитывать при применении параметров:

- Автоотбор сетей в `tasks/main.yml` сравнивает **имена интерфейсов на текущем хосте**. Комментарий group_vars о сравнении IP/отдельном L2 не соответствует фактической формуле. Кроме того, проверка непустого `interface_var` сохраняется даже при наличии `consul_*_address` (`K:ansible/roles/consul/tasks/main.yml:17`).
- Несколько агентов на одном узле получают одинаковые `client_addr=127.0.0.1` и HTTP port `8500`, а все `agent_*` hostmonitor — одинаковый endpoint. Контейнеры используют host network (`K:ansible/module_utils/kolla_docker_worker.py:291`; `K:ansible/module_utils/kolla_podman_worker.py:200`). Это статически выявленный конфликт стандартной схемы размещения нескольких агентов; готовность multi-network нельзя заключить только по включённым флагам и успешно сформированной матрице. Фактические listener-адреса и соответствие каждого endpoint своему datacenter здесь не проверены.
- `server_group_extra` объявлен списком, но `site.yml` передаёт весь список как ключ в `groups.get(...)` (`K:ansible/group_vars/all.yml:983`; `K:ansible/site.yml:121`). Поэтому описывать непустой список дополнительных групп как проверенный способ расширения server group нельзя.
- ACL/TLS — opt-in-настройки HCL. В `consul.json.j2` нет доставки ACL-токенов и TLS-файлов, а hostmonitor-шаблон выдаёт адреса через `consul_http_port`. Простой переход на `https_port`/ACL требует согласованного обеспечения материалов и совместимости клиента; это не подтверждено одним наличием переменных.
- `consul_probe_interval`, `consul_probe_timeout`, `consul_indirect_checks`, `consul_suspicion_mult`, `consul_suspicion_max_timeout`, `consul_server_bootstrap_expect` в `etc/kolla/globals.yml` помечены историческими и не читаются исследованным per-network шаблоном (`K:etc/kolla/globals.yml:1113`). В справочнике действующими считаются значения HCL выше.

Проверки без изменения состояния, для одного явно выбранного контейнера; повторить для каждого реально включённого `consul_management` / `consul_customer` / `consul_storage`:

```bash
# Версия бинарника нужна для сопоставления HCL с действительной реализацией.
docker exec consul_management consul version
# Читающий запрос списка участников; токены и полная конфигурация не выводятся.
docker exec consul_management consul members
```

Выполнение этих команд в одном контейнере при общих HTTP-адресах само по себе не доказывает, что запрос обслужил именно его агент; необходима проверка фактических listener-адресов. Команды не выполнялись против стенда. Ни `probe_interval`, ни `monitoring_samples`, ни `matrix_policy` по отдельности не задают гарантированное полное время «отказ сети → fencing → эвакуация».

## Ironic

В этом снимке Ironic предназначен для BMC/power существующих compute-узлов. Enrollment создаёт node в `enroll`, вызывает переход `manage` и ожидает конечное состояние `manageable`; `available`, deploy и очистка не являются результатом этого playbook (`K:ansible/roles/ironic_enroll/tasks/enroll.yml:157`, `K:ansible/roles/ironic_enroll/tasks/enroll.yml:247`, `K:ansible/roles/ironic_enroll/tasks/verify.yml:2`).

«Ironic INI» ниже означает `/etc/kolla/config/ironic/ironic-conductor.conf` для conductor-specific опций. Порядок слияния: шаблон → `config/global.conf` → `config/ironic.conf` → `config/ironic/<service>.conf` → `config/ironic/<inventory_hostname>/ironic.conf`. Результат: `/etc/kolla/<service>/ironic.conf` на узле и `/etc/ironic/ironic.conf` внутри контейнера (`K:ansible/roles/ironic/tasks/config.yml:87`, `K:ansible/roles/ironic/templates/ironic-conductor.json.j2:5`). **Node attributes/`driver_info` живут в Ironic API/БД, а не в этом INI.**

| Параметр | Значение в данном снимке и mapping | Назначение / единицы | Где менять | Точное определение / потребитель |
|---|---|---|---|---|
| `enable_ironic`; `enable_ironic_dnsmasq`, `enable_ironic_inspector`, `enable_ironic_neutron_agent` | `yes`; остальные три `no` | Включение Ironic и дополнительных компонентов | `globals.yml` | `K:ansible/group_vars/all.yml:1156` |
| `[DEFAULT] enabled_hardware_types` | В шаблоне conductor литерал `ipmi,redfish` | Разрешённые hardware types; Kolla-переменной `ironic_enabled_hardware_types` здесь нет | Ironic INI | `K:ansible/roles/ironic/templates/ironic.conf.j2:24` |
| `[DEFAULT] enabled_power_interfaces`, `enabled_management_interfaces` | Оба `ipmitool,redfish` | Разрешённые реализации power/management; node выбирает одну совместимую реализацию | Ironic INI; выбранные node interfaces — Ironic API/enrollment | `K:ansible/roles/ironic/templates/ironic.conf.j2:29`; `K:ansible/roles/ironic_enroll/tasks/enroll.yml:159` |
| `[DEFAULT] enabled_network_interfaces`, `default_network_interface`; аналогичные `storage` | Везде `noop` | Power-only без работы с сетью/хранилищем provisioning; enrollment также записывает node `network_interface=storage_interface=noop` | Ironic INI для разрешений/default; node attrs — API/enrollment | `K:ansible/roles/ironic/templates/ironic.conf.j2:37`; `K:ansible/roles/ironic_enroll/tasks/enroll.yml:168` |
| `[DEFAULT] enabled_inspect_interfaces`, `default_inspect_interface`; пары `bios`, `raid`, `console`, `rescue`, `firmware`, `vendor` | `no-inspect`; `no-bios`, `no-raid`, `no-console`, `no-rescue`, `no-firmware`, `no-vendor` | Отключённые реализации ненужных семейств интерфейсов | Ironic INI; существующие node attrs отдельно | `K:ansible/roles/ironic/templates/ironic.conf.j2:35`; `K:ansible/roles/ironic/templates/ironic.conf.j2:41` |
| `[DEFAULT] enabled_boot_interfaces`, `default_boot_interface`; `enabled_deploy_interfaces`, `default_deploy_interface` | `pxe`; `direct` | Совместимые реализации обязательных семейств. Наличие этих значений не означает запуск PXE/deploy | Ironic INI; enrollment фиксирует те же node attrs | `K:ansible/roles/ironic/templates/ironic.conf.j2:31`; `K:ansible/roles/ironic_enroll/tasks/enroll.yml:166` |
| `[conductor] automated_clean` | Литерал `false` в conductor template | Автоматическая очистка выключена | Ironic INI | `K:ansible/roles/ironic/templates/ironic.conf.j2:101` |
| `ironic_bmc_hosts` / группа inventory `[bmc]`; `address`, `type`, `attached_host` | Пустой mapping по fallback; `address/type` обязательны; `attached_host` по умолчанию равен ключу/имени BMC | Источник BMC endpoints; `attached_host` становится именем Ironic node. Уже существующий `[bmc]` host не заменяется globals mapping | `globals.yml` mapping либо inventory/host_vars | `K:ansible/ironic-enroll-inventory.yml:6`; `K:ansible/roles/ironic_enroll/tasks/validate.yml:5`; `K:ansible/roles/ironic_enroll/tasks/enroll.yml:152` |
| `ironic_driver_priority`, `ironic_supported_bmc_types` | Приоритет: `redfish`, `ilo5`, `drac5`, `xclarity`, `irmc`, `ipmi` | Для комбинированного `type` через `+` выбирает driver и power/management interfaces. Mapping не включает соответствующий driver в conductor автоматически | `globals.yml`; per-BMC `type` — inventory/mapping | `K:ansible/roles/ironic_enroll/defaults/main.yml:23`; `K:ansible/roles/ironic_enroll/defaults/main.yml:55`; `K:ansible/roles/ironic_enroll/tasks/detect_driver.yml:5` |
| `ironic_enroll_mode` | `bmc-only` → node `extra.enrollment_profile` | Метка профиля; не переключатель provisioning: интерфейсы/state в tasks заданы отдельно | `globals.yml`; не менять как способ включить provisioning | `K:ansible/roles/ironic_enroll/defaults/main.yml:2`; `K:ansible/roles/ironic_enroll/tasks/enroll.yml:174` |
| `ironic_enroll_cloud` | `kolla-admin`; `OS_CLIENT_CONFIG_FILE={{ node_config }}/clouds.yaml` | Какая запись clouds.yaml используется Ansible-модулями и CLI enrollment | `globals.yml`; учётная запись — clouds.yaml/принятый механизм credentials | `K:ansible/roles/ironic_enroll/defaults/main.yml:4`; `K:ansible/enroll-ironic.yml:29`; `K:ansible/roles/ironic_enroll/tasks/enroll.yml:146` |
| `ironic_enroll_api_interface` | `internal` → SDK `interface` и CLI `--os-interface` | Endpoint OpenStack API; не `network_interface` node и не BMC-интерфейс | `globals.yml` | `K:ansible/roles/ironic_enroll/defaults/main.yml:5`; `K:ansible/roles/ironic_enroll/tasks/enroll.yml:147`; `K:ansible/roles/ironic_enroll/tasks/enroll.yml:215` |
| `ironic_enroll_serial` | `25` | Размер партии BMC hosts в Ansible play | `globals.yml` | `K:ansible/roles/ironic_enroll/defaults/main.yml:7`; `K:ansible/enroll-ironic.yml:28` |
| `ironic_enroll_throttle` | `10` | Ограничение параллельных выполнений конкретных create/manage tasks. Это **не BMC/с**, несмотря на комментарий globals | `globals.yml` | `K:ansible/roles/ironic_enroll/defaults/main.yml:8`; `K:ansible/roles/ironic_enroll/tasks/enroll.yml:180`; `K:ansible/roles/ironic_enroll/tasks/enroll.yml:263`; `K:etc/kolla/globals.yml:1099` |
| `ironic_enroll_manage_timeout` | `300` с → `openstack baremetal node manage --wait 300` | Ожидание перехода `enroll/enroll failed` к `manageable`; не timeout команды power/BMC | `globals.yml` | `K:ansible/roles/ironic_enroll/defaults/main.yml:9`; `K:ansible/roles/ironic_enroll/tasks/enroll.yml:247` |
| `ironic_enroll_state_read_retries`, `ironic_enroll_state_read_delay` | `6` и `2` с | Повторы чтения provision state через OpenStack CLI; не повторы BMC-команды | `globals.yml` | `K:ansible/roles/ironic_enroll/defaults/main.yml:10`; `K:ansible/roles/ironic_enroll/tasks/enroll.yml:229` |
| `ironic_enroll_verify_retries`, `ironic_enroll_verify_delay` | `12` и `5` с | Финальное ожидание `provision_state=manageable`; фактическое время включает длительность CLI-вызовов | `globals.yml` | `K:ansible/roles/ironic_enroll/defaults/main.yml:12`; `K:ansible/roles/ironic_enroll/tasks/verify.yml:22` |
| `ironic_enroll_default_redfish_system_id`; per-BMC `redfish_system_id` | `/redfish/v1/Systems/System.Embedded.1`; per-BMC значение приоритетнее; пустое значение не добавляется в `driver_info` | URI конкретной Redfish ComputerSystem; default подходит не каждому BMC | Глобальный default — `globals.yml`; per-BMC — inventory/mapping; хранится в node `driver_info` | `K:ansible/roles/ironic_enroll/defaults/main.yml:19`; `K:ansible/roles/ironic_enroll/tasks/enroll.yml:23` |
| Per-BMC `redfish_address` | По умолчанию `https://` + `address` → node `driver_info.redfish_address` | BMC endpoint; отдельный override допускает явный `http(s)://host[:port]` | Inventory/mapping; далее node API | `K:ansible/roles/ironic_enroll/tasks/enroll.yml:11`; `K:ansible/roles/ironic_enroll/tasks/validate.yml:53` |
| Per-BMC `redfish_verify_ca` | По умолчанию `ironic_enroll_bmc_ca_container_path` → node `driver_info.redfish_verify_ca` | Проверка Redfish TLS; путь относится к файловой системе conductor-контейнера | Inventory/mapping; далее node API | `K:ansible/roles/ironic_enroll/tasks/enroll.yml:13`; `K:ansible/roles/ironic_enroll/tasks/validate.yml:21` |
| `ironic_enroll_bmc_username`; inventory `ironic_bmc_username` | `admin`; globals mapping переносит общий username в `ironic_enroll_bmc_username_global`; inventory fallback учитывает `ironic_bmc_username` | Логин BMC → соответствующее поле node `driver_info` | `globals.yml` либо inventory/host_vars; при наличии `_global` он приоритетнее | `K:ansible/roles/ironic_enroll/defaults/main.yml:20`; `K:ansible/ironic-enroll-inventory.yml:21`; `K:ansible/roles/ironic_enroll/tasks/validate.yml:26`; `K:ansible/roles/ironic_enroll/tasks/enroll.yml:18` |
| `ironic_bmc_redfish_password`, `ironic_bmc_ipmi_password` и `vault_ironic_bmc_*_password` | При `enable_config_vault=true` берутся transient Vault значения, иначе прямые переменные; fallback пустой | Источник BMC credentials. В Redfish пароль записывается; для IPMI есть пробел реализации, см. ниже | Принятый secret backend/passwords.yml; не помещать значения в документацию | `K:ansible/roles/ironic_enroll/tasks/resolve_passwords.yml:2`; `K:ansible/roles/ironic_enroll/tasks/enroll.yml:19`; `K:ansible/roles/ironic_enroll/tasks/enroll.yml:31` |
| `ironic_enroll_bmc_ca_source`, `ironic_enroll_bmc_ca_host_path`, `ironic_enroll_bmc_ca_container_path` | Source fallback `/etc/kolla/certificates/bmc-ca.pem`; host `{{ node_config }}/certificates/bmc-ca.pem`; container `/etc/ironic/bmc-ca.pem` | Source/host/container пути CA — разные места. Prepare копирует только на conductor host; mount требуется проверить отдельно | `globals.yml`; при необходимости явный mount через `ironic_conductor_extra_volumes` | `K:ansible/roles/ironic_enroll/tasks/prepare.yml:14`; `K:ansible/roles/ironic_enroll/defaults/main.yml:15`; `K:ansible/roles/ironic/defaults/main.yml:283` |
| `enable_ironic_prometheus_exporter`; `ironic_prometheus_exporter_sensor_data_interval`, `ironic_prometheus_exporter_sensor_data_undeployed_nodes` | `enable_ironic and enable_prometheus`; `300` с; `true` → `[conductor] send_sensor_data=true`, `send_sensor_data_interval`, `send_sensor_data_for_undeployed_nodes` | Сбор сенсоров, включая undeployed nodes; не polling выполнения power action | `globals.yml` | `K:ansible/group_vars/all.yml:1160`; `K:ansible/roles/ironic/defaults/main.yml:321`; `K:ansible/roles/ironic/templates/ironic.conf.j2:104` |
| `ironic_enroll_run_after_post_deploy` | `false`, только объявление default | В данном дереве потребитель не найден; `true` само по себе не доказывает автозапуск enrollment после post-deploy | Не использовать как доказанный рабочий toggle | `K:ansible/roles/ironic_enroll/defaults/main.yml:21` |

Существующие nodes принимаются только в `enroll`, `enroll failed`, `verifying`, `manageable` и с `extra.managed_by=ansible`. При reconciliation модуль обновляет только `driver_info`: изменение `type`/интерфейсов в inventory не гарантирует изменение driver или interfaces уже существующего node (`K:ansible/roles/ironic_enroll/tasks/enroll.yml:105`, `K:ansible/roles/ironic_enroll/tasks/enroll.yml:121`, `K:ansible/roles/ironic_enroll/tasks/enroll.yml:177`).

Ограничения именно этого снимка:

- Таблица enrollment содержит `ilo/idrac/xclarity/irmc`, но conductor разрешает только `ipmi,redfish`. Перечень vendor types не является доказательством их готовности к работе.
- IPMI branch формирует `ipmi_address`, `ipmi_username`, `ipmi_priv_level=ADMINISTRATOR`, но не добавляет `ipmi_password`, хотя resolver выбирает IPMI secret (`K:ansible/roles/ironic_enroll/tasks/enroll.yml:31`, `K:ansible/roles/ironic_enroll/tasks/resolve_passwords.yml:5`). Подробнее: [разбор IPMI enrollment и BMC credentials](IRONIC_ENROLL_IPMI_BMC_FIX_GUIDE.md).
- Копирование BMC CA на host не доказывает наличие `/etc/ironic/bmc-ca.pem` в контейнере: такого mount в `ironic_conductor_default_volumes` и такой копии в `ironic-conductor.json.j2` нет (`K:ansible/roles/ironic/defaults/main.yml:237`, `K:ansible/roles/ironic/templates/ironic-conductor.json.j2:3`).
- Собственный исходник Ironic conductor/drivers в исследованном комплекте отсутствует; Kolla-шаблон не задаёт native BMC retry/Redfish timeouts. Их имена, default и фактическая поддержка зависят от Ironic/Sushy в образе и здесь **не установлены**. Enrollment retries, manage timeout и PowerOps timeout нельзя выдавать за BMC-driver timeout.

Две проверки без вывода BMC credentials:

```sh
# NODE — имя либо UUID узла. Выбраны только несекретные поля.
NODE="имя-или-UUID-узла"
openstack baremetal node show "$NODE" -f yaml -c uuid -c name -c driver -c provision_state -c power_state -c maintenance -c power_interface -c management_interface -c network_interface
# Выполняется на conductor host; exit 0 означает, что файл доступен для чтения.
docker exec ironic_conductor test -r /etc/ironic/bmc-ca.pem
```

Обе проверки только читают состояние; они не подтверждают успешную power-операцию. `provision_state=manageable` и `power_state` — отдельные свойства node.

## Как проверить, какое значение действительно используется

Проверка проходит по цепочке: **объявление → переопределения → шаблон → файл в контейнере → чтение опции кодом сервиса**. Одного совпадения имени в `globals.yml` недостаточно. Если шаблон не использует переменную, её изменение не влияет на сервис. Если код не регистрирует/не читает native option, присутствие строки в INI тоже не доказывает её действие.

### Поиск определений в своём checkout

На deploy host, из корня используемого Kolla-Ansible:

```bash
# Поиск определений и потребителей конкретной переменной.
rg -n -- 'vmclone_wait_timeout|masakari_hostmonitor_driver' \
  ansible/group_vars ansible/roles etc/kolla

# Поиск переопределений в настройках окружения.
# Если globals.d ещё не создан, исключите этот путь из команды.
rg -n -- 'vmclone_wait_timeout|masakari_hostmonitor_driver' \
  /etc/kolla/globals.yml /etc/kolla/globals.d
```

Сверяйте checkout с той версией, из которой запускается `kolla-ansible`: исходники рядом с архивом могут отличаться от установленного пакета. `ansible-inventory --list` показывает inventory, но сам по себе не воспроизводит загрузку role defaults, Kolla extra vars и INI merge. Полный вывод inventory/config может содержать секреты, поэтому для обращения за помощью достаточно выбранных параметров и версий.

### Чтение выбранных параметров VMClone в контейнере

На узле с `mistral_executor`, при Docker и стандартных именах контейнеров:

```bash
docker exec -i mistral_executor python3 - <<'PY'
import configparser
from pathlib import Path

path = Path('/etc/mistral/mistral.conf')
cfg = configparser.ConfigParser(interpolation=None, strict=False)
with path.open() as stream:
    cfg.read_file(stream)
for key in ('enabled', 'request_timeout', 'wait_timeout',
            'poll_interval', 'max_disks', 'allowed_roles'):
    value = cfg.get('vmclone', key, fallback='<нет в файле>')
    print(f'[vmclone] {key} = {value}')
PY
```

Команда читает файл и выводит только перечисленные настройки. Она не выполняет action и не меняет ВМ. При Podman замените `docker` на `podman`. Отсутствующий ключ требует проверки default **установленной** версии пакета; отсутствие секции также может означать, что патч ещё не установлен или шаблон не был применён. Значение в файле не доказывает, что уже запущенный процесс перечитал его.

По тому же принципу проверяют конкретные section/key в `/etc/masakari/masakari.conf`, `/etc/masakari-monitors/masakari-monitors.conf`, `/etc/watcher/watcher.conf` и `/etc/ironic/ironic.conf`. Для Consul используется HCL, а не INI; отдельные проверки приведены в его разделе. Имена контейнеров и каталоги на вашем стенде могут быть переопределены.

### Порядок изменения параметров

1. Найдите параметр в таблицах и исходниках своей версии. Уточните единицу, область действия и наличие потребителя.
2. Для Ansible-переменной задайте только необходимое отличие от defaults в `globals.yml`/`globals.d`; для native INI option используйте путь override соответствующей роли. Consul HCL требует своего механизма.
3. Проверьте более поздние overrides и условие формирования секции. Для VMClone отдельно проверьте наличие патчей в Kolla и образах Mistral.
4. Примените изменение штатной процедурой Kolla для выбранного сервиса и окружения. Это отдельная операция, которая может затрагивать контейнеры; команды применения в рамках подготовки этого справочника не запускались.
5. На всех затронутых узлах проверьте выбранные ключи в доставленных конфигах, версию образа и факт перезапуска/перечитывания конфигурации.
6. Подтвердите ожидаемое поведение отдельной эксплуатационной проверкой. Наличие ключа в файле не заменяет проверку получения метрик, detection/recovery, BMC-доступа или клонирования.

## Какие таймауты нельзя подменять друг другом

| Контур | Что ограничивают параметры | Чего из них нельзя заключить |
|---|---|---|
| Mistral / VMClone | HTTP-запрос, отдельное ожидание ресурса, число дисков, доступ к actions | Что весь workflow закончится за `wait_timeout`, или что увеличение таймаута исправит `error` Cinder/Nova |
| Mistral / PowerOps | Захват lock, наблюдение питания, graceful shutdown, instance/service waits | Что истечение ожидания разрешает hard-off или снимает межсервисные ограничения |
| Masakari | Проверку состояния Nova, этапы recovery, повторы fencing/evacuation | Что одна настройка определяет полное время восстановления ВМ |
| Consul / hostmonitor | Периоды наблюдения и пороги обнаружения отказа | Что detector гарантирует завершение fencing или evacuation за тот же интервал |
| Watcher | Получение метрик, построение модели, выполнение действий | Что interval сбора автоматически задаёт расписание audits или миграций |
| Ironic / enroll | Проверку перехода provisioning state и настройки BMC-доступа | Что таймаут Ansible enroll является runtime power timeout Ironic/Masakari/PowerOps |

Для конкретной операции оценивайте последовательность её стадий, число ресурсов и повторов. Defaults из разных сервисов не складываются в универсальный SLA без анализа workflow и проверки на стенде.
