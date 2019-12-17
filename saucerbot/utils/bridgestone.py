# -*- coding: utf-8 -*-

from typing import Any, Dict, List, Optional
import logging
import random
import re
import arrow
from requests.exceptions import RequestException
from arrow.parser import ParserError
from saucerbot.utils.parsers import BridgestoneEventsParser
from saucerbot.utils.parsers import BridgestoneEventTimeParser, HtmlContentProvider

logger = logging.getLogger(__name__)

__bridgestone_date_pattern = 'MMM D'
__bridgestone_time_pattern = r'h:mm[\s*]A'
__message_formats = [
    "Better get there early: {event} at Bridgestone{time} tonight!",
    "Just so you know, {event} at Bridgestone tonight{time}.",
    "Parking might be rough tonight: {event} at Bridgestone{time}",
    "WARNING! {event} at Bridgestone tonight{time}!"
]
__preds_quips = [
    "the Perds take on the {team}",
    "the {team} come to town to play the Preds",
    "your Nashville Predators are kicking some {team} butt"
]

__general_quips = [
    "Nashvillians are coming in to catch {name}",
    "{name} will be",
    "people from all over are coming to see {name}"
]

bridgestone_events_url = 'https://www.bridgestonearena.com/events'


def get_todays_events() -> List[Dict[str, Any]]:
    today = arrow.now('US/Central')
    all_events = get_all_events(HtmlContentProvider(bridgestone_events_url))
    return get_events_for_date(all_events, today)


def get_events_for_date(events: List[Dict[str, Any]], date) -> List[Dict[str, Any]]:
    results = []
    for ev in events:
        event_date = ev['parsed_date']
        if date.day == event_date.day \
                and date.month == event_date.month:
            results.append(ev)
    return results


def get_all_events(provider: HtmlContentProvider) -> List[Dict[str, Any]]:
    events = []
    for ev in BridgestoneEventsParser(provider).parse():
        try:
            ev['parsed_date'] = arrow.get(ev['date'], __bridgestone_date_pattern)
            events.append(ev)
        except ParserError:
            logger.info("Failed to parse date '%s'", ev['date'])
            # Date won't parse, just skip it
            continue
    return events


def create_message(event: Dict[str, Any]) -> str:
    template = random.choice(__message_formats)
    time_string = get_event_time(event)
    if not time_string:
        time_string = ''
    else:
        time_string = ' at ' + time_string
    preds_match = re.fullmatch('Nashville Predators vs. ([A-Za-z. ]+)', event['name'])
    if preds_match:
        team = preds_match.group(1)
        event_string = random.choice(__preds_quips).format(team=team)
    else:
        event_string = random.choice(__general_quips).format(name=event['name'])
    return template.format(event=event_string, time=time_string)


def get_event_time(event: Dict[str, Any]) -> Optional[str]:
    provider = BridgestoneEventTimeParser.create_event_time_provider(event)
    return get_event_time_helper(provider, event['name'])


def get_event_time_helper(provider: HtmlContentProvider, event_name: str) -> Optional[str]:
    try:
        parser = BridgestoneEventTimeParser(provider)
        times = list(t for t in parser.parse())
        if not times:
            logger.info('No times found for event %s', event_name)
            return None
        return arrow.get(times[0]['time'], __bridgestone_time_pattern).format('h:mm')
    except (RequestException, ParserError) as e:
        logger.info('Failed to get event info for %s', event_name, exc_info=e)
        return None
