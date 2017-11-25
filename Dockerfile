# Base Image: %%RESIN_MACHINE_NAME%% supports multiple arch
FROM resin/raspberry-pi2-python

# Set our working directory
WORKDIR /usr/src/app

# Copy requirements.txt first for better cache on later pushes
COPY ./requirements.txt /requirements.txt 

# The resin.io python-based images has already the following installed:
# pip, python-dbus, virtualenv, setuptools

# pip install python deps from requirements.txt on the resin.io build server
RUN pip install -r /requirements.txt

# This will copy all files in our root to the working  directory in the container
COPY . ./

# switch on systemd init system in container
ENV INITSYSTEM on

# main.py will run when container starts up on the device
CMD [ "python","src/example-flask.py" ]