import pymongo
from api.api_config import DB_USR, PSWD, ADDRESS, AUTH_DB


uri = "mongodb://{}:{}@{}/?authSource={}&authMechanism=SCRAM-SHA-1".format(DB_USR,
                                                                               PSWD,
                                                                               ADDRESS,
                                                                               AUTH_DB)
client = pymongo.MongoClient(uri)

datasets = client.ciiproDBs

acute_oral = datasets.acute_oral_toxicity
hepato = datasets.hepatotoxicity
bioavail = datasets.bioavailability
bbb = datasets.BBB
oc_tox = datasets.ocular_toxicity

master = datasets.master


AVAILABLE_DATABASES = {
    'bbb': bbb,
    'acute_oral_toxicity': acute_oral,
    'hepatotoxicity': hepato,
    'bioavailability': bioavail,
    'ocular_toxicity': oc_tox
}

ACTIVITY_MAPPER = {
    'bbb': 'logBB',
    'acute_oral_toxicity': 'LD50_mgkg',
    'hepatotoxicity': 'majority_def',
    'bioavailability': 'logK(%F)',
    'ocular_toxicity': 'Composite category'
}

NAME_MAPPER = {
    'bbb': 'CID',
    'acute_oral_toxicity': 'CASRN',
    'hepatotoxicity': 'ID',
    'bioavailability': 'Name',
    'ocular_toxicity': 'CASRN '
}