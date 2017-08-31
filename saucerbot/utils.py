# -*- coding: utf-8 -*-

import logging
import os

import requests


API_URL = 'https://api.groupme.com/v3'
BOT_ID = os.environ['BOT_ID']

logger = logging.getLogger(__name__)


def send_message(text, **kwargs):
    message = {
        'bot_id': BOT_ID,
        'text': text,
    }

    message.update(kwargs)

    r = requests.post('{}/bots/post'.format(API_URL), json=message)

    if r.status_code != 201:
        logger.debug('Message failed to send: {}'.format(r.text))

    return r.status_code == 201
