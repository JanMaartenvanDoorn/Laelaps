# SPDX-FileCopyrightText: 2024 Jan Maarten van Doorn <laelaps@vandoorn.cloud>
#
# SPDX-License-Identifier: MPL-2.0

autoflake .
bandit -r ./laelaps
black .
isort .
docformatter --in-place ./laelaps/*.py ./laelaps/*.py
flake8 .
pydocstyle laelaps
mypy laelaps
pylint laelaps
reuse lint
pytest tests
