""" just read and writing files """

def parse_upload_file(filename):
    identifiers = []
    activities = []
    f = open(filename, 'r')

    for line in f:
        line = line.strip()
        identifiers.append(line.split('\t')[0])
        activities.append(line.split('\t')[1])

    return identifiers, activities

