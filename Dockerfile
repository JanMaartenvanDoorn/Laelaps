# SPDX-FileCopyrightText: 2023 Jan Maarten van Doorn <laelaps@vandoorn.cloud>
#
# SPDX-License-Identifier: MPL-2.0

FROM python:3.11.4-slim

# Copy files
COPY . .

# Install dependencies
RUN pip install --upgrade pip && pip install .

# Start app
CMD python -m laelaps
