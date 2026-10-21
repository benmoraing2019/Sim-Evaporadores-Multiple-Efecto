# Puedes ajustar la versión de Python según tus necesidades (ej. 3.10, 3.11, 3.12)
FROM mcr.microsoft.com/devcontainers/python:3.11

# Evitar advertencias durante la instalación de paquetes del SO
ENV DEBIAN_FRONTEND=noninteractive

# Instalación de dependencias del sistema recomendadas para librerías científicas
RUN apt-get update && apt-get -y install --no-install-recommends \
    build-essential \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*

# Actualizar pip e instalar los paquetes requeridos
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    numpy \
    scipy \
    matplotlib \
    pygimli