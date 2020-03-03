# FROM anapsix/alpine-java:8u202b08_jdk
FROM java:8
MAINTAINER Christoph Schranz <christoph.schranz@salzburgresearch.at>

ADD target/streamApp-1.1-jar-with-dependencies.jar /streamApp.jar

ENTRYPOINT ["java", "-jar", "/streamApp.jar"]
