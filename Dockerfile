ARG pyversion=3.7
FROM python:${pyversion}-stretch
ARG pyversion=3.7
ENV PYVERSION ${pyversion:-3.7}

# Install packages
RUN apt-get -yqq update && \
    apt-get -yqq install apache2 apache2-dev locales && \
    apt-get clean

# Install locale
COPY ./locale.gen /etc/locale.gen
RUN locale-gen

# Prepare virtualenv
RUN mkdir /app
WORKDIR /app
RUN python -m venv ./virtualenv
RUN ./virtualenv/bin/pip install --upgrade pip setuptools

# Install mod_wsgi
RUN ./virtualenv/bin/pip install mod_wsgi

# Install requirements
COPY ./requirements.txt ./requirements.txt
RUN ./virtualenv/bin/pip install --trusted-host pypi.python.org -r requirements.txt

# Prepare app directory
RUN mkdir ./pylibs

COPY ./pylibs/* ./pylibs/


COPY ./index.html ./www-data/index.html
COPY ./dab.wsgi ./www-data/dab.wsgi

# Configure Apache
COPY ./start-apache.sh /
COPY ./wsgi.conf.tmpl /tmp/wsgi.conf.tmpl
RUN sed -e s/\$PYVERSION/$PYVERSION/g /tmp/wsgi.conf.tmpl | sed -e s/\$PYV/`echo $PYVERSION | sed -e "s/\\.//"`/g >/etc/apache2/mods-enabled/wsgi.conf
COPY apache.conf /etc/apache2/sites-available/000-default.conf

ENV VERBOSE False
# ENV DB_PASS_WD 


# Start Apache
EXPOSE 80
CMD ["/bin/sh", "/start-apache.sh"]

