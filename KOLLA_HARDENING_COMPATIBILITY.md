**Применимость USCR hardening к форку Kolla-Ansible PVS от 23.09**

Дата анализа: 29 сентября 2026 года.

Источники: `uscr-production@290a25d1e36-v3.zip` и `kolla-ansible-pvs_1.0.0_23.09.zip` из текущей рабочей папки. Проверены роли, defaults, точки входа CLI, порядок deploy/reconfigure, SELinux-профили и реализация host-firewall. Это статическое сопоставление исходников; эффективный inventory/globals работающего кластера, установленная внешняя коллекция `openstack.kolla` и состояние узлов не проверялись. Исходный код не менялся, плейбуки не запускались.

**Вывод: применимы отдельные меры после адаптации; общий USCR-профиль в текущем виде несовместим с SELinux-профилями форка. Управление SELinux и firewalld следует оставить за Kolla, а хостовый hardening согласовать с её жизненным циклом.**

| Область | Оценка по исходникам |
|---|---|
| SELinux | Прямой конфликт требований: USCR требует `disabled`, Kolla SELinux profiles требуют `enabled` и `targeted` на ОС версии 9 |
| Firewall | USCR не заменяет host-firewall форка. Его точечные изменения iptables для SOC требуют согласования с firewalld и другими владельцами сетевых правил |
| Bootstrap/deploy/reconfigure | Массовый hardening нельзя добавлять как произвольную задачу до/после deploy: он меняет доступ, службы и системные настройки, а Kolla временно меняет состояние защитных механизмов |
| SSH, PAM, пароли, права | Потенциально переносимые меры, но с учётом учётной записи Ansible, sudo, поддерживаемой ОС, контейнерных конфигураций и каталогов |
| sysctl | Возможен выбор отдельных параметров; в исходном USCR-списке нет сетевых sysctl Neutron, однако отсутствие совпадения ключей не доказывает совместимость workloads |

**1. SELinux: что конфликтует**

Стандартный USCR precheck включает `check_selinux: 1`. При наличии `/usr/sbin/sestatus` он проверяет наличие слова `disabled` в выводе и иначе завершает проверку ошибкой. Следовательно, режимы `permissive` и `enforcing` для этого precheck одинаково неприемлемы. USCR defaults[^uscr-precheck-defaults], условие проверки[^uscr-precheck].

При `enable_selinux_profiles: yes` ваш форк, наоборот, требует:

- основную версию ОС `9`;
- `ansible_facts.selinux.status == 'enabled'`;
- политику `targeted`;
- системные Python bindings `selinux` и `semanage`.

Роль не является процедурой перевода произвольной ОС из disabled в готовый к работе SELinux: она сначала проверяет уже включённый SELinux. Проверки профилей[^selinux-install], подготовка[^selinux-prepare].

Во время `deploy/reconfigure` роль переводит весь хост в permissive, устанавливает CIL-модули и booleans, а контейнерный worker назначает соответствующим контейнерам домены Kolla. В конце, в зависимости от `selinux_profiles_mode`, роль оставляет permissive либо включает enforcing. Часть сервисов остаётся privileged; наличие набора CIL-файлов не означает одинаковую изоляцию всех контейнеров. Установка[^selinux-install], container worker[^container-worker], финализация[^selinux-finalize].

По defaults `enable_selinux_profiles: "no"`, `selinux_profiles_mode: "permissive"`. Это значения поставляемого кода, не доказательство параметров вашего работающего кластера. Выключение `enable_selinux_profiles` после управляемого развёртывания выполняет откат модулей/меток и оставляет permissive, а не disabled. Поэтому выключение только этого флага не устраняет требование USCR. Defaults форка[^all-vars], откат[^selinux-rollback].

Дополнительный прямой конфликт — аудит. USCR устанавливает в auditd правило:

```text
-a always,exclude -F msgtype=AVC
```

Оно исключает AVC-записи из audit-потока, то есть убирает из этого канала материал для диагностики SELinux-отказов. В окружении с собственными SELinux-профилями переносить это правило без изменения нельзя. Это не утверждение об отсутствии любых сообщений SELinux во всех остальных журналах. Правила USCR[^uscr-audit-rules].

Адаптация должна включать пересмотр требования precheck, отказ от ролей отключения SELinux и пересмотр правил аудита. Простое `check_selinux: 0` только обходит проверку; оно не подтверждает совместимость остальных задач с SELinux.

**2. Firewall: кто им управляет в этом форке**

В версии от 23.09 host-firewall встроен в `site.yml` и работает в lifecycle `deploy/reconfigure/destroy`; отдельно сохранена команда `kolla-ansible host-firewall`. Это необходимо отличать от более ранних реализаций с отдельным ручным применением.

| Этап | Поведение текущего кода |
|---|---|
| `bootstrap-servers` | CLI выбирает `kolla-host.yml`, принудительно задаёт Podman и выключает Docker repo. PRE Bootstrap устанавливает firewalld и останавливает/отключает его на `all,!deployment`. Затем вызывает внешнюю роль `openstack.kolla.baremetal` |
| `prechecks`, multinode | Если firewalld установлен, требует inactive и не enabled. Если пакет отсутствует, допускает это только при выключенном `enable_pvs_firewalld` |
| Начало `deploy/reconfigure`, multinode | На `baremetal` останавливает watchdog timer и firewalld; условие остановки не зависит от `enable_pvs_firewalld` |
| Конец `deploy/reconfigure`, feature enabled | Включает/запускает firewalld, формирует правила, применяет собственную политику и проверяет соединение |
| `reconfigure`, feature disabled, либо `destroy` | Через automatic rollback удаляет свою политику при наличии, останавливает и отключает firewalld |
| Single-node | Основной host-firewall и его precheck пропускаются по `groups['all'] | length <= 1`. Но PRE Bootstrap выше не содержит такого исключения |

Источники: bootstrap[^kolla-host], CLI[^commands], firewalld precheck[^firewalld-precheck], site.yml[^site], host-firewall.yml[^host-firewall], teardown[^firewall-teardown].

Точка применения host-firewall расположена после сервисных ролей и перед финализацией SELinux. Поэтому не следует запускать параллельно сторонний hardening, который останавливает службы, меняет SSH или управляет firewall. Финальные этапы — обычные задачи в конце playbook; при прерванном deploy нельзя считать, что firewalld и SELinux enforcing обязательно восстановлены. После ошибки нужны проверки фактического состояния.

Основной флаг — `enable_pvs_firewalld`, по defaults `no`. Отдельный `enable_external_api_firewalld` не является его заменой. В loadbalancer precheck при включённом external API flag требуется работающий firewalld, а общий multinode precheck требует остановленный. Совместное использование этих путей требует отдельного согласования; простое включение обоих флагов не является готовой конфигурацией. Defaults[^all-vars], loadbalancer precheck[^lb-precheck].

Политика `kolla-host-input` направлена `ANY → HOST`: это фильтрация входящего трафика хоста. Она не заменяет Neutron security groups и не доказывает защиту всего FORWARD/datapath. Компилятор добавляет разрешения из каталога и финальный `drop`; SSH-порт inventory разрешается отдельным правилом без ограничения источника. Следовательно, этот профиль сам по себе также не является ограничением SSH только бастионом. Адаптер firewalld[^firewall-adapter], компилятор правил[^firewall-plan].

USCR audit изменяет другой участок — добавляет ACCEPT для UDP к SOC в OUTPUT через iptables и может сохранять `/etc/sysconfig/iptables`. Это не прямое редактирование `kolla-host-input`, но и не интеграция с его жизненным циклом. Переносить такие операции стоит только после определения единого владельца соответствующих правил. В USCR нет готового firewall-каталога потоков OpenStack. USCR iptables[^uscr-iptables].

**3. Ограничение автоматического firewall-пути**

В `_auto_apply()` текущего форка исходные диагностические blockers заменяются пустым списком, а обязательные проверки задаются как `['ssh-fresh']`. Playbook дополнительно выставляет `host_firewall_ssh_only: true`. При этом компилятор правил формирует завершающий `drop`.

Таким образом, успешное автоматическое применение подтверждает предусмотренную проверку SSH, но не доступность API, RPC, storage, overlay, DHCP, metadata, консоли и migration. Если нужный поток отсутствует в сформированном списке, сам по себе доступный SSH не выявит эту проблему. Это конкретное ограничение кода, а не подтверждение, что на ваших узлах уже есть сетевой сбой. Automatic admission[^firewall-admission], SSH-only[^host-firewall], проверка[^firewall-verify], drop[^firewall-plan].

Аналогично, SELinux finalization проверяет наличие доменов и результат `getenforce`, но найденные unhealthy-контейнеры лишь выводит как сообщение: они не блокируют включение enforcing. Поэтому успешная финализация не является функциональным тестом всех сервисов. SELinux enforce[^selinux-enforce].

**4. Что можно переносить из USCR**

Все строки ниже предполагают сначала устранение общего конфликта precheck/SELinux. Оценка «условно применимо» не означает разрешение на запуск исходного плейбука без адаптации.

| Меры USCR | Как соотнести с Kolla |
|---|---|
| SSH, запрет root, PAM, sudo | Условно применимы к хосту. До применения должны быть определены отдельная учётная запись Ansible, её sudo-права и SSH-порт. USCR принудительно ставит 22 и комментирует `%wheel`: это может лишить deploy доступа |
| `password`, блокировка пустых паролей | Рассматривать для локальных хостовых учётных записей. Не объявлять этим защищёнными пароли сервисов, Keystone или учётные записи внутри контейнеров |
| PAM-шаблоны | Для SberLinux 9 шаблон есть; `pam_redhat_9.j2` в USCR отсутствует. Допуск версии 9 общим precheck не устраняет это ограничение. Также необходимо согласовать Python interpreter: USCR defaults задают `/usr/libexec/platform-python` |
| `profile`, `pamenv` | Потенциально переносимы как политика хостовых сессий, после проверки сценариев администрирования |
| `sysctl` | Выбирать параметры поштучно. Kolla и USCR по defaults пишут `/etc/sysctl.conf`. Списки ключей исследованных ролей различаются, но BPF/perf/memory-защита требует проверки мониторинга и workloads |
| `permissions_*` | Применять по согласованным путям. Не распространять автоматически на `/etc/kolla`, `/var/lib/containers`, volumes, `/var/lib/nova`, `/var/lib/libvirt`, сокеты и устройства. Часть путей хоста используется контейнерами через bind mounts |
| `fstab` | Проверять с фактическим layout и storage backend. Изменение `nosuid/nodev` на разделах `/var` и дочерних не следует переносить только на основании общего имени hardening |
| `grub` | Выбранные параметры возможны отдельно от deploy, с учётом требуемой перезагрузки хоста |
| `ntp` | Корпоративные адреса USCR требуют замены/согласования с инфраструктурой кластера |
| `audit` | Нужна адаптация AVC, хранения, доставки, источников пакетов и взаимодействия с firewalld; исходный профиль не подходит как есть |
| `disable_service_*` | Выбирать по назначению узла. Проверки DNS/rpcbind/NFS/LDAP могут пересекаться с нужными функциями или обнаруживать нестандартные для USCR процессы. Нельзя считать все найденные службы лишними |
| `additional_libvirtd` | Не включать как общую меру для compute. USCR выключает хостовый `libvirtd.service`; в Kolla может использоваться контейнер `nova_libvirt`. Это разные объекты управления, и наличие контейнера не делает blanket-политику корректной |
| Чеклисты Greenplum/Cloudera/SDP | Не переносить в профиль Kolla целиком: там есть отключение SELinux, удаление swap и настройки под другие нагрузки |

Важно различать host SSH и контейнерный SSH. В Nova есть отдельный контейнер `nova_ssh`, отдельная сгенерированная конфигурация и по defaults порт `8022`. Правка `/etc/ssh/sshd_config` хоста не равна правке этого контейнера. Главный непосредственный риск host SSH hardening — доступ Ansible и администратора, а не автоматическое изменение настроек `nova_ssh`. Nova defaults[^nova-defaults], контейнерный SSH config[^nova-ssh].

То же относится к libvirt и файловым правам: в Nova присутствуют privileged-контейнеры, bind mounts `/dev`, `/lib/modules`, volumes libvirt/nova. Поэтому ни вывод «всё изолировано контейнерами», ни вывод «любое хостовое изменение обязательно ломает контейнер» по исходникам не обоснован. Nova volumes и сервисы[^nova-defaults].

**5. Подход к интеграции**

Предлагаемый порядок проектирования, без выполнения каких-либо изменений:

1. Зафиксировать целевую ОС, inventory и effective globals; проверить версию установленной `openstack.kolla`, поскольку её baremetal-роль вызывается bootstrap и не вложена в архив. `requirements.yml` ссылается на ветку `stable/2025.1`, а не на конкретный commit.
2. Определить владельцев настроек: Kolla — SELinux-профили, контейнерные labels и host-firewall; отдельный адаптированный профиль — выбранные хостовые меры доступа, прав, ядра и аудита.
3. Подготовить хост с включённым SELinux targeted и подходящими bindings; применить только согласованные хостовые меры, сохраняющие доступ Ansible. Проверить, что последующий bootstrap не меняет требуемое исходное состояние.
4. Выполнить штатную последовательность Kolla с её управляемыми фазами permissive/firewalld. Не вставлять туда запуск всего USCR wrapper.
5. Для SELinux enforcing проверять не только `getenforce`, но и AVC и работу сервисов после перехода; для firewall — фактические OpenStack-потоки, а не только SSH.
6. Проверить повторный `reconfigure`: настройки не должны взаимно отменяться между Kolla и hardening-профилем.

По имеющимся исходникам можно подтвердить необходимость этой адаптации и перечисленные конфликты. Утверждать «совместимо и безопасно для вашего развёрнутого кластера» без effective configuration и проверки на узлах нельзя.

**Указатели на исходники**

Сноски содержат пути внутри исходных архивов. `uscr-production@290a25d1e36/` относится к архиву `uscr-production@290a25d1e36-v3.zip`; `kolla-ansible-pvs_1.0.0/` — к `kolla-ansible-pvs_1.0.0_23.09.zip`. Архивы и распакованные исходники в репозиторий документации не включены.

[^uscr-precheck-defaults]: `uscr-production@290a25d1e36/collections/ansible_collections/linuxadm/core/roles/basic_host_precheck/defaults/main.yml`.
[^uscr-precheck]: `uscr-production@290a25d1e36/collections/ansible_collections/linuxadm/core/roles/basic_host_precheck/tasks/main.yml`.
[^uscr-audit-rules]: `uscr-production@290a25d1e36/collections/ansible_collections/linuxadm/security/roles/compliance_audit/files/auditd_rules/secure7.rules`.
[^uscr-iptables]: `uscr-production@290a25d1e36/collections/ansible_collections/linuxadm/security/roles/compliance_audit/tasks/task_iptables.yml`.
[^selinux-install]: `kolla-ansible-pvs_1.0.0/ansible/roles/selinux-profiles/tasks/install.yml`.
[^selinux-prepare]: `kolla-ansible-pvs_1.0.0/ansible/roles/selinux-profiles/tasks/prepare.yml`.
[^selinux-finalize]: `kolla-ansible-pvs_1.0.0/ansible/roles/selinux-profiles/tasks/finalize.yml`.
[^selinux-enforce]: `kolla-ansible-pvs_1.0.0/ansible/roles/selinux-profiles/tasks/enforce.yml`.
[^selinux-rollback]: `kolla-ansible-pvs_1.0.0/ansible/roles/selinux-profiles/tasks/rollback_finish.yml`.
[^container-worker]: `kolla-ansible-pvs_1.0.0/ansible/module_utils/kolla_container_worker.py`.
[^all-vars]: `kolla-ansible-pvs_1.0.0/ansible/group_vars/all.yml`.
[^kolla-host]: `kolla-ansible-pvs_1.0.0/ansible/kolla-host.yml`.
[^commands]: `kolla-ansible-pvs_1.0.0/kolla_ansible/cli/commands.py`.
[^site]: `kolla-ansible-pvs_1.0.0/ansible/site.yml`.
[^firewalld-precheck]: `kolla-ansible-pvs_1.0.0/ansible/roles/prechecks/tasks/firewalld_checks.yml`.
[^host-firewall]: `kolla-ansible-pvs_1.0.0/ansible/host-firewall.yml`.
[^firewall-teardown]: `kolla-ansible-pvs_1.0.0/ansible/roles/host-firewall/tasks/teardown.yml`.
[^firewall-adapter]: `kolla-ansible-pvs_1.0.0/ansible/module_utils/kolla_firewall_firewalld.py`.
[^firewall-plan]: `kolla-ansible-pvs_1.0.0/ansible/module_utils/kolla_firewall_plan.py`.
[^firewall-admission]: `kolla-ansible-pvs_1.0.0/ansible/action_plugins/kolla_firewall_admission.py`.
[^firewall-verify]: `kolla-ansible-pvs_1.0.0/ansible/module_utils/kolla_firewall_verification.py`.
[^lb-precheck]: `kolla-ansible-pvs_1.0.0/ansible/roles/loadbalancer/tasks/precheck.yml`.
[^nova-defaults]: `kolla-ansible-pvs_1.0.0/ansible/roles/nova-cell/defaults/main.yml`.
[^nova-ssh]: `kolla-ansible-pvs_1.0.0/ansible/roles/nova-cell/templates/nova-ssh.json.j2`.
