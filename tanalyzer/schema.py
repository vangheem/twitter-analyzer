import logging

from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import MetaData
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy.schema import CreateTable
from tanalyzer.const import DB_ENGINE


logger = logging.getLogger(__name__)


metadata = MetaData()
settings = Table(
    'settings', metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String, index=True, unique=True),
    Column('value', String),
)


users = Table(
    'users', metadata,
    Column('id', String, primary_key=True),
    Column('name', String, index=True),
    Column('screen_name', String, index=True),

    Column('description', String, index=True),
    Column('location', String, index=True),
    Column('favourites_count', Integer, index=True),
    Column('friends_count', Integer, index=True),
    Column('followers_count', Integer, index=True),
    Column('statuses_count', Integer, index=True),
    Column('listed_count', Integer, index=True),
    Column('verified', Boolean, index=True),
    Column('protected', Boolean, index=True),
    Column('blocked_by', Boolean, index=True),
    Column('blocking', Boolean, index=True),
    Column('contributors_enabled', Boolean, index=True),
    Column('follow_request_sent', Boolean, index=True),
    Column('muting', Boolean, index=True),
    Column('live_following', Boolean, index=True),

    Column('friend', Boolean, index=True),
    Column('follower', Boolean, index=True),
    Column('me', Boolean, index=True),

    Column('analyzed', Boolean, index=True),
    Column('suspended', Boolean, index=True),
)


tweets = Table(
    'tweets', metadata,
    Column('id', String, primary_key=True),
    Column('user_id', String, ForeignKey(users.c.id)),

    Column('favorite_count', Integer, index=True),
    Column('favorited', Boolean, index=True),
    Column('my_favorite', Boolean, index=True),
    Column('in_reply_to_status_id', String, nullable=True),
    Column('in_reply_to_user_id_str', String, nullable=True),
    Column('retweet_count', Integer, index=True),
    Column('retweeted', Boolean, index=True),
    Column('text', String, index=True),
    Column('created_at', DateTime, index=True),

    Column('polarity', Float, index=True),
    Column('subjectivity', Float, index=True),
)

urls = Table(
    'urls', metadata,
    Column('id', Integer, primary_key=True),
    Column('url', String, index=True),
    Column('domain', String, index=True),
    Column('tweet_id', String, ForeignKey(tweets.c.id))
)

mentions = Table(
    'mentions', metadata,
    Column('id', Integer, primary_key=True),
    Column('tweet_id', String, ForeignKey(tweets.c.id)),
    Column('user_id', String, ForeignKey(users.c.id))
)


async def initialize():
    await DB_ENGINE.execute(CreateTable(settings))
    await DB_ENGINE.execute(CreateTable(users))
    await DB_ENGINE.execute(CreateTable(tweets))
    await DB_ENGINE.execute(CreateTable(urls))
    await DB_ENGINE.execute(CreateTable(mentions))
