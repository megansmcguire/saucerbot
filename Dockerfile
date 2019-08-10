FROM python:3.7-alpine

# These don't get removed, so install them first separately
RUN apk add --no-cache curl postgresql-libs

ENV PYTHONUNBUFFERED 1
ENV PIP_NO_CACHE_DIR off

# Passing the -h /app will set that as the home dir & chown it
RUN addgroup -S saucerbot && adduser -D -S -g saucerbot -G saucerbot -h /app saucerbot

WORKDIR /app

COPY --chown=saucerbot:saucerbot Pipfile Pipfile.lock manage.py /app/

# Install all the deps & uninstall build-time reqs all in one step to reduce image size
RUN apk add --no-cache --virtual .build-deps gcc g++ postgresql-dev && \
    pip install pipenv && \
    pipenv install --deploy --system && \
    pip uninstall -y pipenv virtualenv virtualenv-clone && \
    apk --purge del .build-deps


# Copy all the code & generate the static files
COPY --chown=saucerbot:saucerbot saucerbot saucerbot

USER saucerbot

RUN python -m compileall saucerbot

# Build static files
RUN DJANGO_ENV=build HEROKU_APP_NAME=build python manage.py collectstatic --noinput

CMD ["gunicorn", "saucerbot.wsgi"]
