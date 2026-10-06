# Everything runs on your own machine: no cloud, no infrastructure to create. "make" just calls the
# scripts in app/run/.

.DEFAULT_GOAL := help
.PHONY: help local chat dvc-setup dvc-pull dvc-push

help: ## Lists the commands
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | sed -E 's/:.*## /\t/'

local: ## Validates, indexes and examines knowledge/ in local Docker
	app/run/run.sh

chat: ## Interactive chat with the bot once it's up (run it after "make local")
	app/run/chat.sh

dvc-setup: ## One-time: brings up SeaweedFS and configures it as the DVC remote
	app/dvc-setup.sh

dvc-pull: ## Fetches knowledge/ from the DVC remote (SeaweedFS)
	cd app && uv run --group dvc dvc pull

dvc-push: ## Publishes your local changes to knowledge/ to the DVC remote (SeaweedFS)
	cd app && uv run --group dvc dvc add knowledge && uv run --group dvc dvc push
