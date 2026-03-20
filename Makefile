# Настройки
PROJECT=mnist-test

include .env
export

.PHONY: help check init run logs status dashboard

help:
	@echo "Доступные команды:"
	@echo "  make check     - Проверка подключения к серверу"
	@echo "  make init      - Создание проекта $(PROJECT)"
	@echo "  make run       - Запуск обучения"
	@echo "  make logs      - Просмотр логов"
	@echo "  make status    - Статус запусков"
	@echo "  make dashboard - Открыть веб-интерфейс"

check:
	@uv run polyaxon project ls > /dev/null 2>&1 \
		&& echo "✅ Подключено к $(POLYAXON_HOST)" \
		|| echo "❌ Не удалось подключиться к $(POLYAXON_HOST)"

init:
	uv run polyaxon project create --name $(PROJECT)

run:
	uv run polyaxon run -f polyaxonfile.yaml -u -p $(PROJECT)

logs:
	uv run polyaxon ops logs -p $(PROJECT)

status:
	uv run polyaxon ops ls -p $(PROJECT)

dashboard:
	@open "$(POLYAXON_HOST)" 2>/dev/null || echo "Открой: $(POLYAXON_HOST)"

notebook:
	uv run polyaxon run -f notebook.yaml -p $(PROJECT)
