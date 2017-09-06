# -*- coding: utf-8 -*-

import datetime
import logging
import os
import re

from elasticsearch import Elasticsearch
import requests

from saucerbot.parsers import NewArrivalsParser

# This url is specific to nashville
BREWS_URL = 'https://www.beerknurd.com/api/brew/list/13886'
TASTED_URL = 'https://www.beerknurd.com/api/tasted/list_user/{}'

logger = logging.getLogger(__name__)

ABV_RE = re.compile(r'(?P<abv>[0-9]+(\.[0-9]+)?)%')


def get_es_client():
    return Elasticsearch(os.environ['BONSAI_URL'])


def get_tasted_brews(saucer_id):
    r = requests.get(TASTED_URL.format(saucer_id))
    return r.json()


def load_beers_into_es():
    es = get_es_client()

    # Make sure the template is there
    es.indices.put_template(
        'beers',
        {
            'template': 'beers-*',
            'mappings': {
                'beer': {
                    'properties': {
                        'name': {'type': 'text'},
                        'store_id': {'type': 'keyword'},
                        'brewer': {'type': 'text'},
                        'city': {'type': 'text'},
                        'country': {'type': 'text'},
                        'container': {'type': 'keyword'},
                        'style': {'type': 'text'},
                        'description': {'type': 'text'},
                        'stars': {'type': 'long'},
                        'reviews': {'type': 'long'},
                        'abv': {'type': 'float'},
                    }
                }
            }
        }
    )

    beers = requests.get(BREWS_URL).json()

    now = datetime.datetime.today()

    index_name = 'beers-nashville-{}'.format(now.strftime('%Y%m%d-%H%M%S'))

    # Manually create the index
    es.indices.create(index_name)

    # index all the beers
    for beer in beers:
        beer_id = beer.pop('brew_id')
        beer['reviews'] = int(beer['reviews'])
        if not beer['city']:
            beer.pop('city')
        if not beer['country']:
            beer.pop('country')
        abv_match = ABV_RE.search(beer['description'])
        if abv_match:
            beer['abv'] = float(abv_match.group('abv'))
        es.index(index_name, 'beer', beer, beer_id)

    alias_actions = []

    # Remove old indices
    if es.indices.exists_alias(name='beers-nashville'):
        old_indices = es.indices.get_alias(name='beers-nashville')
        for index in old_indices:
            alias_actions.append({
                'remove_index': {'index': index},
            })

    # Add the new index
    alias_actions.append({
        'add': {'index': index_name, 'alias': 'beers-nashville'},
    })

    # Perform the update
    es.indices.update_aliases({'actions': alias_actions})


def get_new_arrivals():
    parser = NewArrivalsParser()

    beers = parser.parse()

    return '\n'.join(x['name'] for x in beers)
