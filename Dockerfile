# SPDX-FileCopyrightText: 2024 Jan Maarten van Doorn <laelaps@vandoorn.cloud>
#
# SPDX-License-Identifier: MPL-2.0

# Use Python 3.13.1-slim as base image
FROM python:3.13.1-slim

# Set metadata
LABEL org.opencontainers.image.source = https://github.com/JanMaartenVanDoorn/laelaps
LABEL org.opencontainers.image.license = MPL-2.0

# Copy files
COPY . .

# Install dependencies
RUN pip install --upgrade pip && pip install .

# Start app
CMD python -m laelaps