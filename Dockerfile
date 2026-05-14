ARG PYTHON_IMAGE=public.ecr.aws/docker/library/python:3.12-slim
ARG NODE_IMAGE=public.ecr.aws/docker/library/node:22-slim

FROM ${PYTHON_IMAGE} AS backend-base

WORKDIR /app

COPY backend/pyproject.toml /app/backend/pyproject.toml
COPY backend/ssh_kms /app/backend/ssh_kms
COPY client/get-ssh-keys.py /app/client/get-ssh-keys.py
COPY img /app/img

COPY config/ssh-keys.json /config/ssh-keys.json

RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir /app/backend

FROM backend-base AS backend-test

COPY tests /app/tests
COPY pytest.ini /app/pytest.ini
RUN pip install --no-cache-dir "/app/backend[test]"

FROM ${NODE_IMAGE} AS frontend

WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ARG VITE_OIDC_ENABLED=false
ARG VITE_OIDC_AUTHORITY=http://localhost:8080/realms/ssh-kms
ARG VITE_OIDC_CLIENT_ID=ssh-kms-ui
ENV VITE_OIDC_ENABLED=${VITE_OIDC_ENABLED}
ENV VITE_OIDC_AUTHORITY=${VITE_OIDC_AUTHORITY}
ENV VITE_OIDC_CLIENT_ID=${VITE_OIDC_CLIENT_ID}
RUN npm run build

FROM backend-base

LABEL maintainer="Oier Saizar <oisaizar@gmail.com>"

COPY --from=frontend /frontend/dist /app/frontend/dist

EXPOSE 5000
VOLUME /config

ENV SSH_KMS_KEY_FILE=/config/ssh-keys.json
ENV SSH_KMS_CLIENT_FILE=/app/client/get-ssh-keys.py
ENV SSH_KMS_PROJECT_DIR=/app

ENTRYPOINT ["python"]
CMD ["-m", "ssh_kms"]
