#!/usr/bin/env python
# coding: utf-8

from flask import Flask, render_template, request, jsonify, send_file, redirect
from pymongo import MongoClient
import hashlib
import globalvar
import predict_after
import os
import datetime
import shutil
import pandas as pd
import smtplib
import email
# 负责构造文本
from email.mime.text import MIMEText
# 负责将多个对象集合起来
from email.mime.multipart import MIMEMultipart
from email.header import Header


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
 'eno',
 'R1',
 'R8',
 'Hgt',
 'Mat',
 'Ldg',
 'SQ',
 'SdWgt',
 'Yield']
filePath = ""
fileName = ""
page = 0
resultDF = pd.DataFrame()

def index():
    return render_template('test.html')

app = Flask(__name__)
app.add_url_rule('/SoyDNGP', 'index', view_func=index)

@app.route('/')
def redirect_to_index():
    return redirect('/SoyDNGP')

@app.route('/SoyDNGP')
def redirect_to():
    return render_template('test.html')

@app.route('/contact')
def concat():
    return render_template('contact.html')

@app.route('/Document')
def document():
    return render_template('Document.html')

@app.route('/AboutUs')
def AboutUs():
    return render_template('AboutUs.html')

@app.route('/Search')
def Search():
    return render_template('Search.html')

@app.route('/UploadData')
def Predict():
    globalvar.initProgressBar()
    return render_template('UploadData.html', df=pd.DataFrame(), total_pages=0, page=0, predict_finish=False)

@app.route('/submit', methods=['POST'])
def submit():
    if request.method == 'POST':
        ID = request.form['ID'].split(';')
        new_ID = list(set(ID))
        new_ID.sort(key=ID.index)
        print(new_ID)
        traits = request.form.getlist('options')
        results = []
        if len(new_ID) and len(traits) != 0:
            for id in new_ID:
                if traits[0] == 'all':
                    traits = traits[1:]
                traitsNames = [traitsList[int(i)] for i in traits]
                client = MongoClient("mongodb://localhost:27017/")
                db = client.test
                collection = db.test
                rets = collection.find({'acid': id})
                results.append({'trait': id, 'value': ""})
                for i in rets:
                    for j in traitsNames:
                        value = i.get(j, 'No result')
                        result = {"trait": j, "value":value}
                        results.append(result)
                showresult = True
        else:
            results = None
            showresult = False
        print(results)
        return render_template('/Search.html', showresult=showresult, results=results, ID=ID)

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files.get('file')
    content = file.read()  # 从缓存中被拿出，用byte保存
    if content:
        file_md5 = hashlib.md5(content).hexdigest() # 计算 MD5
        date = str(datetime.datetime.now()).split(' ')
        newfilename = date[0] + '-' + date[1].replace(':', '.') + '-' + file_md5
        if not os.path.exists(f"./{newfilename}"):
            os.mkdir(f"./{newfilename}")  # 创建文件夹
        savepath = f"./{newfilename}/" + file.filename  # 组合出路径
        global fileName
        fileName = file.filename
        global filePath 
        filePath = f"./{newfilename}/"
        client = MongoClient("mongodb://localhost:27017/")
        db = client.files
        result = db.files.find_one({'md5': file_md5}) # 查询 MongoDB
        if not result:
            with open(savepath, 'wb') as f:
                f.write(content)
            db.files.insert_one({'path':savepath, 'md5': file_md5})
        else:
            print(result['path'])
            shutil.copyfile(result['path'], savepath)
        return jsonify({'errno':0, 'errmsg':'success'})
    else:
        return jsonify({'errno':1, 'errmsg':'file is empty'})

@app.route('/progress')
def update_progress():
    progress = globalvar.getProgressBar()  # 获取当前进度
    title = globalvar.getTitle()  # 获取进度条标题
    return {
        'title': title,
        'progress': progress
    }  # 返回进度信息
    
@app.route('/Predict', methods=['GET', 'POST'])
def predict_():
    if request.method == 'POST':
        globalvar.initProgressBar()
        traits = request.form.getlist('options')
        worker = None
        if len(traits) != 0:
            if traits[0] != 'all':
                traitsNames = [traitsList[int(i)] for i in traits]
                print(traitsNames)
                worker = predict_after.predict(filePath + fileName, traitsNames, filePath, if_all=False)

            else:
                traits = traits[1:]
                traitsNames = [traitsList[int(i)] for i in traits]
                worker = predict_after.predict(filePath + fileName, [], filePath, if_all=False)
        global resultDF
        # resultDF = pd.read_csv(r"C:\Users\PinkFloyd\OneDrive\桌面\predict.csv")
        if worker.is_finished:
            resultDF = worker.Result
        else:
            print("not finished yet")
        rows_per_page = 3
        total_pages = len(resultDF) // rows_per_page + 1
        global page
        page = 1
        start_row = (page - 1) * rows_per_page
        end_row = start_row + rows_per_page
        df_slice = resultDF.iloc[start_row:end_row]
        col_names = resultDF.columns.tolist()
        return render_template('UploadData.html', df=df_slice, total_pages=total_pages, page=page, predict_finish=True, col_names = col_names)
    return render_template('UploadData.html', df=pd.DataFrame(), total_pages=0, page=0, predict_finish=False)



@app.route('/pagenext')
def pagenext():
    global page
    page += 1
    rows_per_page = 3
    total_pages = len(resultDF) // rows_per_page + 1
    start_row = (page - 1) * rows_per_page
    end_row = start_row + rows_per_page
    df_slice = resultDF.iloc[start_row:end_row]
    col_names = resultDF.columns.tolist()
    return render_template('UploadData.html', df=df_slice, total_pages=total_pages, page=page, predict_finish=False, col_names = col_names)

@app.route('/pageprev')
def pageprev():
    global page
    page -= 1
    rows_per_page = 3
    total_pages = len(resultDF) // rows_per_page + 1
    start_row = (page - 1) * rows_per_page
    end_row = start_row + rows_per_page
    df_slice = resultDF.iloc[start_row:end_row, :]
    col_names = resultDF.columns.tolist()
    return render_template('UploadData.html', df=df_slice, total_pages=total_pages, page=page, predict_finish=False, col_names = col_names)


@app.route('/download')
def download_file():
    return send_file(f'{filePath}/predict.csv')
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
        mail_license = 'dgyqkhmkgirjigij'
        mail_receivers = ['1135431747@qq.com', 'wangxt881@gmail.com']  # 接收邮件，可设置为你的QQ邮箱或者其他邮箱
        mail = MIMEMultipart('related')
        mail['From'] = f"Website User<{mail_sender}>"  # 发送者
        mail['To'] = "zhn<1135431747@qq.com>, wxt<wangxt881@gmail.com>"  # 接收者
        mail['Subject'] = Header('网页问题反馈', 'utf-8')  # 主题
        # 三个参数：第一个为文本内容，第二个 plain 设置文本格式，第三个 utf-8 设置编码
        message = MIMEText(f'用户：{userName[0]}\n反馈：{userContent[0]}\n请回复至：{userEmail[0]}', 'plain', 'utf-8')
        mail.attach(message)
        stp = smtplib.SMTP()
        stp.connect(mail_host, 587)
        stp.login(mail_sender, mail_license)
        # 发送邮件，传递参数1：发件人邮箱地址，参数2：收件人邮箱地址，参数3：把邮件内容格式改为str
        # stp.sendmail(mail_sender, mail_receivers, mail.as_string())
        stp.quit()
    return render_template('thanks.html')

if __name__ == '__main__':
    app.run(host="0.0.0.0")  # 实时更改





