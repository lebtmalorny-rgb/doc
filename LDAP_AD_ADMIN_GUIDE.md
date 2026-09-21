# Интеграция OpenStack с Active Directory через LDAP: руководство администратора

> Пути к исходникам указаны внутри архивов соответствующей версии; состав и коммиты см. в [README](README.md). В репозитории публикуется только Markdown.

## 1. Краткая справка: от общего к частному

**OpenStack использует Active Directory как внешний источник пользователей и групп.** Keystone проверяет пароль через LDAP bind; проекты и назначения ролей остаются в OpenStack. Пользователь входит в Horizon под своей учётной записью AD, выбирая соответствующий домен Keystone. Изменение паролей и управление учётными записями AD выполняются средствами каталога. [Архитектура Keystone](https://docs.openstack.org/keystone/2025.1/admin/configuration.html#integrate-identity-with-ldap).

**В исследованной ветке Kolla-Ansible интеграция уже автоматизирована.** Параметр `ldap_engine_enabled: "yes"` создаёт конфигурацию LDAP-домена Keystone, включает выбор домена в Horizon и назначает двум группам AD роли в проекте. Он также включает LDAP в развёрнутой Grafana, а при включённом аудите безопасности — в OpenSearch. Это расширение данной ветки, а не универсальный набор параметров любой установки Kolla-Ansible.

**Основной вариант подключения в этом документе — LDAPS, TCP/636.** Локальный домен `Default` сохраняется для служебных пользователей и аварийного администратора. LDAP-домен по умолчанию называется `LDAP`, а проект для автоматического назначения ролей — `region` в домене `Default`.

| Компонент | Что делает интеграция |
|---|---|
| AD | Хранит пользователей, пароли, группы и членство |
| Keystone | Аутентифицирует пользователей AD; хранит назначения ролей в SQL |
| Horizon | Передаёт логин, пароль и выбранный домен в Keystone |
| Grafana | Подключается к AD самостоятельно; указанной группе назначает `Admin` организации |
| OpenSearch | Подключается к AD самостоятельно; указанной группе назначает `all_access` |

Сетевые потоки: `Horizon/CLI → Keystone → AD`; отдельно `Grafana → AD` и `OpenSearch → AD`. Браузеру пользователя прямой доступ к AD не нужен. Подробности фильтрации приведены в [руководстве по firewall](FIREWALL_ADMIN_GUIDE.md).

**Граница проверки:** документ составлен по исходникам архивов от 21.09.2026. Подключение к действующему AD, конфигурация контейнеров и вход пользователей на стенде не проверялись. Команды ниже — инструкция для администратора; при подготовке документа они на инфраструктуре не выполнялись.

## 2. Область применимости и исходные значения

Основной источник — `kolla-ansible-pvs_1.0.0_21.09zip.zip`, комментарий ZIP содержит коммит `365af98421ff35db2e9ca5ee605723a1bcc8e756`. Коллекция `openstack.kolla` в `requirements.yml` привязана к `stable/2025.1`; это не доказывает версию запущенных образов: `openstack_release` в исследованном `group_vars/all.yml` равен `latest`.

| Параметр | Значение в исходниках | Что учитывать |
|---|---|---|
| `ldap_engine_enabled` | `no` | Интеграция включается явно |
| `ldap_engine` | `AD` | В исследованной логике нет выбора разных шаблонов по этому значению; реальные параметры задают атрибуты ниже |
| `ldap_url` | `ldap://…:389` | Исходный пример не защищён TLS; заменить на согласованный LDAPS endpoint |
| `ldap_domain_name` | `LDAP` | Имя домена Keystone, не DNS-домен AD |
| `keystone_admin_project` | `region` | Не подставлять автоматически `admin` из upstream-примеров |
| `default_project_domain_name` | `Default` | Домен проекта отличается от домена пользователей AD |
| `node_custom_config` | `/etc/kolla/config` | Каталог исходных переопределений на deployment-узле |
| `node_config_directory` | `/etc/kolla` | Сгенерированные конфигурации на узлах сервисов |
| `kolla_container_engine` | `podman` | Для установки с Docker адаптировать команды осмотра контейнеров |
| `kolla_base_distro` | `sberlinux` | Фактический путь CA bundle проверить в образе |

Источники: общие переменные (`kolla-ansible-pvs_1.0.0/ansible/group_vars/all.yml`), параметры Keystone (`kolla-ansible-pvs_1.0.0/ansible/roles/keystone/defaults/main.yml`), зависимость коллекции (`kolla-ansible-pvs_1.0.0/requirements.yml`).

### 2.1. Где задаются параметры: globals, all.yml и отдельные конфиги

Под «alls» далее понимается файл **`ansible/group_vars/all.yml`** в исходниках Kolla-Ansible. Это базовые значения поставки. Для настройки конкретной установки переопределять их в `/etc/kolla/globals.yml` или в `/etc/kolla/globals.d/*.yml`; редактирование `all.yml` относится к сопровождению самой ветки.

| Где | Что относится к LDAP/AD | Действие администратора |
|---|---|---|
| `ansible/group_vars/all.yml` | Defaults `ldap_engine_enabled`, `ldap_url`, DN, имена групп, общие пути | Сверять исходные значения; параметры площадки задавать в globals |
| `ansible/roles/keystone/defaults/main.yml` | LDAP-атрибуты, фильтры, область поиска, настройки групп | Поддерживаемые переменные переопределять в globals |
| `/etc/kolla/globals.yml` или `globals.d/ldap.yml` | Включение AD, URL, DN, группы, фильтры, выбор доменов Horizon, копирование CA | Основное место настройки; пример в разделе 4.2 |
| `/etc/kolla/passwords.yml` | `ldap_password` | Хранить действующий bind-пароль; не дублировать в globals |
| `/etc/kolla/certificates/ca/*.crt` | Сертификаты доверенных CA, когда используется файловый источник | Подготовить цепочку доверия; при Vault использовать предусмотренный веткой источник |
| `/etc/kolla/config/keystone.conf` | Дополнительные параметры основного Keystone, участвующие в merge | Не рассчитывать на наследование `[ldap]` отдельным доменом |
| `/etc/kolla/config/keystone/keystone.conf` и `keystone/domains/keystone.<DOMAIN>.conf` | Результат генерации LDAP-коннектора на deployment-узле | Роль перезаписывает; не использовать как постоянное место ручных правок |
| Шаблоны роли / `opensearch_security_audit_config` | Настройки, которые коннектор не выводит в отдельные переменные: например, дополнительные параметры доменного TLS или полная security-конфигурация OpenSearch | Требуется отдельное сопровождение шаблона/полного конфига с проверкой merge; это не произвольный ключ в globals |
| `/etc/kolla/<service>/…` на сервисном узле, файлы внутри контейнера | Итоговая конфигурация | Проверять результат; изменения здесь не являются источником для следующего запуска Kolla |

CLI этой ветки передаёт `globals.yml`, затем `passwords.yml`, затем файлы `globals.d` по алфавиту, затем пользовательские `-e`. Более позднее определение одной переменной имеет приоритет; не хранить противоречивые значения в нескольких местах. Путь `/etc/kolla` может быть изменён через `--configdir`; пути выше соответствуют defaults. Загрузка переменных (`kolla-ansible-pvs_1.0.0/kolla_ansible/ansible.py`).

## 3. Что подготовить до изменения OpenStack

1. FQDN и порт LDAPS: один контроллер домена или согласованный балансируемый адрес. Шаблоны Grafana/OpenSearch разбирают одну строку `scheme://host:port`; список серверов через запятую и IPv6 URI нельзя считать поддержанными общим коннектором.
2. Служебную учётную запись для bind с правом чтения нужных пользователей, групп и членства. Административные права в AD для чтения каталога не требуются. Пароль должен быть действующим; порядок его ротации согласуется заранее.
3. Точные `user_tree_dn` и `group_tree_dn`, включая OU/CN. Пользователи и группы должны попадать в выбранную область поиска.
4. Группы для пользователей виртуализации и администраторов виртуализации. При использовании Grafana/OpenSearch — отдельные административные группы этих сервисов. Роль Kolla не создаёт группы в AD.
5. Тестового пользователя с прямым членством в пользовательской группе; отдельно — тест для административного доступа и вложенного членства, если оно используется.
6. Цепочку доверия CA контроллера домена, рабочее разрешение DNS и корректное время на узлах. Сертификат LDAPS должен подходить для Server Authentication и имени сервера, указанного в URL. [Требования Microsoft к LDAPS](https://learn.microsoft.com/en-us/windows-server/identity/ad-ds/configure-ldap-signing-certificates).
7. Рабочий вход локального администратора `Default`, резервные копии конфигурации и окно для перезапуска затронутых сервисов.

| Источник | Назначение | Доступ |
|---|---|---|
| Все узлы Keystone | Согласованные DC / LDAP-балансировщик | TCP/636 |
| Узлы Grafana и OpenSearch, если сервисы развёрнуты | Тот же endpoint AD | TCP/636 |
| Узлы-клиенты | Корпоративные DNS | UDP/53 и TCP/53 |
| Узлы, которым нужна синхронизация | Серверы времени | По принятой схеме, обычно UDP/123 |

Открывать входящий TCP/636 на всех узлах OpenStack не требуется: они являются LDAP-клиентами. TCP/389 нужен только при отдельно реализованном StartTLS; TCP/3269 — только при сознательном выборе Global Catalog. Присоединение Linux-узлов к домену, Kerberos/88, SMB/445 и RPC AD не являются частью описанного LDAP bind-сценария.

## 4. Настройка deployment-узла

### 4.1. Сохранить существующую конфигурацию

До редактирования сохранить `globals.yml`, `passwords.yml`, используемые `globals.d/*.yml` и каталог `config` в защищённую резервную копию. В ней будут секреты. Проверить фактический inventory, выбранную конфигурационную директорию и установленную версию Kolla-Ansible: использовать эту ветку, а не произвольную upstream-версию.

**Особенность ветки:** при включённом коннекторе роль заново записывает на deployment-узле:

- `/etc/kolla/config/keystone/keystone.conf`;
- `/etc/kolla/config/keystone/domains/keystone.<ldap_domain_name>.conf`.

Ручные изменения этих двух файлов будут потеряны при следующем запуске генерации. Общие дополнительные настройки Keystone можно хранить в `/etc/kolla/config/keystone.conf`, который участвует в merge, но проверять приоритет последующих файлов. **Настройки `[ldap]` для отдельного домена нельзя переносить туда в расчёте на наследование:** в upstream Keystone 2025.1 доменный драйвер загружает отдельный файл в новый объект конфигурации. Задачи Kolla (`kolla-ansible-pvs_1.0.0/ansible/roles/keystone/tasks/config.yml`), [загрузка доменных драйверов Keystone](https://raw.githubusercontent.com/openstack/keystone/stable/2025.1/keystone/identity/core.py).

### 4.2. Задать параметры в `/etc/kolla/globals.yml`

Ниже — пример для условной организации `example.org`. Заменить URL, DN и группы на реальные; существующие настройки других сервисов сохранить.

```yaml
ldap_engine_enabled: "yes"
ldap_engine: "AD"
ldap_url: "ldaps://dc01.example.org:636"
ldap_user: "svc-openstack@example.org"
ldap_suffix: "DC=example,DC=org"
ldap_user_tree_dn: "OU=People,DC=example,DC=org"
ldap_group_tree_dn: "OU=OpenStack,OU=Groups,DC=example,DC=org"
ldap_domain_name: "LDAP"

ldap_group_virt_admin: "os-virtualization-admins"
ldap_group_virt_user: "os-virtualization-users"
ldap_group_grafana_admin: "os-monitoring-admins"
ldap_group_opensearch_admin: "os-security-admins"

kolla_copy_ca_into_containers: "yes"

# Ключ — передаваемое Horizon имя домена, значение — подпись в списке.
horizon_keystone_domain_choices:
  Default: "Default"
  LDAP: "Active Directory"
```

`horizon_keystone_multidomain` уже вычисляется из `ldap_engine_enabled`. Явное старое переопределение `horizon_keystone_multidomain: "no"` следует убрать или изменить. В выпадающем списке должен остаться локальный `Default`.

Параметры, которые встроенный доменный шаблон поддерживает непосредственно:

| Параметр | По умолчанию | Смысл |
|---|---|---|
| `ldap_query_scope` | `sub` | Поиск во всём поддереве |
| `ldap_page_size` | `1000` | Постраничное получение результатов |
| `ldap_chase_referrals` | `False` | Переходы по referrals отключены |
| `ldap_user_objectclass` | `person` | Класс объекта пользователя |
| `ldap_user_filter` | `(!(objectClass=computer))` | Исключаются компьютеры; это не ограничение одной группой |
| `ldap_user_id_attribute` / `ldap_user_name_attribute` | `sAMAccountName` / `sAMAccountName` | Идентификатор и логин пользователя |
| `ldap_user_mail_attribute` | `mail` | Адрес электронной почты |
| `ldap_user_enabled_attribute` | `userAccountControl` | Проверка отключённой учётной записи AD |
| `ldap_user_enabled_mask` / `ldap_user_enabled_default` / `ldap_user_enabled_invert` | `2` / `512` / `false` | Параметры обработки статуса |
| `ldap_group_objectclass` | `group` | Класс группы AD |
| `ldap_group_id_attribute` / `ldap_group_name_attribute` | `sAMAccountName` / `cn` | ID и имя группы Keystone |
| `ldap_group_member_attribute` | `member` | Атрибут членства |
| `ldap_group_ad_nesting` | `true` | Обработка вложенных групп в Keystone |

Для автоматического поиска групп в Keystone задавать их имена по `cn`. При стандартном шаблоне Grafana административная группа должна находиться **непосредственно** в `ldap_group_tree_dn`: её DN собирается как `CN=<ldap_group_grafana_admin>,<ldap_group_tree_dn>`. Выбор общего родительского OU, под которым группа лежит ещё на один уровень глубже, здесь недостаточен.

Изменение `sAMAccountName` при таком выборе ID может изменить представление пользователя в Keystone. После начала эксплуатации смена ID-атрибутов и переименование домена требуют отдельного плана; это не безобидная настройка отображения.

### 4.3. Указать bind-пароль

В существующем `/etc/kolla/passwords.yml` заполнить ключ:

```yaml
ldap_password: "REPLACE_WITH_EXISTING_AD_BIND_PASSWORD"
```

Это пароль уже созданной учётной записи AD. Генератор паролей Kolla не меняет пароль в каталоге. Не передавать секрет через `-e ldap_password=...` в командной строке. Ограничить доступ к исходным файлам, резервным копиям и журналам Ansible; не использовать `--diff` для публикации конфигурации LDAP.

Шаблоны напрямую вставляют значение в INI/TOML/YAML. Для паролей с кавычками, переводами строк или синтаксисом Jinja необходимо проверить корректность сгенерированных файлов; универсального экранирования в этих шаблонах нет.

Если уже используется `enable_config_vault`, сохранить действующий механизм ссылок на секреты и разрешения внутри образов. Полный путь разрешения LDAP-секрета нельзя доказать одним архивом Kolla-Ansible: исходники контейнерного механизма материализации в набор архивов не входят. Не отключать Vault ради этого примера.

### 4.4. Настроить доверие к CA

В режиме локальных файлов CA разместить корневой и, при необходимости, промежуточные сертификаты AD в `/etc/kolla/certificates/ca/*.crt`; один PEM-сертификат на файл. Не заменять имеющиеся CA OpenStack и не копировать закрытый ключ контроллера домена. Роль `service-cert-copy` переносит CA в конфигурации сервисов; контейнер получает их в `/var/lib/kolla/share/ca-certificates`. При старте Kolla должен добавить их в доверенное хранилище. Механизм роли (`kolla-ansible-pvs_1.0.0/ansible/roles/service-cert-copy/tasks/main.yml`), [Kolla: CA в контейнерах](https://docs.openstack.org/kolla-ansible/2025.1/admin/tls.html#adding-ca-certificates-to-the-service-containers).

При `enable_vault_file_sources: true` эта ветка использует другую ветвь задач — `vault_extra_ca_files`. Локальный каталог `ca/` тогда не является достаточной настройкой. Добавить CA AD в уже принятый источник сертификатов и проверить материализацию в каждом LDAP-клиенте.

Встроенный `keystone-ldap-domain.conf.j2` **не выводит** `use_tls`, `tls_cacertfile`, `tls_req_cert`. Для upstream Keystone 2025.1 значения по умолчанию — `use_tls=False`, `tls_req_cert=demand`; LDAPS задаётся схемой URL, без StartTLS. Поэтому основной сценарий требует, чтобы библиотека LDAP внутри образа доверяла CA AD. Если необходим явный CA-файл в доменном конфиге или StartTLS, потребуется управляемое расширение доменного шаблона либо отдельный ручной доменный режим; произвольная переменная `ldap_use_tls` эту задачу не решает. [Опции Keystone](https://docs.openstack.org/keystone/2025.1/configuration/config-options.html#ldap).

У Grafana в шаблоне выставлены `start_tls=false`, `ssl_skip_verify=false`; у OpenSearch — `enable_start_tls=false`, `verify_hostnames=true`. OpenSearch работает на JVM: перенос CA в системное хранилище Linux сам по себе ещё не подтверждает доверие LDAP-плагина. Проверить его truststore или LDAP-параметр `pemtrustedcas_filepath` для фактической версии образа. В предоставленном LDAP-фрагменте этот параметр не задан. [OpenSearch: LDAP TLS](https://docs.opensearch.org/latest/security/authentication-backends/ldap/).

## 5. Проверка и применение

### 5.1. Проверить AD до переключения

На узле с диагностическими средствами проверить DNS, сертификат и чтение каталога. Подставить реальные значения. Пароль `ldapsearch` вводится интерактивно.

```bash
getent hosts dc01.example.org

openssl s_client -connect dc01.example.org:636 \
  -servername dc01.example.org -verify_hostname dc01.example.org \
  -verify_return_error -CAfile /path/to/ad-ca-chain.pem </dev/null

LDAPTLS_CACERT=/path/to/ad-ca-chain.pem LDAPTLS_REQCERT=demand \
ldapsearch -LLL -x -H ldaps://dc01.example.org:636 \
  -D 'svc-openstack@example.org' -W \
  -b 'OU=OpenStack,OU=Groups,DC=example,DC=org' \
  '(&(objectClass=group)(cn=os-virtualization-users))' \
  dn cn sAMAccountName member
```

Повторить поиск для административной группы и тестового пользователя в пользовательском OU. Успех на deployment-узле не подтверждает сетевой доступ и доверие из контейнеров Keystone, Grafana и OpenSearch: они проверяются отдельно после доставки CA.

### 5.2. Сгенерировать и проверить конфигурации

Команды запускать из окружения установленной исследованной ветки, с действующим inventory. Здесь `/path/to/multinode` — заполнитель. Теги включают существующие LDAP-клиенты; отключённые сервисы не нужно включать ради команды.

```bash
kolla-ansible prechecks -i /path/to/multinode \
  --tags keystone,horizon,grafana,opensearch

kolla-ansible genconfig -i /path/to/multinode \
  --tags keystone,horizon,grafana,opensearch
```

`genconfig` записывает конфигурационные файлы на deployment-узле и целевых узлах; это не read-only-проверка. До перезапуска проверить:

- наличие правильного URL, DN, имени домена, фильтров и файла CA;
- наличие доменного файла на всех узлах Keystone;
- сохранение SQL-драйвера для `Default`, отсутствие глобального `driver=ldap`;
- корректность `ldap.toml` и OpenSearch `security-audit/config.yml`, не раскрывая пароли;
- наличие доверия именно к CA AD, а не только к внутреннему CA OpenStack.

`prechecks` не заменяет LDAP bind, проверку ролей и проверку входа; OpenSearch precheck в этой ветке проверяет TCP-порт LDAP, а не полноценную аутентификацию.

### 5.3. Применить в согласованное окно

```bash
kolla-ansible reconfigure -i /path/to/multinode \
  --tags keystone,horizon,grafana,opensearch
```

Запуск может перезапустить сервисы. Keystone-роль создаёт домен, при его создании вызывает перезапуск, сбрасывает handlers перед запросом групп и назначает роли. При отсутствии одной из двух обязательных групп выполнение заканчивается ошибкой. Для запросов групп/назначений предусмотрены `ldap_role_retries=12`, `ldap_role_delay=10`; отсутствие группы не исправляется ожиданием само по себе.

OpenSearch-роль загружает конфигурацию Security plugin через `securityadmin.sh`, поэтому изменение затрагивает его действующую конфигурацию безопасности, а не только файл на диске. Не ограничивать такую операцию случайным одним узлом без проверки роли первого узла группы `opensearch`.

## 6. Что именно создаётся и какие права выдаются

| Объект | Реализация |
|---|---|
| Общая доменная настройка | `[identity] domain_specific_drivers_enabled=True`, `domain_config_dir=/etc/keystone/domains` |
| Домен AD | `keystone.<ldap_domain_name>.conf`, внутри `[identity] driver=ldap` |
| Доставка на узел Keystone | `/etc/kolla/keystone/domains/` |
| Путь внутри контейнера | `/etc/keystone/domains/`; в `config.json` задан владелец `keystone`, права `0600` |
| Группа `ldap_group_virt_admin` | `admin` на проект `keystone_admin_project` в `default_project_domain_name` |
| Группа `ldap_group_virt_user` | `member` на тот же проект |
| Группа `ldap_group_grafana_admin` | `org_role='Admin'`; это не явное назначение Grafana Server Admin |
| Группа `ldap_group_opensearch_admin` | `all_access` через `backend_roles` |

Автоматическое назначение в Keystone имеет область проекта, не `system_scope=all`. Однако реальные полномочия роли `admin` зависят от политик сервисов — нельзя считать такое назначение гарантированно ограниченным только одним проектом.

Членство в AD не создаёт автоматически отдельный проект для каждого пользователя. Для дополнительных проектов назначения выполняются через Keystone отдельно. Пользователь может пройти проверку пароля, но не получить доступ к проекту без назначения роли.

Вложенные группы обрабатываются неодинаково: Keystone включает `group_ad_nesting`, OpenSearch использует `resolve_nested_roles`, а шаблон поиска Grafana содержит обычное `(member=%s)` без рекурсивного AD matching rule. Проверять вложенность отдельно в каждом сервисе; для первичной приёмки использовать прямое членство.

## 7. Приёмочная проверка

Под локальным администратором проверить созданные объекты:

```bash
source /etc/kolla/admin-openrc.sh
openstack domain show LDAP
openstack group list --domain LDAP
openstack user list --domain LDAP
openstack project show --domain Default region
openstack role assignment list --group os-virtualization-users \
  --group-domain LDAP --project region --project-domain Default --names
openstack role assignment list --group os-virtualization-admins \
  --group-domain LDAP --project region --project-domain Default --names
```

Если deployment использует `clouds.yaml`, применить его штатный локальный административный профиль. Названия `LDAP` и `region` в командах должны соответствовать фактическим переменным. [Параметры просмотра role assignments](https://docs.openstack.org/python-openstackclient/2025.1/cli/command-objects/role-assignment.html).

Проверку пользователя AD выполнять **в отдельном чистом терминале**, без административных `OS_PASSWORD`, `OS_TOKEN`, `OS_SYSTEM_SCOPE`, `OS_PROJECT_ID` и `OS_USER_ID`. Пример параметров:

```bash
export OS_AUTH_URL='https://identity.example.org:5000/v3'
export OS_AUTH_TYPE=password
export OS_IDENTITY_API_VERSION=3
export OS_USERNAME='test.user'
export OS_USER_DOMAIN_NAME='LDAP'
export OS_PROJECT_NAME='region'
export OS_PROJECT_DOMAIN_NAME='Default'
export OS_CACERT='/path/to/openstack-api-ca.pem'

# Клиент запросит пароль интерактивно; токен в вывод не включён.
openstack token issue -f value -c expires
```

`OS_AUTH_URL` берётся из реального каталога endpoint; при едином HTTPS frontend порт может быть `443`. CA для OpenStack API и CA для AD могут различаться.

| Проверка | Критерий успеха |
|---|---|
| Локальный администратор `Default` | Вход сохраняется |
| Обычный пользователь AD | Получает токен для нужного проекта; разрешённая операция проходит |
| Пользовательская группа | Административная операция, не положенная `member`, отклоняется |
| Административная группа | Получает согласованные административные права |
| Учётная запись вне разрешённых назначений | Не получает доступ к проекту только из-за наличия в каталоге |
| Отключённая тестовая учётная запись AD | Новый вход отклоняется |
| Horizon | Вход через пункт `Active Directory`, логин `sAMAccountName`, без автоматического добавления доменного суффикса |
| Grafana / OpenSearch | Вход и права проверены отдельно для своих групп |
| Каждый контроллер | Имеет одинаковую конфигурацию и доверие к CA |

Проверки блокировки проводить на выделенной тестовой учётной записи. Уже выданные токены и открытые сессии проверяются отдельно: успешное отключение нового входа не доказывает мгновенный отзыв ранее выданного доступа.

Если используется Watcher с Prometheus, дополнительно проверить метрики ВМ, созданной обычным пользователем AD: поставленные recording rules фильтруют `user_name="admin"`, поэтому охват таких ВМ не гарантирован. Подробности и настройка Grafana приведены в [руководстве по мониторингу](PROMETHEUS_GRAFANA_ADMIN_GUIDE.md).

## 8. Диагностика и сопровождение

| Симптом | Что проверить |
|---|---|
| `SERVER DOWN`, timeout | DNS, маршрут, TCP/636, доверие libldap внутри Keystone, срок и имя сертификата |
| Ошибка bind / invalid credentials | Учётную запись bind, её пароль, блокировку и требования политики AD |
| Группы не найдены | `group_tree_dn`, класс `group`, значение `cn`, права чтения, точное имя LDAP-домена |
| Пользователь виден, токен проекта не выдаётся | Назначение роли, `OS_USER_DOMAIN_NAME=LDAP`, домен проекта `Default` |
| Keystone работает, Grafana не пускает | Полный DN административной группы, прямое членство, отдельный TLS-клиент Grafana |
| Keystone работает, OpenSearch не пускает | LDAP authc/authz, Java truststore, `roles_mapping.yml`, загрузку через Security plugin |
| Настройки пропали после `reconfigure` | Не редактировался ли файл, который автоматически перезаписывает роль |

Для первичного осмотра на соответствующем узле:

```bash
sudo podman ps --format '{{.Names}} {{.Status}}'
sudo podman logs --tail 100 keystone
sudo tail -n 100 /var/log/kolla/keystone/keystone.log
sudo podman exec keystone ls -l /etc/keystone/domains
```

Не публиковать полный доменный конфиг: он содержит bind-пароль. При ротации пароля обновить источник секрета и последовательно проверить всех трёх LDAP-клиентов. Парольная политика AD применяется в AD; настройки SQL password policy Keystone не заменяют её.

**Откат:** восстановить сохранённые значения и файлы, затем выполнить соответствующий `reconfigure`. Одного `ldap_engine_enabled: "no"` недостаточно для удаления уже созданных файлов, домена и назначений: в исследованных задачах автоматической очистки нет. Убирать остаточные доменные файлы нужно согласованно на deployment-узле и всех Keystone-узлах, включая копии внутри контейнеров; после перезапуска проверить результат. Домен и его назначения не удалять вслепую: отдельно учесть действующий доступ и зависимости. Локальный `Default` должен оставаться доступным на всех этапах.

## 9. Карта реализации и проверенных источников

| Источник | Что подтверждает |
|---|---|
| Шаблон LDAP-домена (`kolla-ansible-pvs_1.0.0/ansible/roles/keystone/templates/keystone-ldap-domain.conf.j2`) | Точный набор выводимых LDAP-параметров |
| Конфигурирование Keystone (`kolla-ansible-pvs_1.0.0/ansible/roles/keystone/tasks/config.yml`) | Перезапись custom-файлов, порядок merge и копирования |
| Регистрация домена (`kolla-ansible-pvs_1.0.0/ansible/roles/keystone/tasks/register.yml`) и назначение ролей (`kolla-ansible-pvs_1.0.0/ansible/roles/keystone/tasks/assign_ldap_roles.yml`) | Создание домена, поиск групп, проектные роли |
| Конфигурация контейнера (`kolla-ansible-pvs_1.0.0/ansible/roles/keystone/templates/keystone.json.j2`) | Пути внутри контейнера и права файлов |
| Настройки Horizon (`kolla-ansible-pvs_1.0.0/ansible/roles/horizon/templates/_9998-kolla-settings.py.j2`) | Формирование списка доменов |
| Переменные Grafana (`kolla-ansible-pvs_1.0.0/ansible/roles/grafana/vars/main.yml`) и ldap.toml (`kolla-ansible-pvs_1.0.0/ansible/roles/grafana/templates/ldap.toml.j2`) | Условия включения, DN группы, TLS, роль организации |
| Переменные OpenSearch (`kolla-ansible-pvs_1.0.0/ansible/roles/opensearch/vars/main.yml`), Security config (`kolla-ansible-pvs_1.0.0/ansible/roles/opensearch/defaults/main.yml`), загрузка Security config (`kolla-ansible-pvs_1.0.0/ansible/roles/opensearch/tasks/security-audit-post-config.yml`) | LDAP authc/authz, TLS и `all_access` |

SHA-256 основного архива: `e68e98cb5ce6d2384ebf90c4ff1e6a9b779efe986ae11a83bc8cb1b556bfe004`. Ссылки `sources/...` ведут на распакованный исходный срез рядом с документом. Документация upstream использована для семантики протокола и Keystone; особенности ветки установлены по локальным исходникам. Значения production inventory, содержимое образов и runtime-состояние остаются предметом приёмки.
