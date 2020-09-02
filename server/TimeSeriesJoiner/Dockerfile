FROM python:3.7
# not using onbuild, because code updates result in re-fetching of the image

MAINTAINER Christoph Schranz <christoph.schranz@salzburgresearch.at>

# test internet connection and dns settings. If apt-get update fails there is a Docker error.
# Restart the Docker, check internet connection and dns settings in /etc/docker/daemon.json
#RUN apt-get update

# install the official librdkafka client written in C
ENV LIBRDKAFKA_VERSION 1.4.4
RUN apt-get update && \
    git clone https://github.com/edenhill/librdkafka && cd librdkafka && \
    git checkout v${LIBRDKAFKA_VERSION} && \
    ./configure && make && make install && ldconfig

# Copy requirements to the host and install them
ADD requirements.txt .
RUN pip install -r requirements.txt

# Copy the content of this folder into the hosts src directory.
RUN mkdir /src
ADD . /src

# Load environment variables to customize Stream Apps
ENV STREAM_NAME $STREAM_NAME
ENV SOURCE_SYSTEM $SOURCE_SYSTEM
ENV TARGET_SYSTEM $TARGET_SYSTEM
ENV GOST_SERVER $GOST_SERVER
ENV KAFKA_BOOTSTRAP_SERVERS $KAFKA_BOOTSTRAP_SERVERS
ENV FILTER_LOGIC $FILTER_LOGIC

ENV PYTHONPATH /
WORKDIR /src
ENTRYPOINT ["python", "/src/stream_join_engine.py", "--use-env-config"]
