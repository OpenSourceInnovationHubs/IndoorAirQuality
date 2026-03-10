FROM python:3.12-alpine

ENV HOME=/app
RUN mkdir -p $HOME
WORKDIR $HOME

# Install curl for the healthcheck
RUN apk add --no-cache curl

ADD requirements.txt $HOME/requirements.txt
RUN pip install -r $HOME/requirements.txt

ADD . $HOME/ngsi_proxy

CMD ["python", "ngsi_proxy/app.py"]