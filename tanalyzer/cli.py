import asyncio
from sqlalchemy import or_
from functools import update_wrapper

import click

import peony
from tanalyzer import schema
from tanalyzer import twitter
from tanalyzer import utils
from tanalyzer.const import DB_ENGINE


def run_async(func):

    def _func(*args, **kwargs):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(func(*args, **kwargs))

    return update_wrapper(_func, func)


@click.group()
def cli():
    pass


@cli.command()
@click.option('--consumer-key', prompt='Twitter API Consumer Key')
@click.option('--consumer-secret', prompt='Twitter API Secret Key')
@click.option('--access-token', prompt='Twitter API Access Token')
@click.option('--access-secret', prompt='Twitter API Access Secret')
@run_async
async def init(consumer_key, consumer_secret, access_token, access_secret):
    await schema.initialize()
    conn = await DB_ENGINE.connect()
    await conn.execute(schema.settings.insert().values(
        name='consumer-key', value=consumer_key))
    await conn.execute(schema.settings.insert().values(
        name='consumer-secret', value=consumer_secret))
    await conn.execute(schema.settings.insert().values(
        name='access-token', value=access_token))
    await conn.execute(schema.settings.insert().values(
        name='access-secret', value=access_secret))
    click.echo('Initialized')


async def analyze_tweets(request, conn, since_id_setting, count=0, modified=None):
    if modified is None:
        modified = {}

    since_id = await utils.get_setting(since_id_setting, conn)
    if since_id:
        request = request.get(count=200, since_id=int(since_id))
        responses = request.iterator.with_since_id()
    else:
        request = request.get(count=200)
        responses = request.iterator.with_max_id()

    first_id = None
    async for tweets in responses:
        if len(tweets) == 0:
            break
        for tweet in tweets:
            if first_id is None:
                first_id = tweet['id_str']
            count += 1
            tweet.update(modified)
            await twitter.analyze_tweet(tweet, conn)
        print('Analyzed {} tweets'.format(count))

    if first_id:
        if since_id is None:
            await conn.execute(schema.settings.insert().values(
                name=since_id_setting, value=first_id))
        else:
            await conn.execute(schema.settings.update().values(
                value=first_id).where(
                    schema.settings.c.name == since_id_setting
            ))
    return count


async def analyze_users(request, conn, count=0, override=None):
    if override is None:
        override = {}
    request = request.get(count=200)
    responses = request.iterator.with_cursor()

    async for users in responses:
        if len(users) == 0:
            break
        for user in users['users']:
            count += 1
            user.update(override)
            user['analyzed'] = True
            await twitter.analyze_user(user, conn)
        print('Analyzed {} users'.format(count))

    return count


@cli.command()
@run_async
async def update():
    # update twitter feed
    client = await twitter.get_client()
    api = client.api

    conn = await DB_ENGINE.connect()

    user = (await client.user).data
    user.update({
        'me': True,
        'analyzed': True
    })
    await twitter.analyze_user(user, conn)

    count = await analyze_users(
        api.followers.list, conn, 0, {'follower': True}
    )
    count = await analyze_users(
        api.friends.list, conn, count
    )
    print('Finish analyzing {} users'.format(count))

    count = await analyze_tweets(
        api.statuses.mentions_timeline,
        conn, 'user-mentions-last-id'
    )
    count = await analyze_tweets(
        api.statuses.user_timeline,
        conn, 'user-last-id', count=count
    )
    count = await analyze_tweets(
        api.favorites.list, conn, 'favorites-last-id',
        count=count, modified={'my_favorite': True}
    )

    print('Finish analyzing {} tweets'.format(count))

    for user in await (await conn.execute(schema.users.select(
            schema.users.c.analyzed == False))).fetchall():  # noqa
        print('Getting user {}'.format(user['screen_name']))
        try:
            user = await api.users.show.get(user_id=user['id'])
        except peony.exceptions.Forbidden as ex:
            if ex.data['errors'][0]['code'] == 63:
                # user suspended
                print('User suspended {}'.format(user['screen_name']))
                await conn.execute(schema.users.update().values(
                    suspended=True,
                    analyzed=True).where(
                        schema.users.c.id == user['id'],
                ))
                continue
            raise
        user.update({
            'analyzed': True
        })
        await twitter.analyze_user(user, conn)

    await conn.close()


@cli.command()
@click.argument('query')
@click.option('--url', type=bool, default=False, is_flag=True)
@click.option('--user', type=bool, default=False, is_flag=True)
@run_async
async def search(query, url, user):
    conn = await DB_ENGINE.connect()

    if url:
        for aurl in await (await conn.execute(schema.urls.select(
                schema.urls.c.url.like('%{}%'.format(query))))).fetchall():
            print(aurl.url)
    elif user:
        for auser in await (await conn.execute(schema.users.select(
                or_(
                    schema.users.c.screen_name.like('%{}%'.format(query)),
                    schema.users.c.name.like('%{}%'.format(query)),
                )))).fetchall():
            print('|-----------\n|')
            desc = '\n| '.join(auser.description.splitlines())
            print(f'''| @{auser.screen_name}: {auser.name}
| {desc}
| Likes: {auser.favourites_count:,}
| Friends: {auser.friends_count:,}
| Followers: {auser.followers_count:,}
| Statuses: {auser.statuses_count:,}
| Verified: {auser.verified}
| Blocked: {auser.blocking}
| Muting: {auser.muting}
| Friend: {auser.friend}
| Follower: {auser.follower}
|''')
    else:
        for tweet in await (await conn.execute(schema.tweets.select(
                schema.tweets.c.text.like('%{}%'.format(query))).order_by(
                    schema.tweets.c.created_at.desc()))).fetchall():
            user = await twitter.get_user(tweet['user_id'], conn)
            print('|-----------')
            text = '\n| '.join(tweet.text.splitlines())
            print(f'''| By: @{user.screen_name}
| On: {tweet.created_at}
| {text}''')


@cli.command()
@click.option('--polarity', type=float, default=-0.15)
@click.option('--subjectivity', type=float, default=0.5)
@run_async
async def find_trolls(polarity, subjectivity):
    '''
    Subjective but these are the criteria I've thought of:
    - negative polarity tweets
    - higher than normal number of tweets that are subjective
    - muted
    - not following but comments on your tweets

    Default constants used in queries are arbitrary/guesses
    '''

    conn = await DB_ENGINE.connect()

    me = await utils.get_me(conn)

    trolls = {}

    for tweet in await (await conn.execute('''
select tweets.user_id, users.screen_name, avg(tweets.polarity) polarity
from tweets
inner join users
where users.id = tweets.user_id and
    tweets.polarity < 0 and
    tweets.my_favorite = 0 and
    users.me = 0 and
    (users.friend = 0 or users.muting = 1) and
    tweets.in_reply_to_user_id_str = '{}'
group by tweets.user_id
having avg(tweets.polarity) < {}
order by avg(tweets.polarity)'''.format(me['id'], polarity))).fetchall():
        if await utils.num_replies_by_user(tweet['user_id'], me, conn) > 10:
            trolls[tweet.user_id] = {
                'polarity': tweet.polarity,
                'screen_name': tweet.screen_name
            }

    for tweet in await (await conn.execute('''
select tweets.user_id, users.screen_name, avg(tweets.subjectivity) subjectivity
from tweets
inner join users
where users.id = tweets.user_id and
    tweets.subjectivity > 0.1 and
    tweets.my_favorite = 0 and
    users.me = 0 and
    (users.friend = 0 or users.muting = 1) and
    tweets.in_reply_to_user_id_str = '{}'
group by tweets.user_id
having avg(tweets.subjectivity) > {}
order by avg(tweets.subjectivity)'''.format(me['id'], subjectivity))).fetchall():
        if tweet['user_id'] not in trolls:
            continue

        if await utils.num_replies_by_user(tweet['user_id'], me, conn) < 10:
            del trolls[tweet.user_id]
        else:
            trolls[tweet.user_id]['subjectivity'] = tweet.subjectivity

    for troll_id in list(trolls.keys()):
        if 'subjectivity' not in trolls[troll_id]:
            # only if the 2 intersect
            del trolls[troll_id]

    if len(trolls) == 0:
        print('No trolls found!')
    else:
        print('|---')
        print('|{} trolls found!'.format(len(trolls)))
        for troll_id, data in trolls.items():
            print('|---')
            print('''| @{screen_name}
| polarity: {polarity:.2}
| subjectivity: {subjectivity:.2}'''.format(**data))


if __name__ == '__main__':
    cli()
