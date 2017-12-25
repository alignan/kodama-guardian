# Base Image
FROM resin/raspberry-pi2-python

RUN apt-get update && apt-get install -yq \
            python-smbus i2c-tools libraspberrypi-bin ca-certificates && \
            apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy requirements file first for better cache on later pushes
COPY ./requirements.txt /requirements.txt 

# The resin.io python-based images has already the following installed:
# pip, python-dbus, virtualenv, setuptools

# pip install python deps from requirements.txt on the resin.io build server
RUN pip install -r /requirements.txt

# This will copy all files in our root to the working directory in the container
COPY . /usr/src/app

# Set our working directory
WORKDIR /usr/src/app

# switch on systemd init system in container
ENV INITSYSTEM on

# main.py will run when container starts up on the device
CMD modprobe i2c-dev && python src/kodama.py