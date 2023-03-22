# build
FROM alpine:latest as compiler
RUN apk add --no-cache alpine-sdk cmake curl-dev libxml2-dev
WORKDIR /build
RUN git clone https://github.com/taganaka/SpeedTest.git . \
  && cmake -DCMAKE_BUILD_TYPE=Release . \
  && make

# use
#FROM python:3.11.0a3-slim-bullseye
FROM alpine:latest
LABEL maintainer "NapalmZ <admin@napalmz.eu>"

RUN apk add --no-cache dumb-init libcurl libxml2 libstdc++ libgcc python3 py3-pip procps
#RUN apt-get update && \
#    apt-get upgrade -y && \
#    apt-get install -y dumb-init libcurl4 libxml2 libstdc++ libgcc1
COPY --from=compiler /build/SpeedTest /usr/local/bin/SpeedTest

VOLUME /src/
COPY requirements.txt speed2influx.py config.ini /src/
WORKDIR /src

RUN python3 -m pip install --upgrade pip && \
    pip3 install -r requirements.txt

HEALTHCHECK --interval=1m --timeout=3s --start-period=30s --retries=3 CMD $(ps -eo etimes,comm | awk '{if ($2 == "SpeedTest" && $1 >= 300) { print "exit 1" } }')

CMD ["python3", "/src/speed2influx.py"]