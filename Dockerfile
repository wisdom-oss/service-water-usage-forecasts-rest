FROM python:3.10-slim
# Set some labels
LABEL de.uol.wisdom-oss.vendor="WISdoM 2.0 Project Group"
LABEL de.uol.wisdom-oss.maintainer="wisdom@uol.de"
LABEL de.uol.wisdom-oss.service-name="water-usage-forecast-rest"

WORKDIR /opt/water-usage-forecast-rest
# Copy and install the requirements
COPY . /opt/water-usage-forecast-rest
RUN python -m pip install -r /opt/water-usage-forecast-rest/requirements.txt
RUN python -m pip install gunicorn
RUN ls

EXPOSE 5000
ENTRYPOINT ["gunicorn", "-cgunicorn.config.py", "api:service"]
