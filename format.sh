# SPDX-FileCopyrightText: 2026 Jan Maarten van Doorn <laelaps@vandoorn.cloud>
#
# SPDX-License-Identifier: MPL-2.0

autoflake .
bandit -r ./laelaps
black .
isort .
flake8 .
pydocstyle laelaps
mypy laelaps
pylint laelaps
reuse lint
pytest tests
