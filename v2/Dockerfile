# build
FROM alpine:latest as compiler
RUN apk add --no-cache alpine-sdk cmake curl-dev libxml2-dev
WORKDIR /build
RUN git clone https://github.com/taganaka/SpeedTest.git . \
  && cmake -DCMAKE_BUILD_TYPE=Release . \
  && make

# use
FROM alpine:latest
LABEL maintainer "NapalmZ <admin@napalmz.eu>"
LABEL version "2"

ENV TZ=Europe/Rome
# Default 300s
ENV GENERAL_DELAY=300
ENV GENERAL_OUTPUT=
# Connection to InfluxDb2
ENV INFLUX_URL=http://influxdb:8086
ENV INFLUX_TOKEN=my-token
ENV INFLUX_ORG=my-org
ENV INFLUX_BUCKET=my-bucket
# Choose server, Leave blank to auto pick server
ENV SPEEDTEST_SERVER=

RUN apk add --no-cache dumb-init libcurl libxml2 libstdc++ libgcc python3 py3-pip procps
COPY --from=compiler /build/SpeedTest /usr/local/bin/SpeedTest

VOLUME /src/
#COPY requirements.txt speed2influx.py config.ini /src/
COPY requirements.txt speed2influx.py /src/
WORKDIR /src

RUN python3 -m pip install --upgrade pip && \
    pip3 install -r requirements.txt

HEALTHCHECK --interval=1m --timeout=3s --start-period=30s --retries=3 CMD $(ps -eo etimes,comm | awk '{if ($2 == "SpeedTest" && $1 >= 300) { print "exit 1" } }')

CMD ["python3", "/src/speed2influx.py"]