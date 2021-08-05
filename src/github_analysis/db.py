import typing

from decouple import config
import pymongo

db_user = config('MONGO_ROOT_USER', default=None)
db_pass = config('MONGO_ROOT_PASSWORD', default=None)

if db_user and db_pass:
    database_url = config('DATABASE_URL', default=f'mongodb://{db_user}:{db_pass}@localhost:27017/')
else:
    database_url = config('DATABASE_URL', default='mongodb://localhost:27017/')

client = pymongo.MongoClient(database_url)
db = client['github']


def collection(name: str, indexes: typing.Optional[typing.Iterable[str]] = None):
    collection = db[name]

    if indexes is None:
        indexes = set()

    indexes = {'_repo_name', 'node_id'}.union(indexes)
    for index in indexes:
        collection.create_index(index)

    return collection
