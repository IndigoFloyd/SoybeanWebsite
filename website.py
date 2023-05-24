#!/usr/bin/env python
# coding: utf-8

from flask import Flask, render_template, request, jsonify, send_file
from pymongo import MongoClient
import hashlib
import globalvar
import predict_after
import os
import datetime
import shutil
import pandas as pd



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

app = Flask(__name__)
@app.route('/')
def index():
    return render_template('Index.html')

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

@app.route('/submit', methods=['GET', 'POST'])
def submit():
    if request.method == 'POST':
        ID = request.form['inputText']
        traits = request.form.getlist('options')
        if len(ID) and len(traits) != 0:
            if traits[0] == 'all':
                traits = traits[1:]
            traitsNames = [traitsList[int(i)] for i in traits]
            client = MongoClient()
            db = client.test
            collection = db.test
            rets = collection.find({'acid': ID})
            results = []
            for i in rets:
                for j in traitsNames:
                    value = i.get(j, 'No result')
                    result = {"trait": j, "value":value}
                    results.append(result)
        else:
            results = False
        return render_template('/Search.html', results=results, ID=ID)

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
        client = MongoClient()
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
    
@app.route('/Predict', methods=['POST'])
def predict_():
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
    # resultDF = pd.read_csv(r"D:\Projects\website\soybean\2023-05-22-21.14.32.637542-21656b0cb3b93d93d66473c3bca94cb1\predict.csv")
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
    # return send_file(rf'D:\Projects\website\soybean\2023-05-22-10.40.13.766003-21656b0cb3b93d93d66473c3bca94cb1\predict.csv')


if __name__ == '__main__':
    app.run(host="0.0.0.0")  # 实时更改





