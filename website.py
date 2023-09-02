from flask import Flask, render_template, request, redirect, jsonify, send_file, session
import pandas as pd
from pymongo import MongoClient
import shutil
import datetime
import hashlib
import os
import predict_after
import redis
# construct Email text
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
import smtplib
import json
import requests as re
import torch

# public variable, trait name
traitsList = ['ALL',
 'MG',
 'ST',
 'FC',
 'P_CLR',
 'P_FRM',
 'P_DENS',
 'POD',
 'SC_L',
 'SC_CLR',
 'H_CLR',
 'protein',
 'oil',
 'Linoleic',
 'Linolenic',
 'Stem term',
 'R1',
 'R8',
 'Hgt',
 'Mot',
 'Ldg',
 'SQ',
 'SdWgt',
 'Yield',
 'Oleic',
 'Palmitic',
 'PRR1',
 'SCN3',
 'Stearic']

# Start the app instance
def index():
    return render_template('index.html')
app = Flask(__name__)
app.add_url_rule('/SoyDNGP', 'index', view_func=index)
app.secret_key = 'isadiashdiow12324'
# Create a redis instance for progress bar update
host = "127.0.0.1"
port = "6379"
redis_pool = redis.ConnectionPool(host=host, port=port, decode_responses=True)


# Redirect homepage to /SoyDNGP
@app.route('/')
def redirect_to_index():
    ip = request.headers['X-Forwarded-For']
    key = 'GORBZ-Y27C5-R3GIZ-I6SFZ-BR7U6-3JB6A'
    sk = '87HIx3HWaB3mflZfWiXjIaVuiVsuI0r8'
    api = f"/ws/location/v1/ip/?ip={ip}&key={key}"
    md5 = hashlib.md5(f"{api+sk}".encode('utf-8')).hexdigest()
    api_new = "https://apis.map.qq.com" + api + f"&sig={md5}"
    result = eval(re.get(api_new).content.decode())
    if not int(result['status']):
        pos = eval(re.get(api_new).content.decode())['result']['location']
        # Link to local MongoDB database
        client = MongoClient("mongodb:///")
        # Select the test database
        db = client.location
        # Select location collection under location
        collection = db.location
        # add location
        collection.insert_one(pos)
    return redirect('/SoyDNGP')

# Contact page
@app.route('/contact')
def contact():
    return render_template('contact.html')
@app.route('/SoyTSS')

# Learn More page
@app.route('/LearnMore')
def LearnMore():
    # Link to local MongoDB database
    client = MongoClient("mongodb:///")
    # Select the test database
    db = client.location
    # Select location collection under location
    collection = db.location
    # query all results
    rets = collection.find()
    # set geometries list
    geo = []
    id = 0
    for ret in rets:
        id += 1
        posdict = {"id": id, "lat":f"{ret['lat']}", "lng":f"{ret['lng']}"}
        geo.append(posdict)
    print(geo)
    return render_template('learnmore.html', markers=geo)
# Search page
@app.route('/Search')
def Search():
    return render_template('lookup.html')

# Upload page
@app.route('/UploadData')
def UploadData():
    return render_template('predict.html', df=pd.DataFrame())

# Download the test examples
@app.route('/DownloadExample')
def DownloadExample():
    return send_file('/home/wxt/Projects/SoybeanWebsite2/10_test_examples.vcf')

# error page
@app.errorhandler(400)
def page_not_found(error):
    return render_template('errors.html')

@app.errorhandler(404)
def page_not_found(error):
    return render_template('errors.html')

@app.errorhandler(500)
def internal_server_error(error):
    return render_template('errors.html')

@app.errorhandler(504)
def internal_server_error(error):
    return render_template('errors.html')

@app.route('/submit', methods=['POST'])
def submit():
    # correspond to action /submit
    if request.method == 'POST':
        # Get the ID from the form and split it into a list
        ID = request.form['ID'].split(';')
        # Deduplication and arrangement of ID list
        new_ID = list(set(ID))
        new_ID.sort(key=ID.index)
        # Get the traits selected by the user from the form
        traits = request.form.getlist('options')
        # Create an empty list for storing query results
        results = []
        # When neither the id nor the selected trait is empty
        if len(new_ID) and len(traits) != 0:
            # traversal ID
            for id in new_ID:
                # If selected as "all"
                if traits[0] == 'all':
                    # Equivalent to selecting all traits
                    traits = traits[1:]
                # Get all selected trait names according to traitsList
                traitsNames = [traitsList[int(i)] for i in traits]
                # Link to local MongoDB database
                client = MongoClient("mongodb://")
                # Select the test database
                db = client.test
                # Select the test collection under test
                collection = db.test
                # Query by acid
                print(id)
                rets = collection.find({"$or": [{'acid': id}, {"CommonName": id}]})
                # Create a dictionary of {ID, trait 1, trait 2...} for easy dataframe creation
                result = {"ID or Common Name": f"<span class='text-dark'><b>{id}</b></span>"}
                # Traverse query results
                for i in rets:
                    # Iterate over selected trait names
                    for j in traitsNames:
                        # i is a dict object, use the get method to query the corresponding trait content, if not, it will default to No result
                        value = i.get(j, 'No result')
                        # add to dictionary
                        result[j] = value
                        # add the result to the list
                results.append(result)
                # The result can be displayed because it is not empty
                showresult = True
        # One is empty, no results are displayed, and the query result is empty
        else:
            results = None
            showresult = False
        resultDF = pd.DataFrame(results)
        return render_template('/lookup.html', showresult=showresult, results=resultDF, col_names=resultDF.columns, ID=ID)

@app.route('/upload', methods=['POST'])
def upload():
    # Take a thread, each upload is equivalent to creating a new task
    r = redis.Redis(connection_pool=redis_pool)
    # Initialize taskID
    taskID = hashlib.md5(os.urandom(20)).hexdigest()
    session['taskID'] = taskID
    task_session_ = {"taskID": taskID, "md5": "", "join": "", "traits": "", "filePath": "", "fileName": "",
                    "predict_finish": False}
    # Get user uploaded files from files
    file = request.files.get('file')
    # It is taken out from the cache and saved in byte
    content = file.read()
    # if content is not empty
    if content:
        # Calculate MD5
        file_md5 = hashlib.md5(content).hexdigest()
        # Use md5 as a session variable
        task_session_['md5'] = file_md5
        # Record the time and convert it to a list with a total of 7 elements
        date = str(datetime.datetime.now()).split(' ')
        # Combine the new file name with date + md5, e.g."2023-06-06-16.41.05.379780-a8d2a9a59092c18c35f688be915a5bb6"
        newfilename = date[0] + '-' + date[1].replace(':', '.') + '-' + file_md5
        # If the path does not exist
        if not os.path.exists(f"./{newfilename}"):
            # create folder
            os.mkdir(f"./{newfilename}")
            # Compose the path
        savepath = f"./{newfilename}/" + file.filename
        # The global variable is assigned the file name
        task_session_['fileName'] = file.filename
        # Assembly storage directory
        task_session_['filePath'] = f"./{newfilename}/"
        # Upload session, update filePath, fileName and md5
        r.set("task_session", json.dumps({taskID: task_session_}))
        # link database
        client = MongoClient("mongodb://xtlab:S2o0y2D3N0G6P@localhost:27017/")
        # open files
        db = client.files
        # query MongoDB
        result = db.files.find_one({'md5': file_md5})
        # If there is no record, it means uploading for the first time
        if not result:
            # write file to local
            with open(savepath, 'wb') as f:
                f.write(content)
            # Insert md5 and corresponding storage directory records
            db.files.insert_one({'path':savepath, 'md5': file_md5})
        else:
            # Copy the file from the directory if there is already a record
            shutil.copyfile(result['path'], savepath)
        return jsonify({'errno':0, 'errmsg':'success'})
    else:
        return jsonify({'errno':1, 'errmsg':'file is empty'})

@app.route('/getArgs', methods=['POST'])
def getArgs():
    if request.method == "POST":
        # Obtain whether the user agrees to join the database
        data = request.json
        join = data.get("join")
        # Get trait id from form
        traits = data.get('options')
        # update to session
        r = redis.Redis(connection_pool=redis_pool)
        task_session_ = json.loads(r.get("task_session"))[session['taskID']]
        task_session_['join'] = join
        task_session_['traits'] = traits
        r.set("task_session", json.dumps({session['taskID']: task_session_}))
    return 'success'

@app.route('/Predict', methods=['GET', 'POST'])
def JoinOrNot():
    torch.cuda.empty_cache()
    if request.method == 'POST':
        # Get the date and md5 and assemble it into taskID to identify different requests
        date = str(datetime.datetime.now()).split(' ')
        # Get a redis thread from the thread pool
        r = redis.Redis(connection_pool=redis_pool)
        # Retrieve session
        task_session_ = json.loads(r.get("task_session"))[session['taskID']]
        # If the trait is not null
        worker = None
        if len(task_session_['traits']) != 0:
            # Determine whether to click Select All and change traitsNames
            if task_session_['traits'][-1] != 'all':
                print(task_session_['filePath'] + task_session_['fileName'])
                traitsNames = [traitsList[int(i)] for i in task_session_['traits']]
                # start forecasting
                worker = predict_after.predict(task_session_['filePath'] + task_session_['fileName'], traitsNames,
                                               task_session_['filePath'], r, taskID=session['taskID'],
                                               if_all=False)
            else:
                traits = task_session_['traits'][:-1]
                traitsNames = [traitsList[int(i)] for i in traits]
                worker = predict_after.predict(task_session_['filePath'] + task_session_['fileName'], traitsNames,
                                               task_session_['filePath'], r, taskID=session['taskID'],
                                               if_all=False)
        torch.cuda.empty_cache()
        # Set the predict_finish state to True and update to the global variable
        progressdict = json.loads(r.get('progressdict'))[session['taskID']]
        task_session_['predict_finish'] = True
        r.set("task_session", json.dumps({session['taskID']: task_session_}))
        progressdict['predict_finish'] = True
        r.set('progressdict', json.dumps({session['taskID']: progressdict}))
        # fetch taskdict
        taskdict = json.loads(r.get('taskdict'))[session['taskID']]
        # Because df cannot be directly jsonized, it needs to be converted into JSON before passing it into taskdict, and it must be parsed before use
        resultJSON = taskdict['result']
        resultDF = pd.read_json(resultJSON, encoding="utf-8", orient='records')
        # resultDF = pd.read_csv(r"C:\Users\PinkFloyd\OneDrive\桌面\predict.csv")
        # If the user agrees to join
        if task_session_['join'] == 'yes':
            client = MongoClient("mongodb://xtlab:S2o0y2D3N0G6P@localhost:27017/")
            db = client.test
            collection = db.test
            resultList = []
            for i in range(len(resultDF)):
                # read each row of data
                row = resultDF.iloc[i, :]
                # read ID
                seedID = row['acid']
                # Get Common Name
                rets = collection.find({'acid': seedID})
                CommonName = ""
                for ret in rets:
                    CommonName = ret.get('CommonName', "")
                # create dictionary
                if len(CommonName):
                    seedDict = {"acid": seedID, "CommonName": CommonName}
                else:
                    seedDict = {"acid": seedID}
                # Add trait content (col_names[0] is id)
                for name in taskdict['col_names'][1:]:
                    trait = name
                    # To judge whether it is a missing value, make a special mark
                    if worker.IsMissing:
                        value = f"**{row[trait]}**(predict, uploaded at {date[0] + '-' + date[1].replace(':', '.')})"
                    else:
                        value = f"{row[trait]}(predict, uploaded at {date[0] + '-' + date[1].replace(':', '.')})"
                    # assembled dictionary
                    seedDict[trait] = value
                # add sample
                resultList.append(seedDict)
            collection.insert_many(resultList)
        elif task_session_['join'] == 'no':
            pass
        temp = resultDF['acid']
        resultDF['acid'] = temp.map(lambda x: f"<span class='text-dark'><b>{x}</b></span>")
        # Set the number of results that can be displayed per page
        rows_per_page = 3
        # Calculate the total number of pages
        taskdict['total_pages'] = len(resultDF) // rows_per_page + 1
        # Set the current page number
        taskdict['page'] = 1
        # Calculate the number of starting rows
        start_row = (taskdict['page'] - 1) * rows_per_page
        # Set the number of ending rows (what row is the last row displayed on the current page in resultDF)
        end_row = start_row + rows_per_page
        # Slicing resultDF with row numbers
        df_slice = resultDF.iloc[start_row:end_row]
        # Get the column names of the form
        taskdict['col_names'] = resultDF.columns.tolist()
        # upload to redis
        r.set('taskdict', json.dumps({session['taskID']: taskdict}))
        return render_template('result.html', df=df_slice, total_pages=taskdict['total_pages'],
                               page=taskdict['page'],
                               predict_finish=task_session_['predict_finish'],
                               col_names=taskdict['col_names'])

@app.route("/progress")
def update_progress():
    # Fetch a thread
    r = redis.Redis(connection_pool=redis_pool)
    # Retrieve progressdict
    progressdict = json.loads(r.get('progressdict'))[session['taskID']]
    return progressdict


@app.route('/pagenext')
def pagenext():
    # Fetch a thread
    r = redis.Redis(connection_pool=redis_pool)
    # retrieve taskdict
    taskdict = json.loads(r.get('taskdict'))[session['taskID']]
    task_session_ = json.loads(r.get('task_session'))[session['taskID']]
    taskdict['page'] += 1
    # update page
    r.set('taskdict', json.dumps({session['taskID']: taskdict}))
    rows_per_page = 3
    resultJSON = taskdict['result']
    resultDF = pd.read_json(resultJSON, encoding="utf-8", orient='records')
    temp = resultDF['acid']
    resultDF['acid'] = temp.map(lambda x: f"<span class='text-dark'><b>{x}</b></span>")
    start_row = (taskdict['page'] - 1) * rows_per_page
    end_row = start_row + rows_per_page
    df_slice = resultDF.iloc[start_row:end_row]
    return render_template('result.html', df=df_slice, total_pages=taskdict['total_pages'],
                           page=taskdict['page'],
                           predict_finish=task_session_['predict_finish'], col_names=taskdict['col_names'])

@app.route('/pageprev')
def pageprev():
    # Fetch a thread
    r = redis.Redis(connection_pool=redis_pool)
    # retrieve taskdict
    taskdict = json.loads(r.get('taskdict'))[session['taskID']]
    task_session_ = json.loads(r.get('task_session'))[session['taskID']]
    taskdict['page'] -= 1
    # update page
    r.set('taskdict', json.dumps({session['taskID']: taskdict}))
    rows_per_page = 3
    resultJSON = taskdict['result']
    resultDF = pd.read_json(resultJSON, encoding="utf-8", orient='records')
    temp = resultDF['acid']
    resultDF['acid'] = temp.map(lambda x: f"<span class='text-dark'><b>{x}</b></span>")
    start_row = (taskdict['page'] - 1) * rows_per_page
    end_row = start_row + rows_per_page
    df_slice = resultDF.iloc[start_row:end_row, :]
    return render_template('result.html', df=df_slice, total_pages=taskdict['total_pages'],
                           page=taskdict['page'],
                           predict_finish=task_session_['predict_finish'], col_names=taskdict['col_names'])


@app.route('/download')
def download_file():
    # Fetch a thread
    r = redis.Redis(connection_pool=redis_pool)
    # retrieve taskdict
    task_session_ = json.loads(r.get('task_session'))[session['taskID']]
    return send_file(f'{task_session_["filePath"]}/predict.csv')
    # return send_file(rf"D:\Projects\website\soybean\2023-05-30-3.3751.402995-a8d2a9a59092c18c35f688be915a5bb6\predict.csv")


@app.errorhandler(400)
def page_not_found(error):
    return render_template('errors.html')

@app.errorhandler(404)
def page_not_found(error):
    return render_template('errors.html')

@app.errorhandler(500)
def internal_server_error(error):
    return render_template('errors.html')

@app.route('/send', methods=['POST'])
def send():
    if request.method == 'POST':
        userName = request.form.getlist('Name')
        userEmail = request.form.getlist('Email')
        userContent = request.form.getlist('field-2')
        print(userName, userEmail, userContent)
        mail_sender = '1135431747@qq.com'
        mail_host = 'smtp.qq.com'
        mail_license = ''
        mail_receivers = ['1135431747@qq.com', 'wangxt881@gmail.com']  
        mail = MIMEMultipart('related')
        mail['From'] = f"Website User<{mail_sender}>"  # sender
        mail['To'] = "zhn<1135431747@qq.com>, wxt<wangxt881@gmail.com>"  # receiver
        mail['Subject'] = Header('网页问题反馈', 'utf-8')  # 主题
        # Three parameters: the first is the text content, the second plain sets the text format, and the third utf-8 sets the encoding
        message = MIMEText(f'用户：{userName[0]}\n反馈：{userContent[0]}\n请回复至：{userEmail[0]}', 'plain', 'utf-8')
        mail.attach(message)
        stp = smtplib.SMTP()
        stp.connect(mail_host, 587)
        stp.login(mail_sender, mail_license)
        # Send email, pass parameter 1: sender email address, parameter 2: recipient email address, parameter 3: change the format of email content to str
        stp.sendmail(mail_sender, mail_receivers, mail.as_string())
        stp.quit()
    return render_template('thanksforcontact.html')



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, threaded=False)
