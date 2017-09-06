# -*- coding: utf-8 -*-

import json
import logging

from flask import request
from flask.json import jsonify

from saucerbot import app

logger = logging.getLogger(__name__)


@app.route('/hooks/groupme/', methods=['POST'])
def groupme():
    message = request.get_json(force=True)

    logger.info('Received raw message: {}'.format(json.dumps(message)))

    # Load it as a groupme message
    message = app.group.bot_message(message)

    # We don't want to accidentally respond to ourself
    if message.sender_type == 'bot' and message.name == 'saucerbot':
        return jsonify({})

    # Call all our handlers
    for handler in app.handlers:
        logger.debug('Trying message handler {} ...'.format(handler.func.__name__))

        if handler.re:
            re_func = getattr(handler.re, handler.type)
            text = message.text
            if not handler.case_sensitive:
                text = text.lower()
            match = re_func(text)
            if match:
                handler.func(message, match)
                res = True
            else:
                res = False
        else:
            res = handler.func(message)

        # Stop the rest of the handlers
        if res and handler.short_circuit:
            break

    response = {
        'ok': True
    }

    return jsonify(response)
