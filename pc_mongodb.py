"""  Module for code to interact with the PubChem data stored on CIIPro """

import pymongo
from pymongo.collection import Collection

from ciipro_config import CIIProConfig

client = pymongo.MongoClient(CIIProConfig.DB_SITE, 27017)

# if in development mode theres no password/usernmane
if (CIIProConfig.DB_USERNAME and CIIProConfig.DB_PASSWORD):
    client.pubchem.authenticate(CIIProConfig.DB_USERNAME, CIIProConfig.DB_PASSWORD, mechanism='SCRAM-SHA-1')



# connect to db, then each collection individually
pubchem = client.pubchem

### collections


# synonyms contain

class PCCollection:

    def __init__(self, collection_ob: Collection):
        self.col_ob = collection_ob

    def query_list(self, query_list, query_field,
                   return_fields_list, return_id=False, return_query=True):

        # TODO: make a copy of the outcomes database and convert all to integers
        # TODO: so we can remove this conversion
        # quick fix for querying the outcomes DB which are all in strings
        # need to convert the CIDS to strings

        field_type = type(self.col_ob.find_one()[query_field])
        if field_type == str:
            query_list = list(map(str, query_list))

        query = {"{}".format(query_field): {"$in": query_list}}

        return_fields = {}

        # turn on return fields
        for field in return_fields_list:
            return_fields[field] = 1

        if return_query:
            return_fields[query_field] = int(return_query)

        return_fields['_id'] = int(return_id)

        return list(self.col_ob.find(query, return_fields))


compounds_db = PCCollection(pubchem.compounds)
synonyms_db = PCCollection(pubchem.synonyms)
outcomes_db = PCCollection(pubchem.outcomes)
bioassays_db = PCCollection(pubchem.bioassay)

# print(outcomes_db.query_list([2244], 'CID', ['AID', 'Outcome']))

# TEST_CMPS_IN = ['N-[3-keto-3-[(4-phenylthiazol-2-yl)amino]propyl]thiophene-2-carboxamide', 'N-[4-keto-4-[(4-phenylthiazol-2-yl)amino]butyl]thiophene-2-carboxamide', '3-(dimethylsulfamoyl)-N-ethyl-N-phenyl-benzamide']
# TEST_CMPS_name = ['acetylcarnitine', 'O-acetylcarnitine', '2,3-dihydro-2,3-dihydroxybenzoic acid']
# CAS = ['50-78-2', '64-19-7', '62-31-7']
#
# print(synonyms.query_list(CAS, 'Synonym', ['CID']))
# print(synonyms.col_ob.find_one())

