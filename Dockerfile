FROM python:3.10-alpine
# Set some labels
LABEL de.uol.wisdom-oss.vendor="WISdoM 2.0 Project Group"
LABEL de.uol.wisdom-oss.maintainer="wisdom@uol.de"
LABEL de.uol.wisdom-oss.service-name="water-usage-forecast-rest"

WORKDIR /opt/water-usage-forecast-rest
# Copy and install the requirements
COPY . /opt/water-usage-forecast-rest
RUN python -m pip install -r /opt/water-usage-forecast-rest/requirements.txt

EXPOSE 5000
ENTRYPOINT ["python", "service.py"]
