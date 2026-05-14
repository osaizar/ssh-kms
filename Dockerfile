ARG NODE_IMAGE=public.ecr.aws/docker/library/node:22-slim
ARG PYTHON_IMAGE=public.ecr.aws/docker/library/python:3.12-slim

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

FROM ${PYTHON_IMAGE}

LABEL maintainer="Oier Saizar <oisaizar@gmail.com>"

WORKDIR /app

COPY backend/ssh-kms.py /app/backend/ssh-kms.py
COPY client/get-ssh-keys.py /app/client/get-ssh-keys.py
COPY backend/requirements.txt /app/backend/requirements.txt
COPY img /app/img
COPY --from=frontend /frontend/dist /app/frontend/dist

COPY config/ssh-keys.json /config/ssh-keys.json

RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r backend/requirements.txt

EXPOSE 5000
VOLUME /config

ENV SSH_KMS_KEY_FILE=/config/ssh-keys.json
ENV SSH_KMS_CLIENT_FILE=/app/client/get-ssh-keys.py

ENTRYPOINT ["python"]
CMD ["backend/ssh-kms.py"]
