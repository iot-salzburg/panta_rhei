FROM grafana/grafana:6.2.5

USER root

RUN apt-get update && \
  apt-get install -y --no-install-recommends \
  gettext

# in the container you just started:
RUN chown -R root:root /etc/grafana && \
  chmod -R a+r /etc/grafana && \
  chown -R grafana:grafana /var/lib/grafana && \
  chown -R grafana:grafana /usr/share/grafana

RUN grafana-cli plugins install grafana-worldmap-panel \
 && grafana-cli plugins install natel-plotly-panel\
 && grafana-cli plugins install grafana-piechart-panel\
 && grafana-cli plugins install grafana-simple-json-datasource

ADD provisioning /etc/grafana/provisioning
ADD config.ini /etc/grafana/config.ini

ARG DBINDEX1
ARG DBINDEX2

ENTRYPOINT envsubst < /etc/grafana/provisioning/datasources/source1.yml > /etc/grafana/provisioning/datasources/source1.yml \
  && envsubst < /etc/grafana/provisioning/datasources/source2.yml > /etc/grafana/provisioning/datasources/source2.yml \
  && su grafana \
  && sh /run.sh
