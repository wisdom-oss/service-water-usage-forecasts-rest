FROM python:3.10-slim
LABEL vendor="WISdoM 2.0 Project Group"
LABEL maintainer="wisdom@uol.de"
# Do not change this variable. Use the environment variables in docker compose or while starting to modify this value
ENV CONFIG_SERVICE_NAME="water-usage-forecasts"
ENV CONFIG_HTTP_PORT=5000
EXPOSE $CONFIG_HTTP_PORT
WORKDIR /service
COPY . /service
RUN python -m pip install -r /service/requirements.txt
RUN python -m pip install gunicorn
RUN python -m pip install uvicorn
RUN ln ./configuration/gunicorn.py gunicorn.config.py
ENTRYPOINT ["gunicorn", "-cgunicorn.config.py", "api:service"]
