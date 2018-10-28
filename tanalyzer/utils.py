from tanalyzer import schema
from tanalyzer.const import DB_ENGINE


async def get_conn():
    return await DB_ENGINE.connect()


async def get_setting(setting_name, conn=None):
    if conn is None:
        conn = await get_conn()
    result = await conn.execute(schema.settings.select(
        schema.settings.c.name == setting_name))
    setting = await result.fetchone()
    if setting is not None:
        return setting['value']


async def get_settings(*args, conn=None):
    if conn is None:
        conn = await get_conn()
    data = {}
    for setting_name in args:
        value = await get_setting(setting_name, conn)
        if value is not None:
            data[setting_name] = value
        else:
            raise Exception('Missing setting {}'.format(setting_name))
    return data


async def get_me(conn):
    return await (await conn.execute(schema.users.select(
        schema.users.c.me == True))).fetchone()  # noqa


async def num_replies_by_user(user_id, me, conn):
    result = await (await conn.execute('''
select count(*)
from tweets
where tweets.user_id = '{}' and
tweets.in_reply_to_user_id_str = '{}'
'''.format(user_id, me.id))).fetchone()
    return result[0]
