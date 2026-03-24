# Usamos PostGIS con PostgreSQL 18
FROM postgis/postgis:18-3.6

# Instalamos las dependencias necesarias para compilar pgvector
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    postgresql-server-dev-18

# Clonamos, compilamos e instalamos pgvector en /tmp
RUN cd /tmp \
    && git clone --branch v0.8.2 https://github.com/pgvector/pgvector.git \
    && cd pgvector \
    && make \
    && make install

# Limpiamos para reducir el tamaño de la imagen
RUN apt-get remove -y build-essential git postgresql-server-dev-18 \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* /tmp/pgvector

# COPIA EL SCRIPT DE INICIALIZACIÓN
# PostgreSQL ejecutará este script automáticamente en el primer arranque
COPY init.sql /docker-entrypoint-initdb.d/