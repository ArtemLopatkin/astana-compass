# Координация трёх команд

Публичный upstream: https://github.com/chinusoid/astana-compass. Репозиторий не требует приглашения для чтения/fork. Публикация в upstream осуществляется через PR; прямой push доступен только владельцу/приглашённым collaborators.

## Порядок работы

1. Каждая команда получает один актуальный `TEAM-*.md`, читает `AGENTS.md`, `PRODUCT.md`, `CONTRACTS.md` и `docs/api/README.md`.
2. Fork → clone → upstream remote → ветка `team/01-data-search`, `team/02-context-routes` или `team/03-frontend-ux` от актуального upstream/main.
3. Сначала небольшой рабочий вертикальный срез модуля с offline tests, затем расширения. Общие контракты не копируются в независимые DTO.
4. Перед PR подтянуть upstream, проверить совместимость, описать данные/тесты/ограничения/ключи без значений. Не скрывать synthetic, approximate и unavailable modes.
5. Координатор проверяет PR, обновляет root workspace и lockfile при интеграции модулей, выполняет общий набор тестов и сливает совместимые изменения. Команды сами не merge и не включают auto-merge.

Пример без передачи чужих credentials:

```sh
git clone https://github.com/YOUR_ACCOUNT/astana-compass.git
cd astana-compass
git remote add upstream https://github.com/chinusoid/astana-compass.git
git fetch upstream
git switch -c team/01-data-search upstream/main
```

Ветки остальных команд выбираются по своему заданию. Пользуйтесь собственной локальной авторизацией GitHub. Не публикуйте токены в запросах боту.

## Интеграционные точки

- `astana-contracts` устанавливается из uv workspace. Root JSON schema канонична, bundled JSON/TypeScript генерируются.
- Team01 возвращает `PlaceRepository` и `Retriever` через согласованные factories.
- Team02 возвращает `ContextProvider`. `ContextResult` уже определён; погода требует отдельного явного расширения wire contract.
- Team03 использует `packages/api_client` и `/v1` endpoints. До реальных данных UI обязан показывать fixture mode.
- Корневые lockfiles меняет координатор; manifest собственного модуля может менять команда.
- Межкомандные запросы: `docs/requests/team-NN-*.md`. Укажите точный контракт, совместимость и тест.

## Приёмка

Нужны passing локальные и GitHub CI проверки, понятные source provenance, отсутствие секретов, review API совместимости и фактических ограничений. Решение required constraints, геометрия маршрута, порядок выбранных stops и time budget не отдаются LLM. Изменения `main` защищены процессом PR/review; техническую branch protection следует проверять отдельно, этот файл её не включает.

Оригинальные восемь TASK-файлов — архив предыдущего разбиения. Их ownership заменён текущим AGENTS и тремя TEAM-файлами.
