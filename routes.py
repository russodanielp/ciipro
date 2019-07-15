# -*- coding: utf-8 -*-
import os
import ntpath

from flask import Flask, render_template, flash, session, \
    redirect, url_for, g, send_file, request
from flask_login import login_user, logout_user, current_user, login_required, LoginManager
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sql import passwordRetrieval, usernameRetrieval, passwordReset
from CIIProTools import *
from ciipro_config import CIIProConfig
import json
from BioSimLib import *
#import urllib
import zipfile
import sqlalchemy.ext

from datasets_io import write_ds_to_json
import pandas as pd

import ciipro_io

import datasets_io as ds_io
import datasets as ds

import bioprofiles as bp


# TODO: go through each module and identifiy and take out passwords, security crucial information

# These variables are configured in CIIProConfig
# TODO: put all this in a true config file
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = CIIProConfig.UPLOAD_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.secret_key = CIIProConfig.APP_SECRET_KEY
app.config['RECAPTCHA_PRIVATE_KEY'] = CIIProConfig.RECAPTCHA_PRIVATE_KEY



db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


class User(db.Model):
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
        self.pw_hash = generate_password_hash(password, method='pbkdf2:sha1', 
                                              salt_length=8)
        
    def check_password(self, password):
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


    # I added these functions

    def get_user_folder(self, folder_name):

        # make folder if it doesnt exists
        folder = os.path.join(CIIProConfig.UPLOAD_FOLDER, self.username, folder_name)
        if not os.path.exists(folder):
            os.makedirs(folder)
        return folder

    def get_user_datasets(self, set_type="training"):
        """ returns the datasets for a users """
        return ds_io.get_datasets_names_for_user(self.get_user_folder('datasets'), set_type=set_type)

    def get_user_bioprofiles(self, set_type="training"):
        """ returns profiles for a user """
        return ciipro_io.get_profiles_names_for_user(self.get_user_folder('profiles'))


    def load_dataset(self, ds_name):

        """ load a dataset object given a dataset name for a user """

        if (ds_name in self.get_user_datasets("training")) or (ds_name in self.get_user_datasets("test")):
            ds_json_file = os.path.join(self.get_user_folder('datasets'), '{}.json'.format(ds_name))

            return ds.DataSet.from_json(ds_json_file)


    def load_bioprofile(self, bp_name):

        """ load a dataset object given a dataset name for a user """

        if bp_name in self.get_user_bioprofiles():
            bp_json_file = os.path.join(self.get_user_folder('profiles'), '{}.json'.format(bp_name))

            return bp.Bioprofile.from_json(bp_json_file)
    
db.create_all()
@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

@app.after_request
def add_header(response):
    """
    Add headers to both force latest IE rendering engine or Chrome Frame,
    and also to cache the rendered page for 10 minutes.
    """
    response.headers['X-UA-Compatible'] = 'IE=Edge,chrome=1'
    response.headers['Cache-Control'] = 'public, max-age=0'
    return response


@app.route('/') 
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
        
    username = request.form['username'].strip()
    password = request.form['password'].strip()
    registered_user = User.query.filter_by(username=username).first()
    
    if registered_user is None:
        flash('Username does not exist', 'danger')
        return redirect(url_for('login'))
       
    if registered_user.check_password(password) == False:
        flash('Password does not match user', 'danger')
        return redirect(url_for(''))
    
    login_user(registered_user)
    flash('Logged in successfully', 'info')
    return redirect(request.args.get('next') or url_for('home'))

@app.route('/logout')
@login_required
def logout():
    """ Logs out user and returns them to the homepage.
    
    """
    
    session.pop('compound_file', None)
    logout_user()
    flash('Logged out successfully')
    return redirect(url_for('home'))

def checkRecaptcha(response, secretkey):
    """ Checks the response to the recaptcha entry on the login page. Returns True if response == recaptcha diplayed
        on the website.
    
    response (str): User supplied recaptcha key.
    secretkey (str): Secret key for the site supplied by Google.
    """
    url = 'https://www.google.com/recaptcha/api/siteverify?'      
    url = url + 'secret=' + secretkey
    url = url + '&response=' + response
    try:
        jsonobj = json.loads(urllib.request.urlopen(url).read().decode('utf-8'))
        if jsonobj['success']:
            return True
        else:
            return False
    except Exception as e:
        print(e)

        return False
      
      
@app.route('/register', methods=['GET', 'POST']) 
def register():
    """ Registers a new user.  checkRecaptcha() must return True to register user.
        Upon successful registration, creates root directory. And four subdirectory folders:
            
            Username
               ├───compounds
               ├───biosims
               ├───profiles
               └───converter   
    """
    if request.method == 'GET':
        return render_template('register.html')

    try:
        user = User(request.form['username'], request.form['password'], request.form['email'])
    except sqlalchemy.exc.IntegrityError as e:
        flash('Sorry, either user exists with that username or email.', 'danger')
    recaptcha = request.form['g-recaptcha-response']
    if checkRecaptcha(recaptcha, CIIProConfig.SECRET_KEY):
        db.session.add(user)
        db.session.commit()
        directory = CIIProConfig.UPLOAD_FOLDER + '/' + str(user.username)
        if not os.path.exists(directory):
            os.makedirs(directory)
            sub_folders = ["compounds", "biosims", "profiles", "converter", "test_sets", "NNs", "datasets"]
            for sf in sub_folders:
                sub_directory = directory + '/' + sf
                os.makedirs(sub_directory)
        flash('User successfully registered')
    else:
        flash('Registration failed', 'danger')
    return redirect(url_for('login'))

@app.route('/passwordrecovery', methods=['GET', 'POST']) 
def passrecov():
    """ Checks to see if an email is associated with a user to recover password.  If so, returns emailsent.html.
  
    """
    if request.method == 'GET':
        return render_template('passwordrecovery.html')
    
    if request.method == 'POST':
        email = request.form['email']
        response = passwordRetrieval(email, User, db)
        if response == "No email":
            error = "No user associated with that email, please register"
            return render_template('passwordrecovery.html')
        else:
            return render_template('emailsent.html')

@app.route('/usernamerecovery', methods=['GET', 'POST']) 
def usernamerecov():
    """ Checks to see if an email is associated with a user to recover username.  If so, returns emailsent.html.
  
    """
    if request.method == 'GET':
        return render_template('usernamerecovery.html')
    if request.method == 'POST':
        email = request.form['email']
        response = usernameRetrieval(email, User, db)
        if response == "No email":
            error = "No user associated with that email, please register"
            return render_template('passwordrecovery.html', error=error)
        else:
            return render_template('emailsent.html')            

@app.route('/passreset', methods=['GET', 'POST'])
def passreset():
    """ Resets a users password.
    
    """
    if request.method == 'GET':
        return render_template('passreset.html')
    
    if request.method == 'POST':
        username = request.form['username']
        temp_password = request.form['temp_password']
        new_password = request.form['new_password']
        conf_password = request.form['conf_password']
        
        if new_password != conf_password:
            flash('New Password and confirmation don\'t match', 'danger')
            return render_template('passreset.html')
        
        response = passwordReset(username, temp_password, new_password, User, db)
        if response == 'Password succesfully changed':
            registered_user = User.query.filter_by(username=username).first()
            login_user(registered_user)
            flash(response, 'info')
            return render_template('home.html')
        
        return render_template('passreset.html')
   
        
@app.before_request
def before_request():
    g.user = current_user

@app.route('/tutorial')
def tutorial():
    return render_template('tutorial.html')

@app.route('/sendbiopro')
def sendbiopro():
      return render_template('StatsGlossary.html')

@app.route('/sendbiosim')
def sendbiosim():
      return send_file('tutorial_samples/BioSim.txt', as_attachment=True)      

@app.route('/sendbioconf')
def sendbiosimconf():
      return send_file('tutorial_samples/BioSim_Conf.txt', as_attachment=True)      

@app.route('/sendbionn')
def sendbionn():
      return send_file('tutorial_samples/Bioneighbor.txt', as_attachment=True)
      
@app.route('/sendactivity')
def sendactivity():
      return send_file('tutorial_samples/Activity.txt', as_attachment=True)
      
@app.route('/sendbiopred')
def sendbiopred():
      return send_file('tutorial_samples/BioPred.txt', as_attachment=True)


@app.route('/statsglossary')
def statsglossary():
    """ Displays statsglossary page. 
    
    """    
    return render_template('statsglossary.html')
    
@app.route('/datasets', methods=['GET', 'POST'])
@login_required
def datasets():
    """ Displays datasets page with all available datasets in users compound folder. 
    
    """
    username = g.user.username
    return render_template('datasets.html', datasets=g.user.get_user_datasets(set_type='training'), testsets=g.user.get_user_datasets(set_type='test'),
                          username=username)
                           
                           
@app.route('/uploaddataset', methods=['POST', 'GET'])
@login_required
def uploaddataset():
    """ Uploads a file from user and saves to users' compounds folder.  Converts non-PubChem CID identifiers to CIDS using 
        PubChem's PUG Rest.
        
        Requests:
            input_type (str): radio button from page
            compound_file: user file upload, first column should be compounds, second should be activity.
            model_type: training or test set upload
    """
   

    
    username = g.user.username

    # requests
    input_type = request.form['input_type'].lower()
    file = request.files['compound_file']
    model_type = request.form['model_type']
    
    if file and allowed_file(file.filename):
        compound_filename = secure_filename(file.filename)

        user_datasets_folder = g.user.get_user_folder('datasets')


        user_uploaded_file = os.path.join(user_datasets_folder, compound_filename)

        # make the name of the dataset just the basename of the file

        name = ntpath.basename(user_uploaded_file).split('.')[0]

        # I think we have to save this in order to use it, not sure if we car read it otherwise
        file.save(user_uploaded_file)

        # TODO: Need to write some checks to make sure everything in the uploaded dataset is good
        # TODO: Things like all activies are there, columns match, etc
        # TODO: the following type conversions are necessary for JSON serialization

        identifiers, activities = ciipro_io.parse_upload_file(user_uploaded_file)

        activities = list(map(int, activities))

        if input_type == 'cid':
            identifiers = list(map(int, identifiers))
        else:
            identifiers = list(map(str, identifiers))

        ds_io.write_ds_to_json(identifiers, activities, user_datasets_folder, name, input_type, set_type=model_type)
        os.remove(user_uploaded_file)

        return redirect(url_for('datasets'))  
    else:
        error = "Please attach file"
        return render_template('datasets.html',
                               datasets=g.user.get_user_datasets(set_type='training'),
                               testsets=g.user.get_user_datasets(set_type='test'),
                               username=username, error=error)
     

@app.route('/deletetestset', methods=['POST'])
@login_required
def deletetestset():
    """ Deletes a test set from a users' test sets folder.  
    
        Requests:
            testset_filename (str): radiobutton from datasets page.  
    """
    USER_TEST_SETS_FOLDER = CIIProConfig.UPLOAD_FOLDER + '/' + g.user.username + '/test_sets'

    username = g.user.username
    testset_filename = request.form['testset_filename']
    testset_filename = str(testset_filename)
    os.remove(USER_TEST_SETS_FOLDER  + '/' + testset_filename)
    return redirect(url_for('datasets'))  
                            
@app.route('/deletedataset', methods=['POST', 'GET'])
@login_required
def deletedataset():
    """ Deletes a dataset from a users' compounds folder.  
    
        Requests:
            compound_filename (str): radiobutton from datasets page.  
    """
    USER_TEST_SETS_FOLDER = CIIProConfig.UPLOAD_FOLDER + '/' + g.user.username + '/test_sets'
    USER_COMPOUNDS_FOLDER = CIIProConfig.UPLOAD_FOLDER + '/' + g.user.username + '/compounds'
    username = g.user.username
    compound_filename = request.form['compound_filename']
    compound_filename = str(compound_filename)
    os.remove(USER_COMPOUNDS_FOLDER + '/' + compound_filename)
    
    datasets = [ds for ds in os.listdir(USER_COMPOUNDS_FOLDER)]
    testsets = [ts for ts in os.listdir(USER_TEST_SETS_FOLDER)]

    return render_template('datasets.html', datasets=g.user.get_user_datasets(set_type='training'), testsets=g.user.get_user_datasets(set_type='test'),
                            username=username)                            

@app.route('/CIIProfiler') 
@login_required
def CIIProfiler():
    """ Displays CIIProfiler page with all available datasets in users compound folder.
    
    """
    return render_template('CIIProfiler.html', username=g.user.username, datasets=g.user.get_user_datasets(set_type='training'))


@app.route('/CIIPPredictor') 
@login_required
def CIIPPredictor():
    """ Displays CIIPBioNN page with all available profiles in users' profile folder.
    
    """

    return render_template('CIIPPredictor.html', profiles=g.user.get_user_bioprofiles(),
                           username=g.user.username, testsets=g.user.get_user_datasets(set_type='test'))	


# TODO Create a save button to save optimized profile, allow for name
@app.route('/optimizeprofile')
@login_required
def optimizeprofile():
    """ Renderts optimize bioprofile
    """
    profile = bioprofile_to_pandas(session['cur_prof_dir'])
    stats_df = pd.read_csv(session['cur_assay_dir'], sep='\t', index_col=0)
    stats = dataTable_bokeh(stats_df)
    hm = bokehHeatmap(profile)


    return render_template('optimizeprofile.html',
                           hm=hm,
                           stats=stats,
                           aids=profile.columns.tolist()
                           )

def allowed_file(filename): #method that checks to see if upload file is allowed
    return '.' in filename and filename.rsplit('.', 1)[1] in CIIProConfig.ALLOWED_EXTENSIONS

@app.route('/optimizeassays', methods=['POST'])
@login_required
def removeassays():
    remove_or_keep = request.form['Remove_or_Keep']
    assays = list(map(int, request.form.getlist('aids')))
    profile = bioprofile_to_pandas(session['cur_prof_dir'])
    if remove_or_keep == 'Remove':
        profile.drop(assays, axis=1, inplace=True)
    else:
        profile = profile[assays]

    new_name = session['cur_prof_dir'].replace('.txt',
                                               '_optimized.txt')

    profile.to_csv(new_name, sep='\t')
    profile.to_csv(new_name.replace('biosims', 'profiles'), sep='\t')

    session['cur_prof_dir'] = new_name
    return redirect(url_for('optimizeprofile'))

@app.route('/ciiprofile',  methods=['POST'])
@login_required
def CIIProfile():
    """ Creates a bioprofile from a users selected dataset.  If the bioprofile is not too large, will create a 
        heatmap to display on the website.  
    
        Requests:
            compound_filename (str): Selected dataset from radio button.  
            noOfActives (str): String number of minumum actives per assays from pull down.
            profile_filename (str): Name of profile that will be generated. From text field. 
            sort_by: Column to sort in vitro, in vivo correlations by
                
    """

    if request.method == 'POST':

        ds_name = str(request.form['compound_filename'])
        ds = g.user.load_dataset(ds_name)
        min_actives = int(request.form['noOfActives'])
        profile_name = str(request.form['profile_filename'])

        bioprofile_json_filename = os.path.join(g.user.get_user_folder('profiles'), '{}.json'.format(profile_name))
        if os.path.exists(bioprofile_json_filename):
            bioprofile = bp.Bioprofile.from_json(bioprofile_json_filename)
        else:
            bioprofile_json = ds.get_bioprofile(min_actives=min_actives)

            bioprofile = bp.Bioprofile(profile_name,
                                       bioprofile_json['cids'],
                                       bioprofile_json['aids'],
                                       bioprofile_json['outcomes'])

            bioprofile.to_json(g.user.get_user_folder('profiles'))

        act = ds.get_activities()

        profile_matrix = bioprofile.to_frame()
        stats_df = getIVIC(act, profile_matrix)

        # stats_df.to_csv(profile_filename.replace('_BioProfile', '_assay_stats').replace('profiles', 'biosims'), sep='\t')
        # writer = getExcel(profile_filename.replace('profiles', 'biosims').replace('.txt', '.xlsx'))
        # profile.to_excel(writer, 'Bioprofile')
        # stats_df.to_excel(writer, 'In vitro-in vivo correlations')
        # writer.save()
        # session['cur_prof_dir'] = profile_filename.replace('profiles', 'biosims')
        # session['cur_assay_dir'] = session['cur_prof_dir'].replace('_BioProfile', '_assay_stats')
        flash('Success! A profile was created consisting '
              'of {0} compounds and {1} bioassays'.format(profile_matrix.shape[0], profile_matrix.shape[1]), 'info')
        return render_template('CIIProfiler.html', stats=~stats_df.empty, datasets=g.user.get_user_datasets(set_type='training'))


    
@app.route('/CIIPPredict', methods=['POST'])
@login_required
def CIIPPredict():
    """ Creates a biosimilarity and biological nearest neighbors from a user selected profile. 
        If an activity file is uploaded, will calculate and display in vitro, in vivo correlations as well as the 
        results of leave one out predictions of the test set.  
        
        Form Requests: 
            profile_filename: The name of the profile to use for biosimilarity and biological NNs.  From radio buttons.
            cutoff: Biosimilarity cutoff to use for NN calculation.  From text field.
            confidence: Minimum confidence score to use for NN calculation.  From text field.
            submit: Type of submit button, either Delete or Submit
    """

    if request.method == 'POST':
        if request.form['Submit'] == 'Delete':
            USER_FOLDER = CIIProConfig.UPLOAD_FOLDER + '/' + g.user.username
            USER_PROFILES_FOLDER = USER_FOLDER +'/profiles'
            profile_filename = request.form['profile_filename']
            os.remove(USER_PROFILES_FOLDER + '/' + profile_filename)
            return redirect(url_for('CIIPPredictor'))    
        elif request.form['Submit'] == 'Submit':
            USER_FOLDER = CIIProConfig.UPLOAD_FOLDER + '/' + g.user.username
            USER_PROFILES_FOLDER = USER_FOLDER +'/profiles'
            USER_COMPOUNDS_FOLDER = USER_FOLDER +'/compounds'
            USER_BIOSIMS_FOLDER =  USER_FOLDER +'/biosims'
            USER_TEST_SET_FOLDER = USER_FOLDER +'/test_sets'
            USER_NN_FOLDER = USER_FOLDER + '/NNs'

            profile_filename = request.form['profile_filename']
            profile_filename = str(profile_filename)
            profile_directory = USER_PROFILES_FOLDER + '/' + profile_filename

            compound_filename = request.form['compound_filename']
            compound_filename = str(compound_filename)
            compound_directory = USER_TEST_SET_FOLDER + '/' + compound_filename

            cutoff = request.form['cutoff']
            cutoff = str(cutoff)
            cutoff = cutoff.strip().split()
            if not cutoff:
                cutoff = [0.5]
        
            confidence = request.form['conf']
            confidence = str(confidence)
            confidence = confidence.strip().split()
            if not confidence:
                confidence = [4]
            
            confidence[0] = float(confidence[0])*0
        
            nns = request.form['nns']

            training_filename = profile_filename.split('_BioProfile')[0] + '.txt'

            bioprofile = bioprofile_to_pandas(profile_directory)
            test = pickle_to_pandas(compound_directory[:-11])
            # if os.path.isfile(USER_BIOSIMS_FOLDER + '/' +
            #                           profile_filename.replace('_BioProfile', '_BioSim_{0}_{1}_{2}'.format(cutoff[0],
            #                                                                                                confidence[0], nns))):
            #     biosims = pd.read_csv(profile_filename.replace('_BioProfile', '_BioSim_{0}_{1}_{2}'.format(cutoff[0], confidence[0], nns)), sep='\t', index_col=0)

            biosims, conf = get_BioSim(bioprofile, test)
            biosims.to_csv(USER_BIOSIMS_FOLDER + '/' +  profile_filename.replace('_BioProfile', '_BioSim_{0}_{1}_{2}'.format(cutoff[0], confidence[0], nns)), sep='\t')
            conf.to_csv(USER_BIOSIMS_FOLDER + '/' +  profile_filename.replace('_BioProfile', '_Conf_{0}_{1}_{2}'.format(cutoff[0], confidence[0], nns)), sep='\t')
            # writer = getExcel(USER_BIOSIMS_FOLDER + '/' +  profile_filename.replace('_BioProfile.txt', '_BioSim_Conf.xlsx'))
            # biosims.to_excel(writer, 'Biosimilarity')
            # conf.to_excel(writer, 'Confidence Scores')
            # writer.save()
            # get smiles
            smi_test = smi_series(compound_directory[:-11])
            smi_train = smi_series(USER_COMPOUNDS_FOLDER + '/' + training_filename[:-11])

            # remove compounds no in bioprofile
            s_train = smi_train.loc[smi_train.index.intersection(bioprofile.index)]
        
            train_fp = getFPs(s_train)
            test_fp = getFPs(smi_test)
            tan = getChemSimilarity(train_fp, test_fp)
            NNs = createNN(biosims, conf, bio_sim=float(cutoff[0]), conf_cutoff=float(confidence[0]))
            print(NNs)
            for nn in NNs:
                if not NNs[nn].empty:
                    s = get_chemNN(nn, tan, nns=len(NNs[nn].BioNN))
                    NNs[nn] = add_ChemNN(NNs[nn], s)
        
            cids = []
            preds = []
            acts = []
            NN_bool = []
            testsets = [testset for testset in os.listdir(USER_TEST_SET_FOLDER)]
            train_act = act_series(USER_COMPOUNDS_FOLDER + '/' + training_filename[:-11])
            for nn in NNs:
                if not NNs[nn].empty:
                    NN_bool.append(True)
                    NNs[nn] = add_BioNN_act(NNs[nn], train_act)
                    NNs[nn] = add_ChemNN_act(NNs[nn], train_act)
                    pred = make_BioNN_pred(NNs[nn], int(nns))
                    cids.append(str(nn))
                    if pred < 0.5:
                        preds.append(str(0))
                    elif pred > 0.5:
                        preds.append(str(1))
                    else:
                        preds.append(str(0.5))
                    if 'Activity' in test.columns:
                        acts.append(str(test.loc[nn, 'Activity']))
                    else:
                        acts.append('N/A')
                else:
                    cids.append(str(nn))
                    NN_bool.append(False)
                    preds.append('N/A')
                    if 'Activity' in test.columns:
                        acts.append(str(test.loc[nn, 'Activity']))
                    else:
                        acts.append('N/A')
            len_cids = len(cids)
            profiles = [profile for profile in os.listdir(USER_PROFILES_FOLDER)]
            for nn in NNs:
                if not NNs[nn].empty:
                    NNs[nn].to_csv(USER_NN_FOLDER + '/' + compound_filename.replace('_CIIPro.txt', '') + '/' + str(nn) + '.csv')
            #session['sim_data'] = NNs
            #session['cids'] = cids
            #session['preds'] = preds
            session['nns'] = int(nns)
            session['test_set'] = compound_filename.replace('_CIIPro.txt', '')
            session['cur_biosim_dir'] = USER_BIOSIMS_FOLDER + '/' +  profile_filename.replace('_BioProfile.txt', '')
            session['max_conf'] = len(bioprofile.columns)            
            return render_template('CIIPPredictor.html', cids=cids,
                               preds=preds, acts=acts, len_cids=len_cids, profiles=profiles, testsets=g.user.get_user_datasets(set_type='test'), 
                               NN_bool=NN_bool)  



@app.route('/similarity<cid>', methods=['GET', 'POST'])
@login_required
def similarity(cid):
    USER_FOLDER = CIIProConfig.UPLOAD_FOLDER + '/' + g.user.username
    USER_TEST_SET_FOLDER = USER_FOLDER +'/test_sets'
    USER_NN_FOLDER = USER_FOLDER + '/NNs'
    
    df = nn_to_pandas(USER_NN_FOLDER + '/' + session['test_set'] + '/' + str(cid) + '.csv')
    #sim_graph = createSimilarityGraph(int(cid), df,  int(session['nns']))
    sim_graph_pic = sim_graph(int(cid), df, int(session['nns']), int(session['max_conf']))
    #cids = session['cids']
    #preds = session['preds']
    #acts = session['acts']
    #len_cids = len(cids)
       
    return render_template('similarity.html', sim_graph=sim_graph_pic)


@app.route('/CIIProTools', methods=['GET', 'POST']) 
@login_required
def CIIProTools():
    """ Displays CIIProTools page with all available training sets
        in users' training folder.
    
    """

    USER_COMPOUND_FOLDER = CIIProConfig.UPLOAD_FOLDER + '/' + g.user.username + '/compounds'
    datasets = [dataset for dataset in os.listdir(USER_COMPOUND_FOLDER)]
    return render_template('CIIProTools.html', datasets=g.user.get_user_datasets(set_type='training'), 
                           username=g.user.username)	

@app.route('/activitycliffs', methods=['GET', 'POST']) 
@login_required
def activitycliffs():
    """ Method Identifies Activity Cliffs in training set
    
    """

    USER_COMPOUND_FOLDER = CIIProConfig.UPLOAD_FOLDER + '/' + g.user.username + '/compounds'
    datasets = [dataset for dataset in os.listdir(USER_COMPOUND_FOLDER)]
    compound_filename = request.form['compound_filename']
    compound_filename = str(compound_filename)
    compound_directory = USER_COMPOUND_FOLDER + '/' + compound_filename
    
    df = activity_cliffs(compound_directory)
    #df.to_csv(compound_directory.replace('compounds', NNs), sep='\t')
    #cliff = cliffTable_bokeh(df)
    df.index.name = 'Target_CID'
        
    writer = pd.ExcelWriter(compound_directory.replace('compounds', 'NNs').replace('.txt', '.xlsx'))
    df.to_excel(writer, sheet_name='Activity Cliffs')
    writer.save()
    session['cur_ciff_dir'] = compound_directory.replace('compounds', 'NNs').replace('.txt', '.xlsx')
        
    return render_template('CIIProTools.html', datasets=g.user.get_user_datasets(set_type='training'), 
                           username=g.user.username, ac=df.to_html())	

                               
def zipBiosimFiles(USER_BIOSIMS_FOLDER, filename):
    """ Zips biosimilarity, confidence, and biological nearest neighbor files.
    """
    os.chdir(USER_BIOSIMS_FOLDER)
    z = zipfile.ZipFile(filename + '_BioSimilarity.zip', 'w')
    z.write(filename + '_BioSim.txt')
    z.write(filename + '_Bioneighbor.txt')
    z.write(filename + '_BioSim_Conf.txt')
    z.close()


def zipPredictionsFiles(biosims_dir):
    """ Zips biosimilarity, confidence, biological nearest neighbor, and bioprediction files.
    """
    dir_L = biosims_dir.split('/')
    dir_ = '/'.join(dir_L[:-1])
    os.chdir(dir_)
    z = zipfile.ZipFile(dir_L[-1] + '_biosims.zip', 'w')
    z.write(dir_L[-1] + '_BioSim.txt')
    #z.write(filename + '_BioPred.txt')
    #z.write(filename + '_Bioneighbor.txt')
    z.write(dir_L[-1] + '_Conf.txt')
    z.write(dir_L[-1] + '_BioSim_Conf.xlsx')
    z.close()
    
def zipbioprofile(prof_dir):
    """ Zips bioprofile and in vitro, in vivo correlation files.
    """
    dir_L = prof_dir.split('/')
    dir_ = '/'.join(dir_L[:-1])
    os.chdir(dir_)
    z = zipfile.ZipFile(dir_L[-1].replace('.txt', '.zip'), 'w')
    z.write(dir_L[-1])
    z.write(dir_L[-1].replace('_BioProfile','_assay_stats'))
    z.write(dir_L[-1].replace('.txt', '.xlsx'))
    z.close()
    
@app.route('/sendbiosims')
@login_required
def sendbiosims():
    zipPredictionsFiles(session['cur_biosim_dir'])
    return send_file(session['cur_biosim_dir'] + '_biosims.zip', as_attachment=True)
 
@app.route('/sendbioprofile')
@login_required
def sendbioprofile():
    zipbioprofile(session['cur_prof_dir'])
    return send_file(session['cur_prof_dir'].replace('.txt', '.zip'), as_attachment=True)

@app.route('/sendactcliff')
@login_required
def sendactcliff():
    return send_file(session['cur_ciff_dir'], as_attachment=True)

@app.route('/sendtutorial')
def trainingsettutorial():
    return send_file('resources/ER_tutorial.zip')
  
 
@app.route('/contact')
def contact():
      return render_template('contact.html')



@app.errorhandler(500)
def internalServiceError(e):
    return render_template('500.html'), 500


# this is where the RESTFul API will be


@app.route('/test')
def test():
    test = g.user.get_user_datasets()
    import json

    return json.dumps(test)


if __name__ == '__main__': #says if this scripts is run directly, start the application
	app.run()
