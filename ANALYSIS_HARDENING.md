**Разбор архива `uscr-production@290a25d1e36-v3.zip`**

Дата анализа: 29 сентября 2026 года. Исходники распакованы в `uscr-production@290a25d1e36/` рядом с архивом. Выполнен статический анализ точек входа, ролей, переменных, шаблонов и встроенных скриптов. Подключения к серверам и выполнения Ansible не было. Работоспособность на конкретной ОС и фактическое соответствие требованиям этим анализом не подтверждаются.

**Краткий вывод.** Это корпоративный комплект администрирования Linux, внутри которого есть широкий профиль hardening всей ОС. Основной механизм — коллекция `linuxadm.security`, управляющая роль `compliance_core` и 36 выбираемых модулей: 15 основных, 12 для отключения служб и 9 для прав доступа. Дополнительно присутствуют EDR, Kaspersky, FreeIPA, подготовка ОС под приложения, миграции и операции с дисками. Эти дополнительные сценарии не являются автоматически частью общего hardening.

Охват системный: аутентификация, привилегии, SSH, загрузка, параметры ядра, файловые системы, права, журналирование и сетевые службы. При этом полнота защиты всей ОС, соответствие CIS/STIG или конкретному нормативному профилю не установлены. В коде реализован собственный набор проверок с внутренними номерами требований и исключениями. Управляющая роль[^core-main], перечень сценариев[^readme].

**Для каких ОС предназначен комплект**

Основная ориентация — RHEL и SberLinux. Предварительная проверка ищет в версии ядра маркеры `el`/`sl`; верхние `security_compliance_*.yml` разрешают основные версии `7 8 9`. Используются RPM/YUM, systemd, `/etc/redhat-release`, в defaults задан `/usr/libexec/platform-python`.

Однако допуск версии в precheck не равен полной поддержке дистрибутива. Для PAM в архиве есть только `pam_redhat_7.j2`, `pam_redhat_8.j2`, `pam_sberlinux_8.j2`, `pam_sberlinux_9.j2`. Имя шаблона строится из `ansible_distribution` и основной версии. Поэтому комплект PAM для RedHat 9, CentOS, Rocky или AlmaLinux в текущем виде не подтверждён: соответствующих шаблонов нет. Поддержка Debian/Ubuntu в исследованном compliance-контуре не обнаружена. Проверка ОС[^precheck], выбор PAM-шаблона[^pam-deploy].

Существенное ограничение: стандартный precheck включён с `check_selinux: 1` и, при наличии `sestatus`, требует результат `disabled`. Он отклоняет ОС с работающим SELinux. Это профиль для среды с отключённым SELinux. В комплекте есть и отдельная роль его отключения, вызываемая некоторыми прикладными чеклистами. Defaults precheck[^precheck-defaults], проверка SELinux[^precheck], отключение SELinux[^selinux].

**Что меняют 15 основных модулей**

| Модуль | Компонент ОС | Реализованное действие |
|---|---|---|
| `ssh` | OpenSSH Server; для версии 7 также клиент | Правит `/etc/ssh/sshd_config`, добавляет баннер, проверяет конфигурацию и перезапускает `sshd`. Порт 22, `PermitRootLogin no`, `PermitEmptyPasswords no`, `UsePAM yes`, `MaxAuthTries 6`, запрет TCP forwarding и tunnel. Для версии 7 задаёт Ciphers/MACs также в клиенте. |
| `pam` | PAM, локальная аутентификация и интеграция SSSD | Заменяет политики `system-auth` и `password-auth` через файлы `*-linuxadm` и симлинки. Учитывает SSSD, PSM и ASG; может устанавливать вспомогательные пакеты. |
| `pamenv` | Окружение PAM | Правит `/etc/security/pam_env.conf`: `LESSSECURE=1`, `SYSTEMD_PAGERSECURE=1`, выбор `less` для pager. |
| `password` | Параметры учётных записей | Правит `/etc/login.defs`: `PASS_MAX_DAYS 80`, `PASS_MIN_DAYS 3`, `PASS_WARN_AGE 7`, `LOGIN_RETRIES 6`, параметры журналирования. |
| `del_empty_password` | Локальные пароли | Ищет пустое поле пароля в `/etc/shadow` и выполняет `passwd -l`. Учётные записи не удаляет; это блокировка парольного входа. |
| `one_uid_zero` | Локальные UID | Для пользователей с UID 0, кроме `root`, подбирает другой UID и редактирует `/etc/passwd`. |
| `empty_root_group` | Группа `root` | Удаляет перечисленных дополнительных членов группы `root` через `gpasswd -d`. Не является универсальной переработкой всех primary GID. |
| `sudo_wheel` | Sudo | Комментирует активные правила `%wheel` в `/etc/sudoers` и `/etc/sudoers.d/*`, проверяя синтаксис. Не строит новую ролевую модель sudo. |
| `grub` | GRUB и параметры загрузки ядра | Настраивает пароль загрузчика; для версий 8/9 задаёт `audit=1`, `tsx=auto`, `slab_nomerge`; для 7 в списке параметров находится `tsx=auto`. Сообщает о необходимости перезагрузки, сам ОС не перезагружает. |
| `sysctl` | Защитные параметры ядра | Записывает выбранные параметры в `/etc/sysctl.conf` и применяет их в работающем ядре. Подробности ниже. |
| `fstab` | Опции монтирования XFS/ext4 | Редактирует `/etc/fstab`: `noatime`, `nodiratime`; `nosuid` для отдельных точек монтирования `/tmp`, `/var`, `/home` и их дочерних; `nodev` для точек, кроме `/`. Сообщает о необходимости перезагрузки. Разделы не создаёт. |
| `disable_wifi` | NetworkManager/Wi-Fi | При работающем NetworkManager выполняет `nmcli radio wifi off`. Это не универсальная блокировка драйверов Wi-Fi. |
| `ntp` | Chrony/NTP | Выбирает службу и корпоративные серверы времени по сегменту, правит конфигурацию, при необходимости устанавливает службу, перезапускает её. Для ntpd также меняет ограничения доступа. |
| `profile` | Интерактивные shell-сессии | Размещает скрипты в `/etc/profile.d`: `TMOUT=900`, расширенная история команд и отправка команд в syslog. |
| `audit` | auditd, rsyslog, частично SSH и iptables | Устанавливает/настраивает аудит, правила событий, пересылку в SOC, локальное временное хранилище; меняет журналирование SSH и перезапускает службы. Подробности ниже. |

Источники конкретных настроек: SSH[^ssh-defaults], PAM[^pam-template], password[^password], учётные записи и остальные роли[^security-roles].

**Пароли и PAM: что именно задаётся**

В исследованных PAM-шаблонах: минимальная длина 16; минимум одна цифра, одна заглавная, две строчные буквы и один специальный символ; `difok=3`; история 20 паролей; `pam_faillock` с `deny=6`, `unlock_time=1800`. Есть исключения/отдельные ветви для `tech-accounts`, доменных пользователей и корпоративных модулей аутентификации. Эти значения нельзя описывать как единую политику без исключений для всех пользователей. PAM RedHat 8[^pam-template].

Модуль `password` редактирует именно `login.defs`. В его задаче применения нет массового `chage` для существующих пользователей: утверждение «всем текущим пользователям выставляется срок пароля 80 дней» кодом не подтверждается. Парольная политика домена FreeIPA/AD также не равна локальному PAM-профилю. Применение login.defs[^password-action].

**Параметры ядра**

| Параметр | Значение профиля | Что ограничивает/включает |
|---|---|---|
| `kernel.dmesg_restrict` | `1` | Доступ непривилегированных пользователей к сообщениям ядра |
| `kernel.kptr_restrict` | `1` | Раскрытие указателей ядра |
| `kernel.randomize_va_space` | `2` | ASLR |
| `kernel.unprivileged_bpf_disabled` | `1`, версии 8/9 | Непривилегированный BPF |
| `vm.mmap_min_addr` | `4096` | Отображение нижней области адресного пространства |
| `fs.protected_symlinks` | `1` | Защита при работе с символическими ссылками |
| `fs.protected_hardlinks` | `1` | Защита при создании жёстких ссылок |
| `kernel.perf_event_paranoid` | `2` | Доступ к perf |
| `fs.protected_regular` | `1`, версии 8/9 | Дополнительные ограничения открытия обычных файлов |
| `fs.suid_dumpable` | `0` | Core dump привилегированных процессов |

В варианте 7 строки BPF и `protected_regular` закомментированы. При обнаружении маркера `fst` предусмотрено изменение `kptr_restrict` на 2, `perf_event_paranoid` на 3 и `protected_regular` на 2. Наличие этой ветви не доказывает соответствие всем требованиям ФСТЭК. Параметры 8[^sysctl-vars], параметры 7[^sysctl-vars7], ветка fst[^sysctl-fst].

Это небольшой набор защитных sysctl, а не полная настройка сетевого стека: в данном списке нет комплекса `net.ipv4.*`/`net.ipv6.*`.

**12 модулей отключения служб**

Отдельные модули предназначены для `autofs`, SMB/Samba, Avahi, почтовых служб, CUPS, Telnet, rlogin, Finger, rpcbind, FTP, DNS и LDAP. Они используют общие механизмы проверки зависимостей systemd, прослушиваемых портов и, для старых протоколов, xinetd.

Среди явно указанных целей — `autofs.service`, `smb.service`, `avahi-daemon`, CUPS, `rpcbind`, `vsftpd`, `dnsmasq`, `unbound`, `named`, `postfix`, `sendmail`, `exim`, `dovecot`, `cyrus-imapd`. Для LDAP список формируется отдельной задачей. Это отключение серверных служб, а не запрет DNS-запросов или LDAP-аутентификации как таковых.

Реализация не останавливает любой процесс по названию протокола: есть ограничения поддерживаемых служб и проверки. Например, rpcbind проверяет использование NFS; DNS проверяет локальный resolver; общий механизм может отказать при нестандартном процессе или связанных службах. Такие проверки уменьшают риск, но не подтверждают совместимость со всеми прикладными системами. Роли служб[^security-roles].

**9 модулей прав доступа**

| Модуль | Область |
|---|---|
| `permissions_simple` | Явный список системных файлов, каталогов и логов: passwd/group/shadow, sudoers, sshd_config, cron, `/tmp`, `/var/tmp` и другие |
| `permissions_home` | Домашние каталоги, выявленные проверкой; устанавливает `0700`, убирает расширенные ACL и специальные биты |
| `permissions_dir_modules` | Содержимое `/lib/modules` |
| `permissions_dir_profile` | Содержимое `/etc/profile.d` |
| `permissions_dir_security` | Содержимое `/etc/security` |
| `permissions_builtin` | Исполняемые файлы в системных bin/sbin и `/usr/libexec`; убирает возможность записи непривилегированными пользователями и расширенные ACL |
| `permissions_rsyslog` | Права, связанные с конфигурацией rsyslog и создаваемыми логами |
| `permissions_wildcard` | Файлы в `/var/log/sssd`, `/var/log/sa`, `/var/log/rhsm`, `/etc/skel`, `/etc/pam.d`, `/etc/rc.d`, `/etc/sudoers.d`, `/usr/lib/systemd/system` |
| `permissions_others` | Дополнительные группы файлов, включая boot/dmesg/ntp logs |

Примеры заданных режимов: `/etc/shadow` и `/etc/gshadow` — `0400`, `/etc/sudoers` — `0440`, `sshd_config` — `0600`, `/tmp` и `/var/tmp` — `1777`, `/usr/bin` и `/usr/sbin` — `0555`. Операции ограничены целевыми списками и результатами собственного сканера. Это не сплошная проверка всех файлов всех файловых систем. Список обычных прав[^permissions], wildcard[^permissions-wildcard], исправление home[^permissions-home], исправление бинарных файлов[^permissions-builtin].

**Аудит устроен с расчётом на внешний SOC**

Роль разворачивает правила auditd для запуска команд, изменения пользователей и групп, sudo/PAM/SSH, systemd, cron, сетевых настроек, mount/umount, ptrace и других событий. В правилах также есть исключения событий/команд и ограничение частоты: это отфильтрованный поток аудита. Правила[^audit-rules].

Конкретная схема хранения и передачи:

- `/var/log/audit_log_tmpfs` монтируется как tmpfs размером 25 МБ; запись добавляется в `/etc/fstab`.
- `auditd.conf` получает `log_file=/var/log/audit_log_tmpfs/audit.log`, `max_log_file=5`, `num_logs=2`, ротацию; действия на нехватку места/ошибки диска настроены как `IGNORE`.
- rsyslog читает файл через imfile и отправляет аудит, `local0` и `authpriv` на выбранный SOC-коллектор по UDP; предусмотрен rate limit.
- Для SSH задаётся `LogLevel DEBUG` и `SyslogFacility AUTHPRIV`.
- При заданных условиях добавляется разрешающее правило OUTPUT в iptables для отправки на коллектор.
- Запускается проверка исходящего потока через tcpdump. Такая проверка не доказывает, что SOC принял и сохранил события.

Следствие выбранной схемы: указанный локальный audit log находится в памяти и не переживает перезагрузку. В шаблоне пересылки нет TCP/TLS. Долговременное хранение и защищённость доставки должны оцениваться отдельно для целевой инфраструктуры; архив не подтверждает их фактическое состояние. Развёртывание аудита[^audit-deploy], rsyslog[^audit-rsyslog], iptables[^audit-iptables].

**Как выбирается объём изменений**

Общий вход — `security_compliance_core_wrapper.yml`, целевая inventory-группа — `compliance`.

| Флаг | Что выбирает |
|---|---|
| `var_compliance_start_all` | 15 основных модулей |
| `var_compliance_start_disable_all_services` | 12 модулей отключения служб |
| `var_compliance_start_permissions_all` | 9 модулей прав |
| `var_compliance_start_<module>` | Отдельный модуль |
| `var_compliance_start_scan` | Полное сканирование своим скриптом |

По defaults эти флаги выключены. `start_all` не включает две другие группы. Сам wrapper при этом выполняет служебные операции: precheck, каталоги, lock/logging, работу с автотестом и другие задачи. Поэтому «все флаги false» не означает строгое отсутствие изменений на хосте. Defaults[^core-defaults], порядок выполнения[^core-main].

Самостоятельные `security_compliance_ssh.yml`, `..._pam.yml` и другие сценарии импортируют конкретную роль; в них передаётся `var_compliance_skip_check_sh: true`. Это позволяет переходить к применению без предварительного решения общего сканера «есть ли нарушение». Внутренние проверки и условия самой роли сохраняются. Пример самостоятельного входа SSH[^ssh-entry].

Есть исключения по номерам требований через `protection_list`/`var_compliance_bypass_list`, журналы и резервные копии в `/etc/linuxadm/compliance`, индивидуальные сценарии rollback. Для SSH/PAM предусмотрен фоновый отложенный откат и проверка восстановления подключения. Это механизмы восстановления отдельных изменений, не транзакционный откат всей ОС. В `compliance_core` для audit нет аналогичного rollback-флага. Исключения[^protection], SSH-откат после проверки соединения[^ssh-rollback].

`security_compliance_check.yml` не является строго read-only: до сканирования вызывается задача, выполняющая `yum install linuxadm-autotest`, `systemctl restart autotest.service`, а также проверку/исправление RPM database; создаются служебные файлы. Успешный Ansible recap также не равен отсутствию нарушений: сканер запускается с `failed_when: false`, а wrapper прямо предлагает отдельную проверку после применения. Сканирование[^check], побочные операции автотеста[^autotest].

**Что ещё находится в архиве**

| Группа | Назначение и связь с hardening |
|---|---|
| `security_edr_wrapper.yml` | Установка/запуск/остановка/проверка EDR-агента; отдельный механизм от `compliance_core` |
| `security_kesl_wrapper.yml`, `security_kesl_trace_collect.yml` | Kaspersky Endpoint Security for Linux, агент управления, статус и сбор диагностики |
| `ipa_client_os_v2.yml`, `ipa_sssd_tmpfs.yml` | Настройки клиентской интеграции FreeIPA и SSSD, перенос кэша SSSD в tmpfs |
| `checklist_*` | Подготовка ОС под Greenplum, SDP/Ozone и Cloudera: пакеты, limits/sysctl, каталоги, диски, swap/THP/NUMA, сертификаты, DNS и другие прикладные требования |
| `core_*` | Отдельные операции обслуживания/производительности: RPM database, NUMA/THP, swap, CPU governor, NetworkManager timeout, sysstat |
| `migration_pes_*`, `multipath_*`, `hotfix*` | Миграции, дисковые операции и точечные исправления |
| `docs/` и часть каталогов `checklist/roles/` | Документация для Oracle, PostgreSQL/Pangolin, Kafka, ELK, IBM MQ, серверов приложений и других продуктов; наличие каталога не всегда означает реализованную Ansible-роль |

Чеклисты приложений могут менять ОС в интересах совместимости и производительности. Например, Greenplum и Tengri Cloudera вызывают `disable_selinux`; часть SDP-сценариев добавляет исключение hardening для `noatime`. Поэтому применение всех файлов архива подряд не образует единый согласованный профиль безопасности. Greenplum[^greenplum], Cloudera[^cloudera], SDP[^sdp].

**Границы покрытия и существенные особенности**

1. Общий hardening ОС реализован широко, но отдельного законченного комплекса SELinux/AppArmor, firewall с политикой deny-by-default, полного сетевого sysctl-профиля, установки всех security updates, шифрования дисков и контроля целостности наподобие AIDE в исследованном compliance-пути не обнаружено.
2. Профиль SSH оставляет `X11Forwarding yes`. Явного общего запрета `PasswordAuthentication` в целевом списке SSH нет. Название hardening не означает автоматически запрет всех необязательных возможностей.
3. Модуль `fstab` не задаёт `noexec` и не создаёт отсутствующие отдельные `/tmp`, `/var` или `/home` разделы. Изменение fstab само по себе не подтверждает активные mount options.
4. Модули доступа реально меняют возможность администрирования: запрет root SSH, порт 22, удаление `%wheel`, новые UID и ACL. Применимость зависит от существующего способа входа и требований приложений.
5. Есть отдельная опция `var_compliance_start_additional_libvirtd`, останавливающая и отключающая `libvirtd`. По умолчанию она выключена и не входит в 36 перечисленных модулей. Для узла виртуализации это существенное изменение назначения службы. Действие libvirtd[^libvirtd].
6. Настройки SOC, NTP, корпоративных репозиториев, EDR/Kaspersky и интеграций привязаны к исходной инфраструктуре. Для другой среды требуется определить её адреса, источники пакетов, исключения и поддержку ОС.

Практический ответ на исходный вопрос: архив содержит **hardening общесистемных компонентов Linux с возможностью применения общего профиля к серверу**, а также отдельные сценарии под прикладные платформы. Под «для всей ОС» здесь следует понимать широту системного охвата; абсолютная полнота защиты и безопасная применимость на любом сервере из этого не следуют.

**Указатели на исходники**

Сноски содержат пути внутри исходных архивов. `uscr-production@290a25d1e36/` относится к архиву `uscr-production@290a25d1e36-v3.zip`. Архивы и распакованные исходники в репозиторий документации не включены.

[^readme]: `uscr-production@290a25d1e36/README.txt`.
[^security-roles]: `uscr-production@290a25d1e36/collections/ansible_collections/linuxadm/security/roles/`.
[^core-main]: `uscr-production@290a25d1e36/collections/ansible_collections/linuxadm/security/roles/compliance_core/tasks/main.yml`.
[^core-defaults]: `uscr-production@290a25d1e36/collections/ansible_collections/linuxadm/security/roles/compliance_core/defaults/main.yml`.
[^precheck]: `uscr-production@290a25d1e36/collections/ansible_collections/linuxadm/core/roles/basic_host_precheck/tasks/main.yml`.
[^precheck-defaults]: `uscr-production@290a25d1e36/collections/ansible_collections/linuxadm/core/roles/basic_host_precheck/defaults/main.yml`.
[^pam-deploy]: `uscr-production@290a25d1e36/collections/ansible_collections/linuxadm/security/roles/compliance_pam/tasks/pam_way_slow_track.yml`.
[^pam-template]: `uscr-production@290a25d1e36/collections/ansible_collections/linuxadm/security/roles/compliance_pam/templates/pam_redhat_8.j2`.
[^selinux]: `uscr-production@290a25d1e36/collections/ansible_collections/linuxadm/core/roles/disable_selinux/tasks/main.yml`.
[^ssh-defaults]: `uscr-production@290a25d1e36/collections/ansible_collections/linuxadm/security/roles/compliance_ssh/defaults/main.yml`.
[^ssh-entry]: `uscr-production@290a25d1e36/security_compliance_ssh.yml`.
[^password]: `uscr-production@290a25d1e36/collections/ansible_collections/linuxadm/security/roles/compliance_password/defaults/main.yml`.
[^password-action]: `uscr-production@290a25d1e36/collections/ansible_collections/linuxadm/security/roles/compliance_password/tasks/password_task_major_action.yml`.
[^sysctl-vars]: `uscr-production@290a25d1e36/collections/ansible_collections/linuxadm/security/roles/compliance_sysctl/vars/8.yml`.
[^sysctl-vars7]: `uscr-production@290a25d1e36/collections/ansible_collections/linuxadm/security/roles/compliance_sysctl/vars/7.yml`.
[^sysctl-fst]: `uscr-production@290a25d1e36/collections/ansible_collections/linuxadm/security/roles/compliance_sysctl/tasks/sysctl_task_fst_rewrite_vars.yml`.
[^permissions]: `uscr-production@290a25d1e36/collections/ansible_collections/linuxadm/security/roles/compliance_permissions_simple/defaults/main.yml`.
[^permissions-wildcard]: `uscr-production@290a25d1e36/collections/ansible_collections/linuxadm/security/roles/compliance_permissions_wildcard/defaults/main.yml`.
[^permissions-home]: `uscr-production@290a25d1e36/collections/ansible_collections/linuxadm/security/roles/compliance_permissions_home/templates/permissions_home_major_action.j2`.
[^permissions-builtin]: `uscr-production@290a25d1e36/collections/ansible_collections/linuxadm/security/roles/compliance_permissions_builtin/templates/permissions_builtin_major_action.j2`.
[^audit-rules]: `uscr-production@290a25d1e36/collections/ansible_collections/linuxadm/security/roles/compliance_audit/files/auditd_rules/secure7.rules`.
[^audit-deploy]: `uscr-production@290a25d1e36/collections/ansible_collections/linuxadm/security/roles/compliance_audit/tasks/task_deploy_long.yml`.
[^audit-rsyslog]: `uscr-production@290a25d1e36/collections/ansible_collections/linuxadm/security/roles/compliance_audit/templates/rsyslog/10-auditd-linuxadm.j2`.
[^audit-iptables]: `uscr-production@290a25d1e36/collections/ansible_collections/linuxadm/security/roles/compliance_audit/tasks/task_iptables.yml`.
[^protection]: `uscr-production@290a25d1e36/collections/ansible_collections/linuxadm/security/roles/compliance_core/tasks/set_protection.yml`.
[^ssh-rollback]: `uscr-production@290a25d1e36/collections/ansible_collections/linuxadm/security/roles/compliance_ssh/tasks/ssh_task_rollback_background_end.yml`.
[^check]: `uscr-production@290a25d1e36/collections/ansible_collections/linuxadm/security/roles/compliance_check/tasks/main.yml`.
[^autotest]: `uscr-production@290a25d1e36/collections/ansible_collections/linuxadm/security/roles/compliance_core/tasks/core_task_update_and_run_autotest.yml`.
[^greenplum]: `uscr-production@290a25d1e36/collections/ansible_collections/linuxadm/checklist/roles/cap_greenplum/tasks/main.yml`.
[^cloudera]: `uscr-production@290a25d1e36/collections/ansible_collections/linuxadm/checklist/roles/tengri_cloudera/tasks/main.yml`.
[^sdp]: `uscr-production@290a25d1e36/collections/ansible_collections/linuxadm/checklist/roles/cap_sdp/tasks/main.yml`.
[^libvirtd]: `uscr-production@290a25d1e36/collections/ansible_collections/linuxadm/security/roles/compliance_additional_libvirtd/tasks/stop_libvirtd.yml`.
