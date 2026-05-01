# Clinical Co-Pilot — local developer tasks (no Fly deploy).
# Usage: make test | make pytest | make chat-ui-build | make smoke-help

.PHONY: test pytest pytest-fast openapi-check chat-ui-build chat-ui-install lint-ruff fmt-ruff smoke-help doctor

test: pytest chat-ui-build

pytest:
	python -m pytest agent/tests deploy/tests -q

pytest-fast:
	python -m pytest agent/tests deploy/tests -q -m "not eval"

openapi-check:
	python -m pytest agent/tests/unit/test_openapi_contract.py -q

chat-ui-install:
	cd chat-ui && npm ci

chat-ui-build: chat-ui-install
	cd chat-ui && npm run build

lint-ruff:
	ruff check agent

fmt-ruff:
	ruff format agent

smoke-help:
	@echo PowerShell: pwsh -File scripts/smoke_agent_optional.ps1 -BaseUrl https://YOUR-agent.fly.dev
	@echo Bash:       bash scripts/smoke_agent_optional.sh --base-url https://YOUR-agent.fly.dev

doctor:
	bash scripts/doctor.sh
