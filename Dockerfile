FROM node:22-slim AS frontend

WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim

LABEL maintainer="Oier Saizar <oisaizar@gmail.com>"

WORKDIR /app

COPY ssh-kms.py /app
COPY client/get-ssh-keys.py /app/client/get-ssh-keys.py
COPY requirements.txt /app
COPY img /app/img
COPY --from=frontend /frontend/dist /app/frontend/dist

COPY ssh-keys.json /config/ssh-keys.json

RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000
VOLUME /config

ENV SSH_KMS_KEY_FILE=/config/ssh-keys.json
ENV SSH_KMS_CLIENT_FILE=/app/client/get-ssh-keys.py

ENTRYPOINT ["python"]
CMD ["ssh-kms.py"]
