FROM python:3.9-slim
# Set some labels
LABEL de.uol.wisdom-oss.vendor="WISdoM 2.0 Project Group"
LABEL de.uol.wisdom-oss.maintainer="wisdom@uol.de"
LABEL de.uol.wisdom-oss.service-name="water-usage-forecast-rest"

# Create a user for the service execution
RUN addgroup --system water-usage-forecast-rest && \
    adduser --home /opt/water-usage-forecast-rest --system --gecos "" water-usage-forecast-rest --ingroup water-usage-forecast-rest

WORKDIR /opt/water-usage-forecast-rest
# Copy and install the requirements
COPY . /opt/water-usage-forecast-rest
RUN python -m pip install -r /opt/water-usage-forecast-rest/requirements.txt
# Switch to the just created user and into the home directory
USER water-usage-forecast-rest

# Expose port used by hypercorn 5000
EXPOSE 5000
ENTRYPOINT ["hypercorn", "-b0.0.0.0:5000", "-w8", "-kuvloop", "api:water_usage_forecasts_rest"]
