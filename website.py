from flask import Flask, render_template, request, redirect, jsonify, send_file, session
import pandas as pd
from pymongo import MongoClient
import shutil
import datetime
import hashlib
import os
import predict_after
import redis
# 负责构造文本
from email.mime.text import MIMEText
# 负责将多个对象集合起来
from email.mime.multipart import MIMEMultipart
from email.header import Header
import smtplib
import json

# 公用变量，性状名
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

# 启动app实例
def index():
    return render_template('index.html')
app = Flask(__name__)
app.add_url_rule('/SoyDNGP', 'index', view_func=index)
app.secret_key = 'isadiashdiow12324'
# 创建一个redis实例，用于进度条更新
host = "127.0.0.1"
port = "6379"
redis_pool = redis.ConnectionPool(host=host, port=port, decode_responses=True)


# 重定向主页至/SoyDNGP
@app.route('/')
def redirect_to_index():
    return redirect('/SoyDNGP')
# Contact页面
@app.route('/contact')
def contact():
    return render_template('contact.html')
# Learn More页面
@app.route('/LearnMore')
def LearnMore():
    return render_template('learnmore.html')
# 搜索页面
@app.route('/Search')
def Search():
    return render_template('lookup.html')

# 上传页面
@app.route('/UploadData')
def UploadData():
    return render_template('predict.html', df=pd.DataFrame())

# 错误页面
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
    # 对应action /submit
    if request.method == 'POST':
        # 从form获取ID并拆分为列表
        ID = request.form['ID'].split(';')
        # ID列表的去重与排列
        new_ID = list(set(ID))
        new_ID.sort(key=ID.index)
        # 从form获取用户选定的性状
        traits = request.form.getlist('options')
        # 创建空白列表，用于存放查询结果
        results = []
        # 当ID和选定的性状都不为空时
        if len(new_ID) and len(traits) != 0:
            # 遍历ID
            for id in new_ID:
                # 如果选定为“all”
                if traits[0] == 'all':
                    # 相当于选定全部性状
                    traits = traits[1:]
                # 根据traitsList获取全部选定性状名
                traitsNames = [traitsList[int(i)] for i in traits]
                # 链接本地MongoDB数据库
                client = MongoClient("mongodb://localhost:27017/")
                # 选择test数据库
                db = client.test
                # 选择test下的test collection
                collection = db.test
                # 根据acid查询
                rets = collection.find({'acid': id})
                # 将ID行添加进空列表，如果查询多ID，可以由此行区分开是谁的性状
                results.append({'trait': id, 'value': ""})
                # 遍历查询结果
                for i in rets:
                    # 遍历选定的性状名
                    for j in traitsNames:
                        # i是dict对象，使用get方法查询对应性状内容，如果没有就默认No result
                        value = i.get(j, 'No result')
                        # 编辑json键值对
                        result = {"trait": j, "value":value}
                        # 将结果添加进列表中
                        results.append(result)
                # 因为不为空所以可以显示结果
                showresult = True
        # 有一个为空，不显示结果，查询结果为空
        else:
            results = None
            showresult = False
        return render_template('/lookup.html', showresult=showresult, results=results, ID=ID)

@app.route('/upload', methods=['POST'])
def upload():
    # 取一个线程，每次上传就相当于建立一个新的task
    r = redis.Redis(connection_pool=redis_pool)
    # 初始化taskID
    taskID = hashlib.md5(os.urandom(20)).hexdigest()
    session['taskID'] = taskID
    task_session_ = {"taskID": taskID, "md5": "", "join": "", "traits": "", "filePath": "", "fileName": "",
                    "predict_finish": False}
    # 从files获取用户上传的文件
    file = request.files.get('file')
    # 从缓存中被拿出，用byte保存
    content = file.read()
    # 如果内容不为空
    if content:
        # 计算 MD5
        file_md5 = hashlib.md5(content).hexdigest()
        # 将md5作为session的变量
        task_session_['md5'] = file_md5
        # 记录时间，并且转换为列表，一共7个元素
        date = str(datetime.datetime.now()).split(' ')
        # 组合新的文件名，以日期+md5组成，e.g."2023-06-06-16.41.05.379780-a8d2a9a59092c18c35f688be915a5bb6"
        newfilename = date[0] + '-' + date[1].replace(':', '.') + '-' + file_md5
        # 如果不存在该路径
        if not os.path.exists(f"./{newfilename}"):
            # 创建文件夹
            os.mkdir(f"./{newfilename}")
            # 组合出路径
        savepath = f"./{newfilename}/" + file.filename
        # 全局变量赋值为文件名
        task_session_['fileName'] = file.filename
        # 组装存放目录
        task_session_['filePath'] = f"./{newfilename}/"
        # 上传session，更新filePath、fileName和md5
        r.set("task_session", json.dumps({taskID: task_session_}))
        # 链接数据库
        client = MongoClient("mongodb://localhost:27017/")
        # 打开files
        db = client.files
        # 查询 MongoDB
        result = db.files.find_one({'md5': file_md5})
        # 如果没记录，说明第一次上传
        if not result:
            # 写入文件到本地
            with open(savepath, 'wb') as f:
                f.write(content)
            # 插入md5和对应存放目录记录
            db.files.insert_one({'path':savepath, 'md5': file_md5})
        else:
            # 如果已经有记录就从目录将文件复制过来
            shutil.copyfile(result['path'], savepath)
        return jsonify({'errno':0, 'errmsg':'success'})
    else:
        return jsonify({'errno':1, 'errmsg':'file is empty'})

@app.route('/getArgs', methods=['POST'])
def getArgs():
    if request.method == "POST":
        # 获取用户是否同意加入数据库
        data = request.json
        join = data.get("join")
        # 从form获取性状id
        traits = data.get('options')
        # 更新到session
        r = redis.Redis(connection_pool=redis_pool)
        task_session_ = json.loads(r.get("task_session"))[session['taskID']]
        task_session_['join'] = join
        task_session_['traits'] = traits
        r.set("task_session", json.dumps({session['taskID']: task_session_}))
    return 'success'

@app.route('/Predict', methods=['GET', 'POST'])
def JoinOrNot():
    if request.method == 'POST':
        # 获取日期与md5，组装成taskID用以辨别不同请求
        date = str(datetime.datetime.now()).split(' ')
        # 从线程池获取一个redis线程
        r = redis.Redis(connection_pool=redis_pool)
        # 取回session
        task_session_ = json.loads(r.get("task_session"))[session['taskID']]
        # 如果性状不为空
        if len(task_session_['traits']) != 0:
            # 判断是否点击了全选，并更改traitsNames
            if task_session_['traits'][0] != 'all':
                print(task_session_['filePath'] + task_session_['fileName'])
                traitsNames = [traitsList[int(i)] for i in task_session_['traits']]
                # 开始预测
                predict_after.predict(task_session_['filePath'] + task_session_['fileName'], traitsNames,
                                               task_session_['filePath'], r, taskID=session['taskID'],
                                               if_all=False)
            else:
                traits = task_session_['traits'][1:]
                traitsNames = [traitsList[int(i)] for i in traits]
                predict_after.predict(task_session_['filePath'] + task_session_['fileName'], traitsNames,
                                               task_session_['filePath'], r, taskID=session['taskID'],
                                               if_all=False)
        # 设置predict_finish状态为True，并更新到全局变量
        progressdict = json.loads(r.get('progressdict'))[session['taskID']]
        task_session_['predict_finish'] = True
        r.set("task_session", json.dumps({session['taskID']: task_session_}))
        progressdict['predict_finish'] = True
        r.set('progressdict', json.dumps({session['taskID']: progressdict}))
        # 获取taskdict
        taskdict = json.loads(r.get('taskdict'))[session['taskID']]
        # 因为df无法直接json化，所以需要先转化为JSON再传入taskdict，使用时也要先解析
        resultJSON = taskdict['result']
        resultDF = pd.read_json(resultJSON, encoding="utf-8", orient='records')
        # resultDF = pd.read_csv(r"C:\Users\PinkFloyd\OneDrive\桌面\predict.csv")
        # 设置每页可以显示的结果数
        rows_per_page = 3
        # 计算总共的页数
        taskdict['total_pages'] = len(resultDF) // rows_per_page + 1
        # 设置当前页面数
        taskdict['page'] = 1
        # 计算起始行数
        start_row = (taskdict['page'] - 1) * rows_per_page
        # 设置结束行数（当前页面显示的最后一行在resultDF中是第几行）
        end_row = start_row + rows_per_page
        # 使用行号切片resultDF
        df_slice = resultDF.iloc[start_row:end_row]
        # 获取表单的列名
        taskdict['col_names'] = resultDF.columns.tolist()
        # 上传到redis
        r.set('taskdict', json.dumps({session['taskID']: taskdict}))
        # 如果用户同意加入
        if task_session_['join'] == 'yes':
            # 链接本地MongoDB数据库
            client = MongoClient("mongodb://localhost:27017/")
            # 选择test数据库
            db = client.test
            # 选择test下的test collection
            collection = db.test
            # 读取df
            for i in range(len(resultDF)):
                # 读取每行数据
                row = resultDF.iloc[i, :]
                # 读取ID
                seedID = row['acid']
                # 创建字典
                seedDict = {"acid": seedID}
                # 添加性状内容（col_names[0]是id）
                for name in taskdict['col_names'][1:]:
                    trait = name
                    value = f"{row[trait]}(predict, uploaded at{date[0] + '-' + date[1].replace(':', '.')})"
                    # 组装字典
                    seedDict[trait] = value
                # 添加样本
                collection.insert_one(seedDict)
        elif task_session_['join'] == 'no':
            pass
        return render_template('result.html', df=df_slice, total_pages=taskdict['total_pages'],
                               page=taskdict['page'],
                               predict_finish=task_session_['predict_finish'],
                               col_names=taskdict['col_names'])

@app.route("/progress")
def update_progress():
    # 取一个线程
    r = redis.Redis(connection_pool=redis_pool)
    # 取回progressdict
    progressdict = json.loads(r.get('progressdict'))[session['taskID']]
    return progressdict


@app.route('/pagenext')
def pagenext():
    # 取一个线程
    r = redis.Redis(connection_pool=redis_pool)
    # 取回taskdict
    taskdict = json.loads(r.get('taskdict'))[session['taskID']]
    task_session_ = json.loads(r.get('task_session'))[session['taskID']]
    taskdict['page'] += 1
    # 更新page
    r.set('taskdict', json.dumps({session['taskID']: taskdict}))
    rows_per_page = 3
    resultJSON = taskdict['result']
    resultDF = pd.read_json(resultJSON, encoding="utf-8", orient='records')
    start_row = (taskdict['page'] - 1) * rows_per_page
    end_row = start_row + rows_per_page
    df_slice = resultDF.iloc[start_row:end_row]
    return render_template('result.html', df=df_slice, total_pages=taskdict['total_pages'],
                           page=taskdict['page'],
                           predict_finish=task_session_['predict_finish'], col_names=taskdict['col_names'])

@app.route('/pageprev')
def pageprev():
    # 取一个线程
    r = redis.Redis(connection_pool=redis_pool)
    # 取回taskdict
    taskdict = json.loads(r.get('taskdict'))[session['taskID']]
    task_session_ = json.loads(r.get('task_session'))[session['taskID']]
    taskdict['page'] -= 1
    # 更新page
    r.set('taskdict', json.dumps({session['taskID']: taskdict}))
    rows_per_page = 3
    resultJSON = taskdict['result']
    resultDF = pd.read_json(resultJSON, encoding="utf-8", orient='records')
    start_row = (taskdict['page'] - 1) * rows_per_page
    end_row = start_row + rows_per_page
    df_slice = resultDF.iloc[start_row:end_row, :]
    return render_template('result.html', df=df_slice, total_pages=taskdict['total_pages'],
                           page=taskdict['page'],
                           predict_finish=task_session_['predict_finish'], col_names=taskdict['col_names'])


@app.route('/download')
def download_file():
    # 取一个线程
    r = redis.Redis(connection_pool=redis_pool)
    # 取回taskdict
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
        mail_license = 'asidohqwoj1p2je'
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
        stp.sendmail(mail_sender, mail_receivers, mail.as_string())
        stp.quit()
    return render_template('thanksforcontact.html')



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
