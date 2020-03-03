# FROM anapsix/alpine-java:8u202b08_jdk
FROM java:8
MAINTAINER Christoph Schranz <christoph.schranz@salzburgresearch.at>

RUN export STREAM_NAME=docker_stream_name


ADD . /usr/src/streamhub
WORKDIR /usr/src/streamhub

# RUN curl 192.168.48.179:9092

CMD java -jar out/artifacts/streamhub_apps_jar/streamhub_apps.jar
