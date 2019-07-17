""" This script will run and check to make sure there is a working Mongo DB connect database connection """

import pymongo
from ciipro_config import CIIProConfig

def test_mongodb():
    try:
        client = pymongo.MongoClient(CIIProConfig.DB_SITE, 27017)
        client.test.authenticate(CIIProConfig.DB_USERNAME, CIIProConfig.DB_PASSWORD, mechanism='SCRAM-SHA-1')
        db = client.test
        print("Successfully connected to MongoDB.")
        stats = db.command("collstats", "Bioassays")
        for stat, value in stats.items():
            print("{0}: {1}".format(stat, value))
    except pymongo.errors.ServerSelectionTimeoutError as err:
        print("There was an error connecting to the MongoDB.")
        print("{0}".format(err))

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--test', dest='test', action='store_true', default=False,
                        help='tests the MongoDB connection and print basic'
                                                                    'Database stats')
    args = parser.parse_args()
    if args.test:
        test_mongodb()