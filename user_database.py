from ciipro.routes import db
from werkzeug.security import generate_password_hash, check_password_hash
# TODO: remove this into its own module
# I was having issues with circular
# imports
class User(db.Model):
    """ sqlalchemly model for handling login information """
    tablename__ = "users"
    id = db.Column('user_id', db.Integer, primary_key=True)
    username = db.Column('username', db.String(20), unique=True, index=True)
    pw_hash = db.Column('password', db.String(10))
    email = db.Column('email', db.String(50), unique=True, index=True)

    def __init__(self, username, password, email):
        self.username = username
        self.set_password(password)
        self.email = email

    def set_password(self, password):
        """ generates and stores a password hash for a given users password. using
        werkzeug's generate_pa"""
        self.pw_hash = generate_password_hash(password, method='pbkdf2:sha1',
                                              salt_length=8)

    def check_password(self, password):
        """ checks a users password against the hash from we """
        return check_password_hash(self.pw_hash, password)

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

    def __repr__(self):
        return '<User %r>' % (self.username)

    # I added these functions,
    # very helpful to probably bring a lot of stuff into this class

    # def get_user_folder(self, folder_name):
    #
    #     # make folder if it doesnt exists
    #     folder = os.path.join(CIIProConfig.UPLOAD_FOLDER, self.username, folder_name)
    #     if not os.path.exists(folder):
    #         os.makedirs(folder)
    #     return folder
    #
    # def get_user_datasets(self, set_type="training"):
    #     """ returns the datasets for a users """
    #     return ds_io.get_datasets_names_for_user(self.get_user_folder('datasets'), set_type=set_type)
    #
    # def get_user_bioprofiles(self):
    #     """ returns profiles for a user """
    #     return ciipro_io.get_profiles_names_for_user(self.get_user_folder('profiles'))
    #
    # def get_user_fp_profiles(self):
    #     """ returns profiles for a user """
    #     return ciipro_io.get_profiles_names_for_user(self.get_user_folder('fp_profiles'))
    #
    # def load_dataset(self, ds_name):
    #
    #     """ load a dataset object given a dataset name for a user """
    #
    #     if (ds_name in self.get_user_datasets("training")) or (ds_name in self.get_user_datasets("test")):
    #         ds_json_file = os.path.join(self.get_user_folder('datasets'), '{}.json'.format(ds_name))
    #
    #         return ds.DataSet.from_json(ds_json_file)
    #
    # def load_bioprofile(self, bp_name):
    #
    #     """ load a dataset object given a dataset name for a user """
    #
    #     if bp_name in self.get_user_bioprofiles():
    #         bp_json_file = os.path.join(self.get_user_folder('profiles'), '{}.json'.format(bp_name))
    #
    #         return bp.Bioprofile.from_json(bp_json_file)
    #
    # def load_adj_matrix(self, clustering_name):
    #     adj_json_file = os.path.join(self.get_user_folder('fp_profiles'),
    #                                  '{}_adj_matrix.json'.format(clustering_name))
    #     return fp.AdjMatrix.from_json(adj_json_file)
    #
    # def load_fp_profile(self, clustering_name):
    #     fp_json_file = os.path.join(self.get_user_folder('fp_profiles'),
    #                                 '{}.json'.format(clustering_name))
    #     return fp.FPprofile.from_json(fp_json_file)


db.create_all()
