import pymongo

from ciipro_config import CIIProConfig
from rdkit import Chem


uri = "mongodb://{}:{}@{}/?authSource={}&authMechanism=SCRAM-SHA-1".format(CIIProConfig.DB_USERNAME,
                                                                           CIIProConfig.DB_PASSWORD,
                                                                           CIIProConfig.DB_SITE,
                                                                               'ciiproDBs')

client = pymongo.MongoClient(uri)






datasets = client.ciiproDBs

acute_oral = datasets.acute_oral_toxicity
hepato = datasets.hepatotoxicity
bioavail = datasets.bioavailability
bbb = datasets.BBB
oc_tox = datasets.ocular_toxicity

master = datasets.master
bit_counts = datasets.bit_counts

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

# the string return from the CIIPro app is in a different format with spaces and
# what not, so this will just convert them to the name used in the database
CIIPRO_NAME_MAPPER = {
    'Acute oral toxicity':  'acute_oral_toxicity',
    'Hepatotoxicity': 'hepatotoxicity',
    'Ocular Toxicity': 'ocular_toxicity'
}



def get_database(database):

    database = CIIPRO_NAME_MAPPER[database]

    if database != 'master':

        smiles_string = 'SMILES' if database != 'bioavailability' else 'Updated SMILES'

        results = master.find({database: {'$exists': True}}, {database: 1, '_id': 0})

        compounds = AVAILABLE_DATABASES[database].find({"_id": {"$in": [result[database] for result in results]}},
                                        {smiles_string: 1, ACTIVITY_MAPPER[database]: 1, NAME_MAPPER[database]: 1, '_id': 0})
        compounds = list(compounds)
        for compound in compounds:
            if database == 'acute_oral_toxicity':
                if compound.get(ACTIVITY_MAPPER[database], 1001) <= 1000:
                    compound['activity'] = 1
                else:
                    compound['activity'] = 0

            compound['identifier'] = compound[NAME_MAPPER[database]]

        identier_type = 'cas' if NAME_MAPPER[database] == 'CASRN' else 'smiles'

        return compounds, identier_type
