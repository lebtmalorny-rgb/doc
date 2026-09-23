# Административная документация OpenStack / Kolla-Ansible

Документы подготовлены по предоставленным исходникам OpenStack и Kolla-Ansible; основная база — архивы ветки `pvs_1.0.0` от 21.09.2026. Для отдельных документов используются более поздний Kolla-архив и патчи, перечисленные в их разделах об источниках. В руководствах сначала дана краткая справка, затем параметры, детали реализации и порядок проверки.

| Документ | Содержание |
|---|---|
| [Короткий backlog HA / PowerOps / VMClone](OPENSTACK_BACKLOG.md) | Готовые, но не внедрённые патчи; Ironic, Watcher, эвакуация, возврат хоста и поэтапный запуск ВМ |
| [Важные параметры Mistral, Masakari, Watcher, Consul и Ironic](OPENSTACK_SERVICE_PARAMETERS.md) | Defaults, точные места определения, единицы и назначение, overrides, VMClone/PowerOps, recovery, метрики, BMC и проверка конфигов |
| [Кратко по требованиям КБ](<КБ_кратко_по_требованиям_2026-09-23.md>) | Ключевые требования, реализованные механизмы и оставшиеся пробелы по четырём блокам |
| [Отчёт по блокам КБ](<Отчет_КБ_по_блокам_2026-09-23.md>) | Ролевая модель и AD, аудит, Vault/SecMan и mTLS, firewall; все 161 строка требований и подпунктов XLSX, включая 39 не оценённых в этой работе |
| [Проверка ролевой модели PVS](PVS_ROLE_MODEL_REVIEW_2026-09-21.md) | Сопоставление с архивом от 21.09, уточнение ДКБ-РМ-12–15, матрица прав, Vault и аудит |
| [Интеграция с Active Directory](LDAP_AD_ADMIN_GUIDE.md) | LDAP/LDAPS, Keystone, Horizon, Grafana, OpenSearch, группы и назначения ролей |
| [Firewall](FIREWALL_ADMIN_GUIDE.md) | Порты, разрешённые и запрещённые направления, firewalld, каталог потоков, проверка и откат |
| [Prometheus и Grafana](PROMETHEUS_GRAFANA_ADMIN_GUIDE.md) | Exporters, jobs, метрики, правила, уведомления и два поставляемых дашборда |
| [Справочник метрик exporters — Epoxy 2025.1](PROMETHEUS_EXPORTERS_METRICS_EPOXY_2025_1.md) | Названия, описания, типы, единицы и labels; vanilla-версии, расширенные каталоги и несовместимые зависимости PVS |
| [Исправление получения метрик Watcher](WATCHER_PROMETHEUS_FIX_GUIDE.md) | FQDN и адрес datasource, согласование labels, CPU/RAM ВМ всех пользователей, TLS и проверка результата |

Во всех документах разделены настройки в `globals.yml` / `globals.d`, defaults в `ansible/group_vars/all.yml` и отдельных ролях, исходные overrides и сгенерированные конфиги.

## Исходные версии

Пути к реализации внутри документов относятся к корням соответствующих ZIP-архивов. Архивы и распакованные исходники в этот репозиторий не включены; ссылки между Markdown-документами работают внутри репозитория. Отчёты по КБ от 23.09.2026 также используют XLSX «Требования КБ 02_07_2026_v3.xlsx» и ролевую модель v5; эти исходные документы в репозиторий не включены.

| Архив | Коммит из комментария ZIP |
|---|---|
| `kolla-ansible-pvs_1.0.0_21.09zip.zip` | `365af98421ff35db2e9ca5ee605723a1bcc8e756` |
| `masakari-pvs_1.0.0_21.09.zip` | `702480386d63c935a6f1b143fbd65f54dba63f52` |
| `watcher-pvs_1.0.0_21.09.zip` | `96eeba4c5b8ce30f29fd7d6461bdac28fdfdfa4d` |
| `kolla-ansible-enroll-ironic-patch-3.zip` | `5db3c8eed90d69a85e3761ff7f55cb72d7fde94f` |
| `mistral-integration-powerops-mistral-2025.1.zip` | `99514c4e11fa2dfdc00dd8de5aa7f5ca07300514` |

Справочник метрик от 22.09.2026 дополнительно сверяет оба Kolla-архива с ванильными exporters из Kolla `stable/2025.1`; точный upstream-срез указан в самом документе.

Справочник параметров от 22.09.2026 использует Kolla `enroll-ironic-patch-3` и Mistral с применёнными патчами [VMClone v1](https://github.com/lebtmalorny-rgb/mistral_live_cloning/tree/02e07a20bc6fdd2102e91fe5d7fe5c6331afaabe). Настройки, добавленные патчем, отделены от исходных defaults. Версии Masakari/Watcher и контрольные суммы исходных архивов указаны в самом справочнике.

Контрольные суммы SHA-256 исходных архивов:

```text
e68e98cb5ce6d2384ebf90c4ff1e6a9b779efe986ae11a83bc8cb1b556bfe004  kolla-ansible-pvs_1.0.0_21.09zip.zip
12403a06d810cbdfe560bc104472f6fe3b1f38b572f9c9e59212329ab6a37db3  kolla-ansible-enroll-ironic-patch-3.zip
71f28efd2c97bbd82f1b5ecd2fdbaa3dd6fb4de69cb2c36469fa2b86308a0a55  mistral-integration-powerops-mistral-2025.1.zip
cf40ec62cdde2795499e7e46e6f5599fe9beb90b07c16c8a988f28d436469156  masakari-pvs_1.0.0_21.09.zip
67722deaa94b4e606620519c34a3db84f3253c492e7238f78bf0045a65c2ac0b  watcher-pvs_1.0.0_21.09.zip
```

## Граница проверки

Это анализ исходников, не отчёт о состоянии действующего облака. Доступность портов, LDAP-вход, получение метрик и доставка уведомлений на стенде не проверялись. Команды в документах при их подготовке на инфраструктуре не выполнялись.

В руководствах отмечены ограничения конкретной ветки: неполное покрытие потоков firewall, несовпадение группы Prometheus в каталоге firewall и inventory, отсутствие импортируемого `pvs_post_config.yml`, условия загрузки правил и дашбордов. До применения изменяющих команд необходимо учесть соответствующие разделы.
