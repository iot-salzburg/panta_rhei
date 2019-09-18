FROM httpd:2.4

RUN apt-get update -y && apt-get install -y libapache2-mod-auth-openidc

COPY conf/httpd.conf /usr/local/apache2/conf/httpd.conf
COPY conf/auth_oidc.conf /usr/local/apache2/conf/auth_oidc.conf