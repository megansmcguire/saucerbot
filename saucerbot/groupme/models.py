# -*- coding: utf-8 -*-

import logging
from functools import lru_cache
from typing import Optional, Union

from django.conf import settings
from django.contrib.auth import models as auth_models
from django.core.exceptions import SuspiciousOperation
from django.db import models
from django.db.models.manager import EmptyManager
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.text import slugify
from lowerpines.endpoints.bot import Bot as LPBot
from lowerpines.endpoints.group import Group as LPGroup
from lowerpines.endpoints.message import Message
from lowerpines.endpoints.user import User as LPUser
from lowerpines.exceptions import NoneFoundException, UnauthorizedException
from lowerpines.gmi import GMI
from lowerpines.message import ComplexMessage

from saucerbot.groupme.handlers import registry
from saucerbot.utils import get_tasted_brews

logger = logging.getLogger(__name__)

SESSION_KEY = '_groupme_user_id'


@lru_cache()
def get_gmi(access_token: str) -> GMI:
    return GMI(access_token)


class User(models.Model):
    access_token: str = models.CharField(max_length=64, unique=True)
    user_id: str = models.CharField(max_length=32, unique=True)

    # User is always active
    is_active = True

    # Never staff or superuser
    is_staff = False
    is_superuser = False

    objects = models.Manager()
    _groups = EmptyManager(auth_models.Group)
    _user_permissions = EmptyManager(auth_models.Permission)

    def __str__(self):
        return self.groupme_user.name

    @cached_property
    def groupme_user(self) -> LPUser:
        return self.gmi.user.get()

    @property
    def username(self):
        return self.groupme_user.user_id

    def get_username(self):
        return self.username

    @property
    def gmi(self):
        return get_gmi(self.access_token)

    @property
    def groups(self):
        return User._groups

    @property
    def user_permissions(self):
        return User._user_permissions

    @property
    def is_anonymous(self):
        return False

    @property
    def is_authenticated(self):
        return True


class InvalidGroupMeUser(SuspiciousOperation):
    pass


def get_user(request) -> Optional[User]:
    try:
        user_id = User._meta.pk.to_python(request.session[SESSION_KEY])
        return User.objects.get(pk=user_id)
    except KeyError:
        pass
    except User.DoesNotExist:
        pass
    return None


def new_user(request, access_token: str):
    try:
        user = User.objects.get(access_token=access_token)
    except User.DoesNotExist:
        user = None

    if user is None:
        gmi = get_gmi(access_token)
        try:
            user_id = gmi.user.get().user_id
        except UnauthorizedException:
            raise InvalidGroupMeUser('Invalid access token')

        # Either create the user, or update the given user with a new access token
        defaults = {
            'access_token': access_token
        }
        user, _ = User.objects.update_or_create(user_id=user_id, defaults=defaults)

    request.session[SESSION_KEY] = str(user.pk)


def _callback_url(slug: str) -> str:
    return 'https://{}{}'.format(
        settings.SERVER_DOMAIN,
        reverse('groupme:bot-callback', kwargs={'slug': slug}),
    )


class BotManager(models.Manager):

    def create(self, **kwargs):
        owner = kwargs.get('owner')
        name = kwargs.get('name')
        slug = kwargs.get('slug')
        group = kwargs.pop('group', None)
        avatar_url = kwargs.pop('avatar_url', None)

        # Auto populate a slug if not given
        if not slug:
            slug = slugify(name)
            kwargs['slug'] = slug

        if 'bot_id' not in kwargs and owner and name and slug and group:
            callback_url = _callback_url(slug)
            bot = owner.gmi.bots.create(group, name, callback_url, avatar_url)
            kwargs['bot_id'] = bot.bot_id
            kwargs['group_id'] = group.group_id

        return super().create(**kwargs)


class Bot(models.Model):
    owner: User = models.ForeignKey(User, models.CASCADE, related_name='bots')
    bot_id: str = models.CharField(max_length=32)
    group_id: str = models.CharField(max_length=32)
    name: str = models.CharField(max_length=64)
    slug: str = models.SlugField(max_length=64, unique=True)

    objects = BotManager()

    def __str__(self):
        return f'{self.name} (slug={self.slug})'

    def __repr__(self):
        return f'Bot({self.bot_id}, {self.name}, {self.slug}, {self.owner_id})'

    @cached_property
    def bot(self) -> Optional[LPBot]:
        try:
            return self.owner.gmi.bots.get(bot_id=self.bot_id)  # pylint: disable=no-member
        except NoneFoundException:
            return None

    @cached_property
    def group(self) -> Optional[LPGroup]:
        try:
            return self.owner.gmi.groups.get(group_id=self.group_id)  # pylint: disable=no-member
        except NoneFoundException:
            return None

    def post_message(self, message: Union[ComplexMessage, str]) -> None:
        self.bot.post(message)

    def handle_message(self, message: Message) -> bool:
        other_bot_names = [b.name for b in Bot.objects.filter(group_id=self.group_id)]

        # We don't want to respond to any other bot in the same group
        if message.sender_type == 'bot' and message.name in other_bot_names:
            return False

        handler_names = [h.handler_name for h in self.handlers.all()]

        for handler in registry:
            if handler.name not in handler_names:
                continue

            logger.debug("Trying message handler %s ...", handler.name)

            matched = handler.run(self.bot, message)

            # just stop here if we matched
            if matched:
                return True

        return False

    def update_bot(self, avatar_url: Optional[str]) -> None:
        self.bot.name = self.name
        self.bot.callback_url = _callback_url(self.slug)
        self.bot.avatar_url = avatar_url
        self.bot.save()


class Handler(models.Model):
    bot: Bot = models.ForeignKey(Bot, models.CASCADE, related_name='handlers')
    handler_name: str = models.CharField(max_length=64)

    def __str__(self):
        return f'{self.bot_id} - {self.handler_name}'

    def __repr__(self):
        return f'Handler({self.bot_id}, {self.handler_name})'


class SaucerUser(models.Model):
    groupme_id: str = models.CharField(max_length=32, unique=True)
    saucer_id: str = models.CharField(max_length=32, unique=True)

    def __str__(self):
        return f'{self.saucer_id} - {self.groupme_id}'

    def __repr__(self):
        return f'SaucerUser({self.groupme_id}, {self.saucer_id})'

    def get_brews(self):
        return get_tasted_brews(self.saucer_id)


class HistoricalNickname(models.Model):
    group_id: str = models.CharField(max_length=32)
    groupme_id: str = models.CharField(max_length=32)
    timestamp = models.DateTimeField()
    nickname: str = models.CharField(max_length=256)

    def __str__(self):
        return f'{self.nickname} - {self.timestamp}'

    def __repr__(self):
        return f'HistoricalNickname({self.groupme_id}, {self.timestamp}, {self.nickname})'
