# Выключение хостов при реконфигурации Consul: краткий вывод

Дата исследования: 13.10.2026.

**В исследованных архивах найден механизм, способный объяснить физическое выключение compute-хостов при `kolla-ansible reconfigure`: ложное обнаружение отказа через Consul может запустить fencing Masakari через Ironic. Причина конкретного инцидента пока не подтверждена журналами.**

Исследованы `kolla-ansible-pvs.zip`, `kolla-pvs_1.0.1.zip`, `masakari-pvs_1.0.1.zip` и `mistral-pvs_1.0.1.zip`. Два архива Masakari, включая файл с суффиксом `(1)`, побайтно идентичны. Архивы и распакованные исходники в этот репозиторий не включены; пути к реализации приведены в сносках. Исходный код и настройки не изменялись, действий на кластере не выполнялось.

## Подтверждённое поведение

Предполагаемая цепочка инцидента:

```text
kolla-ansible reconfigure
→ изменение конфигурации/параметров контейнеров Consul и их рестарт
→ Hostmonitor получает состояние отказа по данным Consul
→ матрица разрешает host recovery
→ Masakari: disable_compute_service_task → ironic_fence
→ Ironic: set_node_power_state(node, "power off", wait=False)
→ физическое выключение хоста
```

1. **Рестарт Consul не защищён режимом обслуживания HA.** `reconfigure.yml` вызывает `deploy.yml`, который применяет конфигурацию, проверяет контейнеры и выполняет restart handlers. Роль Consul выполняется перед Masakari. В этой процедуре нет установки Masakari maintenance, приостановки Hostmonitor или ожидания стабилизации membership. Обязательного рестарта по одному узлу нет: `kolla_serial` по умолчанию равен `0`. Сам вызов `reconfigure` не означает безусловный рестарт: handler вызывается при обнаружении изменений.
2. **При включённом PowerOps recovery содержит физическое выключение.** Fencing стоит перед подготовкой и эвакуацией ВМ. Проверка Nova `disabled/down` выполняется после подтверждённого выключения. Автоматическое включение хоста при откате не предусмотрено.
3. **Шаблон Hostmonitor использует `monitoring_interval=60`, `monitoring_samples=1` по значениям архива.** Объявленные рядом `masakari_consul_monitoring_interval=30` и `masakari_consul_monitoring_samples=3` этим шаблоном не используются. Фактические значения могут быть переопределены на стенде.
4. **Адреса независимых сетей по умолчанию совпадают.** При включении трёх сетей шаблон формирует `agent_manage`, `agent_tenant`, `agent_storage` с одним адресом `127.0.0.1:8500`. Consul-контейнеры используют сеть хоста и тот же HTTP-адрес, что создаёт конфликт прослушивания для нескольких агентов. Опрос одного источника вместо трёх также лишает матрицу независимых наблюдений.

Генератор матрицы проверен локальным запуском: для трёх сетей `all_down` разрешает recovery только при `[down, down, down]`; для единственной management-сети — при `[down]`.

## Граница доказанности

Архива вашей сборки **`masakari-monitors` нет**. Kolla получает его из отдельного репозитория; архив Masakari Engine его не заменяет.

В проверенном upstream `stable/2025.1` Consul-драйвер преобразует member `Status == 1` в `up`, остальные статусы — в `down`. При одном sample переход ранее наблюдавшегося хоста из `up` в подходящий под матрицу `down` может вызвать событие `COMPUTE_HOST/STOPPED`. Ошибка обращения к HTTP API Consul обрабатывается как исключение и сама по себе не означает recovery. Соответствие этой логики вашей сборке требует проверки.

Для подтверждения инцидента нужно сопоставить время рестарта Consul, notification Hostmonitor, выполнение `ironic_fence` и операцию Ironic/BMC. Нужны фактические `masakari-monitors.conf`, `matrix.yaml`, настройки PowerOps и журналы за соответствующий интервал.

## Источники

- Consul deploy.yml[^source-1], restart handlers[^source-2], site.yml[^source-3], строки 1131–1164.
- Шаблон Masakari Engine[^source-4], строки 88–108; IronicFenceTask[^source-5], строки 48–70 и 140–158; IronicPowerClient[^source-6], строки 133–160.
- Шаблон Hostmonitor[^source-7], строки 43–65; group_vars/all.yml[^source-8], строки 640–641, 1076–1082 и 1110–1119; defaults Masakari[^source-9], строки 218–237.
- Матрица[^source-10], строки 140–220; Docker network mode[^source-11], строка 293.
- Upstream для сравнения: [Consul manager](https://github.com/openstack/masakari-monitors/blob/stable/2025.1/masakarimonitors/hostmonitor/consul_check/manager.py), [Consul helper](https://github.com/openstack/masakari-monitors/blob/stable/2025.1/masakarimonitors/hostmonitor/consul_check/consul_helper.py).

Рекомендации: [CONSUL_RECONFIGURE_HA_RECOMMENDATIONS.md](CONSUL_RECONFIGURE_HA_RECOMMENDATIONS.md).

[^source-1]: Архив `kolla-ansible-pvs.zip`, файл `kolla-ansible-pvs/ansible/roles/consul/tasks/deploy.yml`.
[^source-2]: Архив `kolla-ansible-pvs.zip`, файл `kolla-ansible-pvs/ansible/roles/consul/handlers/main.yml`.
[^source-3]: Архив `kolla-ansible-pvs.zip`, файл `kolla-ansible-pvs/ansible/site.yml`.
[^source-4]: Архив `kolla-ansible-pvs.zip`, файл `kolla-ansible-pvs/ansible/roles/masakari/templates/masakari.conf.j2`.
[^source-5]: Архив `masakari-pvs_1.0.1.zip`, файл `masakari-pvs_1.0.1/masakari/engine/drivers/taskflow/powerops.py`.
[^source-6]: Архив `masakari-pvs_1.0.1.zip`, файл `masakari-pvs_1.0.1/masakari/powerops/ironic.py`.
[^source-7]: Архив `kolla-ansible-pvs.zip`, файл `kolla-ansible-pvs/ansible/roles/masakari/templates/masakari-monitors.conf.j2`.
[^source-8]: Архив `kolla-ansible-pvs.zip`, файл `kolla-ansible-pvs/ansible/group_vars/all.yml`.
[^source-9]: Архив `kolla-ansible-pvs.zip`, файл `kolla-ansible-pvs/ansible/roles/masakari/defaults/main.yml`.
[^source-10]: Архив `kolla-ansible-pvs.zip`, файл `kolla-ansible-pvs/kolla_ansible/masakari_consul.py`.
[^source-11]: Архив `kolla-ansible-pvs.zip`, файл `kolla-ansible-pvs/ansible/module_utils/kolla_docker_worker.py`.
