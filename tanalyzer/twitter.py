from urllib.parse import urlparse

import sqlalchemy
from dateutil.parser import parse
from peony import PeonyClient
from tanalyzer import schema
from tanalyzer import utils
from textblob import TextBlob


async def get_client():
    settings = await utils.get_settings(
        'consumer-key',
        'consumer-secret',
        'access-token',
        'access-secret')

    return PeonyClient(
        consumer_key=settings['consumer-key'],
        consumer_secret=settings['consumer-secret'],
        access_token=settings['access-token'],
        access_token_secret=settings['access-secret'])


_user_cache = {}


async def get_user(user_id, conn=None):
    if user_id in _user_cache:
        return _user_cache[user_id]
    if conn is None:
        conn = await utils.get_conn()
    result = await conn.execute(schema.users.select(
        schema.users.c.id == user_id))
    value = await result.fetchone()
    _user_cache[user_id] = value
    return value


async def get_user_or_create_user(data, conn=None, update=False):
    twitter_id = data['id_str']
    if twitter_id in _user_cache:
        return _user_cache[twitter_id]

    if conn is None:
        conn = await utils.get_conn()
    result = await conn.execute(schema.users.select(
        schema.users.c.id == twitter_id))
    value = await result.fetchone()
    kwargs = dict(
        name=data['name'],
        screen_name=data['screen_name'],
        description=data.get('description') or '',
        location=data.get('location') or '',
        favourites_count=data.get('favourites_count') or 0,
        friends_count=data.get('friends_count') or 0,
        followers_count=data.get('followers_count') or 0,
        statuses_count=data.get('statuses_count') or 0,
        listed_count=data.get('listed_count') or 0,
        verified=data.get('verified') or False,
        protected=data.get('protected') or False,
        blocked_by=data.get('blocked_by') or False,
        blocking=data.get('blocking') or False,
        contributors_enabled=data.get('contributors_enabled') or False,
        follow_request_sent=data.get('follow_request_sent') or False,
        muting=data.get('muting') or False,
        live_following=data.get('live_following') or False,

        friend=data.get('following') or False,
        follower=data.get('follower') or False,
        me=data.get('me') or False,

        analyzed=data.get('analyzed') or False,
        suspended=False
    )
    if value is None:
        await conn.execute(schema.users.insert().values(
            id=data['id_str'], **kwargs))
        return await get_user_or_create_user(data, conn)
    elif update:
        await conn.execute(schema.users.update().values(
            **kwargs).where(
                schema.users.c.id == data['id_str']
        ))
    _user_cache[twitter_id] = value
    return value


async def analyze_tweet(data, conn=None):
    if conn is None:
        conn = await utils.get_conn()
    user = await get_user_or_create_user(data['user'], conn)

    tb = TextBlob(data['text'])

    kwargs = dict(
        user_id=user['id'],
        favorite_count=data['favorite_count'],
        favorited=data['favorited'],
        my_favorite=data.get('my_favorite') or False,
        in_reply_to_status_id=data['in_reply_to_status_id_str'],
        in_reply_to_user_id_str=data['in_reply_to_user_id_str'],
        retweet_count=data['retweet_count'],
        retweeted=data['retweeted'],
        text=data['text'],
        created_at=parse(data['created_at']),

        polarity=tb.polarity,
        subjectivity=tb.subjectivity)
    try:
        await conn.execute(schema.tweets.insert().values(
            id=data['id_str'],
            **kwargs
        ))
    except sqlalchemy.exc.IntegrityError:
        # if we've already analyzed, update and then ignore rest
        await conn.execute(schema.tweets.update().values(
            **kwargs).where(
                schema.tweets.c.id == data['id_str']
        ))
        return

    for url in data['entities']['urls']:
        parsed = urlparse(url['expanded_url'])
        await conn.execute(schema.urls.insert().values(
            url=url['expanded_url'],
            domain=parsed.netloc,
            tweet_id=data['id_str']))
    for mention in data['entities']['user_mentions']:
        await get_user_or_create_user(mention, conn)
        await conn.execute(schema.mentions.insert().values(
            tweet_id=data['id_str'],
            user_id=mention['id_str']))


async def analyze_user(data, conn=None):
    if conn is None:
        conn = await utils.get_conn()
    await get_user_or_create_user(data, conn, update=True)
