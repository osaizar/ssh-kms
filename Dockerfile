# Base Image 
FROM python:3.10
# MAINTAINER of the Dockerfile
MAINTAINER Oier Saizar <oisaizar@gmail.com>

# Working directory inside app
WORKDIR /app
#Copy the app
COPY ssh-kms.py /app
COPY client/get-ssh-keys.py /app/client/get-ssh.keys.py
COPY requirements.txt /app

# Copy the config
COPY ssh-keys.json /config/ssh-keys.json

# Install app dependecy 
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

#Expose Nginx Port
EXPOSE 5000

#Start NginxService 
ENTRYPOINT ["python"]
CMD ["ssh-kms.py"]

VOLUME /config