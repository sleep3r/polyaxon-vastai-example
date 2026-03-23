# Настройки
PROJECT=mnist-test

include .env
export

.PHONY: help check init run run-fast run-full logs status dashboard notebook

help:
	@echo "Доступные команды:"
	@echo "  make check      - Проверка подключения к серверу"
	@echo "  make init       - Создание проекта $(PROJECT)"
	@echo "  make run        - Запуск обучения (5 эпох, дефолт)"
	@echo "  make run-fast   - Быстрый тест (2 эпохи)"
	@echo "  make run-full   - Полное обучение (15 эпох)"
	@echo "  make logs       - Просмотр логов"
	@echo "  make status     - Статус запусков"
	@echo "  make dashboard  - Открыть веб-интерфейс"
	@echo "  make notebook   - Запуск Jupyter ноутбука"

check:
	@uv run polyaxon project ls > /dev/null 2>&1 \
		&& echo "✅ Подключено к $(POLYAXON_HOST)" \
		|| echo "❌ Не удалось подключиться к $(POLYAXON_HOST)"

init:
	uv run polyaxon project create --name $(PROJECT)

run:
	uv run polyaxon run -f infra/polyaxonfile.yaml -u -p $(PROJECT)

run-fast:
	uv run polyaxon run -f infra/polyaxonfile.yaml -u -p $(PROJECT) -P epochs=2

run-full:
	uv run polyaxon run -f infra/polyaxonfile.yaml -u -p $(PROJECT) -P epochs=15 -P lr=0.0005

logs:
	uv run polyaxon ops logs -p $(PROJECT)

status:
	uv run polyaxon ops ls -p $(PROJECT)

dashboard:
	@open "$(POLYAXON_HOST)" 2>/dev/null || echo "Открой: $(POLYAXON_HOST)"

notebook:
	uv run polyaxon run -f infra/notebook.yaml -p $(PROJECT)
