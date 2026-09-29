**Роли USCR для hardening хостов Kolla-Ansible PVS**

Дата: 29 сентября 2026 года.

Основание: исходники `uscr-production@290a25d1e36-v3.zip` и `kolla-ansible-pvs_1.0.0_23.09.zip`. Приоритет реализации Kolla-Ansible установлен пользователем. Документ определяет выбор ролей; изменений в Ansible-код и на узлы не внесено.

**Вывод**

Kolla-Ansible остаётся владельцем настроек SELinux, контейнерных профилей, host firewall и порядка `bootstrap-servers → prechecks → deploy/reconfigure`. USCR применяется только как дополнительный профиль хостовой ОС и не должен отменять эти настройки.

Для базового списка выбраны **пять ролей USCR**, в целевых действиях которых по исследованным исходникам не обнаружено прямого конфликта с реализацией Kolla:

1. `linuxadm.security.compliance_password`
2. `linuxadm.security.compliance_pamenv`
3. `linuxadm.security.compliance_permissions_dir_profile`
4. `linuxadm.security.compliance_permissions_dir_security`
5. `linuxadm.security.compliance_permissions_dir_modules`

**Этот список действует после общей адаптации запуска USCR, описанной ниже.** Штатные точки входа этих ролей вызывают precheck, требующий SELinux `disabled`. Поэтому при включённом SELinux готовых к прямому запуску «как есть» ролей из этого списка нет. Адаптируется USCR; политика Kolla ради запуска USCR не ослабляется.

Здесь «без прямого конфликта» означает отсутствие в рассмотренных целевых действиях переопределения требований Kolla. Это результат статического сопоставления, а не подтверждение работоспособности на конкретных узлах. Версия внешней коллекции `openstack.kolla`, эффективные inventory/globals и фактические нестандартные ACL/владельцы на хостах не проверялись.

**Приоритет настроек**

| Область | Владелец и правило совмещения |
|---|---|
| SELinux, CIL-модули, booleans, container labels | Kolla: `selinux-profiles` и container worker. USCR не выключает SELinux и не меняет выбранный Kolla режим |
| Firewalld, `kolla-host-input`, watchdog/recovery | Kolla: `host-firewall`. USCR не останавливает firewalld, не заменяет правила и не добавляет независимый lifecycle iptables |
| Контейнерные конфигурации, сервисы, volumes, устройства и сокеты | Kolla. Общие USCR-проходы по правам не распространяются на эти объекты |
| Параметры ядра, необходимые OpenStack | При совпадении ключей применяется значение Kolla. Дополнительные параметры USCR рассматриваются отдельно |
| SSH/become для развёртывания | Сохраняются фактические пользователь, порт, ключи и sudo-права, используемые Kolla |
| Дополнительные хостовые меры | USCR, только в согласованной области и без отмены перечисленных требований |

По defaults форка `enable_selinux_profiles: "no"`, `selinux_profiles_mode: "permissive"`, `enable_pvs_firewalld: "no"`. Это defaults исходников, а не сведения о конфигурации работающего кластера. Defaults Kolla[^kolla-defaults].

**Что сохраняется из вывода о совместимости**

- USCR precheck требует `disabled`, тогда как включённые SELinux-профили Kolla требуют SELinux `enabled`, `targeted` и основную версию ОС 9. При deploy/reconfigure Kolla переводит хост в permissive, а в конце оставляет permissive или включает enforcing согласно настройке. USCR precheck[^uscr-precheck], Kolla install[^selinux-install], Kolla finalize[^selinux-finalize].
- USCR audit содержит `-a always,exclude -F msgtype=AVC`. Такой профиль исключает AVC из audit-потока и не подходит без переработки для сопровождения SELinux-профилей Kolla. Audit rules[^uscr-audit].
- В этом форке bootstrap устанавливает firewalld и останавливает/отключает его; multinode prechecks требуют неактивную и не enabled службу. Начало deploy/reconfigure останавливает firewalld; заключительная фаза при включённой функции запускает его и применяет политику. Внешний hardening не должен изменять этот порядок. Bootstrap[^kolla-bootstrap], prechecks[^firewall-precheck], site[^kolla-site], host-firewall[^host-firewall].
- Основной host-firewall пропускается на single-node; PRE Bootstrap устанавливает/останавливает firewalld на своей группе `all,!deployment` без отдельного single-node исключения.
- В автоматическом firewall-пути диагностические blockers очищаются и выполняется проверка только SSH. Успешное выполнение этого пути не доказывает доступность всех OpenStack-потоков. Приоритет Kolla сохраняется; это ограничение учитывается при проверке результата. Admission[^firewall-admission], SSH-only verification[^host-firewall].
- Финализация SELinux и firewall находится в конце deploy/reconfigure. При прерывании выполнения нужно проверять фактические состояния, а не предполагать, что enforcing и firewall уже восстановлены.

**Базовый список: роли без выявленного прямого конфликта целевых настроек**

| Роль USCR | Действие | Почему включена | Граница применения |
|---|---|---|---|
| `linuxadm.security.compliance_password` | Редактирует `/etc/login.defs`: `PASS_MAX_DAYS=80`, `PASS_MIN_DAYS=3`, `PASS_WARN_AGE=7`, `LOGIN_RETRIES=6`, параметры журналирования | Не меняет SSH-порт, правила sudo, SELinux, firewall, контейнерные конфигурации или сервисные пароли Kolla | Только локальная политика хоста. Не является массовым `chage` существующих пользователей и не распространяет политику на Keystone/контейнеры |
| `linuxadm.security.compliance_pamenv` | Устанавливает `LESSSECURE`, `SYSTEMD_PAGERSECURE`, `PAGER` и `SYSTEMD_PAGER` в `/etc/security/pam_env.conf` | Не заменяет PAM-стек `system-auth/password-auth`, не меняет методы аутентификации и lifecycle Kolla | Только ограничения pager в хостовом окружении PAM; не считать эту роль эквивалентом `compliance_pam` |
| `linuxadm.security.compliance_permissions_dir_profile` | Исправляет выявленные нарушения владельца/прав в содержимом `/etc/profile.d` | Не меняет содержимое профилей, контейнерные labels и firewall; в исследованном форке не обнаружено требований Kolla к непривилегированной записи или специальным ACL в этом каталоге | Только штатное содержимое каталога хоста; нестандартные ACL/владельцы проверяются до применения |
| `linuxadm.security.compliance_permissions_dir_security` | Исправляет выявленные нарушения владельца/прав в содержимом `/etc/security` | Не заменяет PAM-конфигурацию и её параметры; не управляет SELinux-политиками | Сохраняются требуемые более строгие права; нестандартные файлы, рассчитанные на особого владельца/ACL, не включаются автоматически |
| `linuxadm.security.compliance_permissions_dir_modules` | Исправляет выявленные нарушения владельца/прав в содержимом `/lib/modules` | Не удаляет модули ядра, не создаёт blacklist и не запрещает их загрузку. Kolla продолжает управлять загрузкой модулей для Nova/Neutron/OVS | Штатное дерево модулей с владельцем root; не менять содержимое модулей, доступность дерева и bind mounts контейнеров |

Источники: password defaults[^password-defaults], password apply[^password-action], pamenv defaults[^pamenv-defaults], pamenv apply[^pamenv-action], profile permissions[^permissions-profile], security permissions[^permissions-security], modules permissions[^permissions-modules], загрузка модулей Neutron[^neutron-host].

Три роли каталогов используют общий обработчик. Для объектов, отмеченных сканером, он выполняет `setfacl -b`, снимает специальные биты, убирает запись для others и устанавливает `root:root`. Он **не устанавливает всем файлам фиксированный режим 0775**: это верхняя граница проверки. Более строгие обычные rwx-биты не расширяются этими командами. Обработчик прав[^permissions-helper], сканер[^uscr-scanner].

Допуск этих трёх ролей предполагает отсутствие в целевых объектах необходимых нестандартных ACL, специальных битов и владельцев. При обнаружении такого объекта сохраняется требование целевой системы, а применение соответствующей роли откладывается или сужается. Права и ACL — отдельные от SELinux labels механизмы; отсутствие изменения labels не означает отсутствие влияния прав на доступ.

**Общая адаптация USCR, обязательная для базового списка**

1. **Исправить критерий SELinux в интеграционном запуске USCR.** Вместо требования `disabled` проверять совместимость с эффективной конфигурацией Kolla. Не вызывать `linuxadm.core.disable_selinux`. Сам по себе `check_selinux: 0` не является доказательством совместимости.
2. **Использовать параметры подключения Kolla.** Не переопределять пользователя, SSH-порт, ключи и become. Общая зависимость USCR `ansible_pipelining` записывает `Defaults !requiretty` в `/etc/sudoers.d/linuxadm_disable_requiretty`; этот побочный шаг следует исключить либо отдельно согласовать с действующей политикой sudo. Pipelining[^uscr-pipelining].
3. **Согласовать Python, ОС и коллекции.** В USCR defaults указан `/usr/libexec/platform-python`, а базовый precheck по умолчанию разрешает версии 7/8. Верхние USCR playbooks отдельно расширяют список до 7/8/9. При прямом вызове роли эти настройки необходимо передать явно для целевой поддерживаемой ОС. Совместимость Ansible-зависимостей проверяется в окружении форка, где host-firewall требует ansible-core 2.18.x. USCR precheck defaults[^uscr-precheck-defaults], пример точки входа[^password-entry].
4. **Вызывать только выбранные роли.** Не включать `var_compliance_start_all`, `var_compliance_start_permissions_all` или `var_compliance_start_disable_all_services`. Общий `compliance_core` wrapper выполняет дополнительные действия вне базового списка.
5. **Различать частные служебные задачи и полный wrapper.** Базовые роли используют конкретные `tasks_from` из `compliance_core` для каталогов, backup и исключений, а также сканирование выбранного модуля. Это допустимые технические зависимости после адаптации. Полное выполнение `compliance_core` и `compliance_check/tasks/main.yml` в базовый набор не входит: общий scan вызывает установку/перезапуск `linuxadm-autotest`. Частный scan[^specific-check], полный scan[^full-check].
6. **Применять отдельно от активного deploy/reconfigure.** Интеграционная адаптация не должна добавлять запуск USCR между фазами SELinux/firewall Kolla или изменять эти фазы.

Эти пункты — требования к будущей интеграции. В рамках подготовки документа адаптация кода не выполнялась.

**Роли, которые можно рассматривать только после дополнительных условий**

Следующий список не входит в базовый допуск «без выявленного прямого конфликта». Префикс всех ролей в таблице — `linuxadm.security.`.

| Роль | Что требуется проверить или адаптировать |
|---|---|
| `compliance_ssh` | Сохранить SSH-порт и доступ deploy-пользователя. Исходная роль ставит порт 22 и запрещает root. Учитывать перезапуск sshd |
| `compliance_pam` | Согласовать замену PAM-стека с фактической аутентификацией; для RedHat 9 шаблона в архиве нет, для SberLinux 9 есть |
| `compliance_profile` | Согласовать `TMOUT=900`, readonly-переменные истории/PROMPT_COMMAND и запись команд в syslog с эксплуатационными процедурами |
| `compliance_del_empty_password` | Проверить фактические локальные записи и способ входа deploy/сервисных пользователей; роль блокирует пароль через `passwd -l` |
| `compliance_one_uid_zero` | Проверить пользователей с UID 0 и последствия смены UID для процессов и файлов; не выполнять как автоматическую нормализацию идентификаторов |
| `compliance_empty_root_group` | Проверить, не используется ли дополнительное членство в root для доступа к устройствам, файлам или административных процедур |
| `compliance_disable_wifi` | Подтвердить, что управление и сервисные сети узла не используют Wi-Fi |
| `compliance_sysctl` | Согласовать каждый ключ, включая BPF/perf/memory-параметры; не изменять ключи, которыми управляет Kolla. Отсутствие пересечения имён не равно проверке приложений |
| `compliance_grub` | Согласовать параметры загрузки, пароль загрузчика и плановую перезагрузку хоста |
| `compliance_fstab` | Проверить layout, mount options, Podman graphroot, bind mounts и storage backends. Не назначать `nosuid/nodev` для `/var` и дочерних разделов без этой проверки |
| `compliance_ntp` | Заменить корпоративные NTP-источники USCR на согласованные источники кластера и исключить конкуренцию владельцев конфигурации |
| `compliance_permissions_simple` | Сократить список до согласованных путей. Полный профиль включает, в частности, `/usr/bin` и `/usr/sbin` с режимом 0555 |
| `compliance_permissions_home` | Проверить расположение ключей, рабочих каталогов, shared home и требуемые ACL пользователей администрирования |
| `compliance_permissions_builtin` | Проверить все затрагиваемые исполняемые файлы и ACL; Kolla также размещает на хосте собственные wrapper/helper-файлы |
| `compliance_permissions_wildcard` | Согласовать права для PAM, sudoers, systemd и логов; не применять общий проход без списка фактических объектов |
| `compliance_permissions_others` | Согласовать доступ сборщиков к boot/dmesg/ntp logs и дополнительный systemd unit, устанавливаемый ролью |
| `compliance_disable_service_autofs`, `compliance_disable_service_smb`, `compliance_disable_service_avahi`, `compliance_disable_service_mail`, `compliance_disable_service_cups` | Подтвердить ненужность службы для конкретной группы узлов и отсутствие зависимостей |
| `compliance_disable_service_telnet`, `compliance_disable_service_rlogin`, `compliance_disable_service_finger`, `compliance_disable_service_ftp` | Проверить, что отключаются именно обнаруженные штатные legacy-службы; не расширять действие на произвольные процессы или контейнеры |
| `compliance_disable_service_rpcbind`, `compliance_disable_service_dns`, `compliance_disable_service_ldap` | Проверить NFS/storage, DNS/DHCP и каталог пользователей. Эти функции могут быть частью рабочей инфраструктуры |

**Исключить из предлагаемого USCR-профиля**

| Роль/сценарий | Основание при приоритете Kolla |
|---|---|
| `linuxadm.core.disable_selinux` | Противоречит включённым SELinux-профилям Kolla |
| `linuxadm.security.compliance_audit` | Исходный профиль исключает AVC, использует своё хранение/доставку и изменяет rsyslog/SSH/iptables. Если аудит требуется, проектировать адаптацию отдельно |
| `linuxadm.security.audit_replace_collectors` | Заменяет адреса коллекторов исходной корпоративной схемы; в базовый профиль Kolla не относится |
| `linuxadm.security.compliance_permissions_rsyslog` | Кроме прав переписывает параметры rsyslog, перезапускает его и меняет членство zabbix в группе. Это отдельное изменение схемы журналирования |
| `linuxadm.security.compliance_sudo_wheel` | Исходная мера комментирует `%wheel` целиком; доступ развёртывания и действующая модель sudo имеют приоритет |
| `linuxadm.security.compliance_additional_libvirtd` | Управление libvirt определяется конфигурацией Kolla; отключение хостового сервиса не добавляется общей hardening-мерой |
| `linuxadm.security.compliance_additional_chaosteam` | Исправление ACL под конкретный внешний сценарий, не универсальное требование Kolla |
| Полный `linuxadm.security.compliance_core` и `security_compliance_core_wrapper.yml` | Дополнительная оркестрация, служебные изменения и возможность включить несовместимые группы; использовать выбранные роли и их необходимые частные зависимости |
| Полный `security_compliance_check.yml` как «read-only проверка» | Запускает дополнительные изменения через автотест; для базового набора нужна проверка выбранных мер без такого запуска |
| EDR/KESL, FreeIPA, прикладные `checklist_*`, миграции и дисковые операции | Отдельные изменения назначения и эксплуатации узлов; не включать как зависимости хостового hardening |

**Признаки успешного совмещения**

Для выбранного набора после адаптации должны сохраняться: новый вход Ansible с прежними параметрами и рабочим become; выбранные Kolla режим SELinux и контейнерные labels; состояние собственной firewall-политики; доступность сервисов; возможность повторного `reconfigure`. USCR-проверка не должна требовать отключения SELinux или отмены настроек Kolla.

Для базовых ролей прав дополнительно сверяется фактический список изменённых объектов: только согласованные файлы в трёх каталогах, без изменения содержимого, контейнерных конфигураций и labels. Проверка этих условий на узлах в данном анализе не выполнялась.

Подробное сопоставление поведения форка: [KOLLA_HARDENING_COMPATIBILITY.md](KOLLA_HARDENING_COMPATIBILITY.md). Общий разбор USCR: [ANALYSIS_HARDENING.md](ANALYSIS_HARDENING.md).

**Указатели на исходники**

Сноски содержат пути внутри исходных архивов. `uscr-production@290a25d1e36/` относится к архиву `uscr-production@290a25d1e36-v3.zip`; `kolla-ansible-pvs_1.0.0/` — к `kolla-ansible-pvs_1.0.0_23.09.zip`. Архивы и распакованные исходники в репозиторий документации не включены.

[^kolla-defaults]: `kolla-ansible-pvs_1.0.0/ansible/group_vars/all.yml`.
[^kolla-bootstrap]: `kolla-ansible-pvs_1.0.0/ansible/kolla-host.yml`.
[^kolla-site]: `kolla-ansible-pvs_1.0.0/ansible/site.yml`.
[^selinux-install]: `kolla-ansible-pvs_1.0.0/ansible/roles/selinux-profiles/tasks/install.yml`.
[^selinux-finalize]: `kolla-ansible-pvs_1.0.0/ansible/roles/selinux-profiles/tasks/finalize.yml`.
[^firewall-precheck]: `kolla-ansible-pvs_1.0.0/ansible/roles/prechecks/tasks/firewalld_checks.yml`.
[^host-firewall]: `kolla-ansible-pvs_1.0.0/ansible/host-firewall.yml`.
[^firewall-admission]: `kolla-ansible-pvs_1.0.0/ansible/action_plugins/kolla_firewall_admission.py`.
[^neutron-host]: `kolla-ansible-pvs_1.0.0/ansible/roles/neutron/tasks/config-host.yml`.
[^uscr-precheck]: `uscr-production@290a25d1e36/collections/ansible_collections/linuxadm/core/roles/basic_host_precheck/tasks/main.yml`.
[^uscr-precheck-defaults]: `uscr-production@290a25d1e36/collections/ansible_collections/linuxadm/core/roles/basic_host_precheck/defaults/main.yml`.
[^uscr-pipelining]: `uscr-production@290a25d1e36/collections/ansible_collections/linuxadm/core/roles/ansible_pipelining/tasks/main.yml`.
[^uscr-audit]: `uscr-production@290a25d1e36/collections/ansible_collections/linuxadm/security/roles/compliance_audit/files/auditd_rules/secure7.rules`.
[^password-defaults]: `uscr-production@290a25d1e36/collections/ansible_collections/linuxadm/security/roles/compliance_password/defaults/main.yml`.
[^password-action]: `uscr-production@290a25d1e36/collections/ansible_collections/linuxadm/security/roles/compliance_password/tasks/password_task_major_action.yml`.
[^password-entry]: `uscr-production@290a25d1e36/security_compliance_password.yml`.
[^pamenv-defaults]: `uscr-production@290a25d1e36/collections/ansible_collections/linuxadm/security/roles/compliance_pamenv/defaults/main.yml`.
[^pamenv-action]: `uscr-production@290a25d1e36/collections/ansible_collections/linuxadm/security/roles/compliance_pamenv/tasks/pamenv_task_major_action.yml`.
[^permissions-profile]: `uscr-production@290a25d1e36/collections/ansible_collections/linuxadm/security/roles/compliance_permissions_dir_profile/tasks/permissions_dir_profile_way_slow_track.yml`.
[^permissions-security]: `uscr-production@290a25d1e36/collections/ansible_collections/linuxadm/security/roles/compliance_permissions_dir_security/tasks/permissions_dir_security_way_slow_track.yml`.
[^permissions-modules]: `uscr-production@290a25d1e36/collections/ansible_collections/linuxadm/security/roles/compliance_permissions_dir_modules/tasks/permissions_dir_modules_way_slow_track.yml`.
[^permissions-helper]: `uscr-production@290a25d1e36/collections/ansible_collections/linuxadm/security/roles/compliance_permissions_common_tools_for_dir/templates/compliance_permissions_common_tools_for_dir___major_action.j2`.
[^uscr-scanner]: `uscr-production@290a25d1e36/collections/ansible_collections/linuxadm/security/roles/compliance_check/templates/compliance_check.j2`.
[^specific-check]: `uscr-production@290a25d1e36/collections/ansible_collections/linuxadm/security/roles/compliance_check/tasks/task_check_specific_module.yml`.
[^full-check]: `uscr-production@290a25d1e36/collections/ansible_collections/linuxadm/security/roles/compliance_check/tasks/main.yml`.
