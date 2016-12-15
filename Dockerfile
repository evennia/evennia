FROM python:2.7-alpine
MAINTAINER Dan Feeney "feend78@gmail.com"
RUN apk update && apk add gcc musl-dev
ADD . /usr/src/evennia
RUN pip install -e /usr/src/evennia
ONBUILD ADD . /usr/src/game
VOLUME /usr/src/game
WORKDIR /usr/src/game
CMD ["evennia", "-l", "-i", "start"]
EXPOSE 8000 8001 4000
