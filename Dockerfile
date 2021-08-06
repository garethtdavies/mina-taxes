FROM python:3.8-buster

RUN adduser exporter

WORKDIR /home/exporter

COPY requirements.txt requirements.txt
RUN python -m venv venv
RUN venv/bin/pip install -r requirements.txt

COPY app app
COPY config.py config.py
COPY taxapp.py wsgi.py taxapp.sh ./
RUN chmod +x taxapp.sh

ENV FLASK_APP=taxapp.py

RUN chown -R exporter:exporter ./
USER exporter

EXPOSE 8080 
ENTRYPOINT [ "./taxapp.sh" ]
