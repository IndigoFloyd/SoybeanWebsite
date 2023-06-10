import os
import torch
from data_loader import *
from dataprocess_predict import *
from torch.utils.data import DataLoader
# from AlexNet_206_p import *
# from AlexNet_206 import *
import time
import json

class predict():

    TOKENIZERS_PARALLELISM= False
    def __init__(self, genotype_path, trait_for_predict, save_path, Redis, taskID="", if_all = False):
        self.Redis = Redis
        self.path = r'./predict/weight'
        self.taskID = taskID
        self.progressdict = {"title": "", "progress": "", "predict_finish": False}
        self.taskdict = {"result": pd.DataFrame(), "page": 0, "total_pages": 0, "col_names": []}
        #构建需要预测的性状列表
        n_trait = ['protein', 'oil', 'SdWgt', 'Yield', 'R8', 'R1', 'Hgt', 'Linoleic', 'Linolenic']
        p_trait = ['ST', 'FC', 'P_DENS', 'POD']
        if not if_all:
            self.n_trait = []
            self.p_trait = []
            for trait in trait_for_predict:
                if trait in n_trait:
                    self.n_trait.append(trait)
                elif trait in p_trait:
                    self.p_trait.append(trait)
                else:
                    print("Error:Couldn't find target trait!")
            self.trait_list = trait_for_predict
        else:
            self.n_trait, self.p_trait = n_trait, p_trait
            self.trait_list = self.n_trait + self.p_trait

        #读取基因型文件以及存储路径
        self.vcf_path = rf'{genotype_path}'
        self.save_dir = rf'{save_path}'

        #获取各个性状的最值、对应类别号的字典并转换为列表        
        max_min = pd.read_csv(r'./predict/n_trait.txt',header=None)
        p_dict = open(r'./predict/p_trait.txt','r').readlines()
        self.p_data = [i.strip() for i in p_dict]
        self.n_data = np.array(max_min.iloc[:]).tolist()
        self.forward()

    def insertRedis(self):
        msg = json.dumps({self.taskID: self.progressdict})
        self.Redis.set('progressdict', msg)

    def insertTaskRedis(self):
        msg = json.dumps({self.taskID: self.taskdict})
        self.Redis.set('taskdict', msg)

    def timer(self):
        return time.time()
    
    def forward(self):
        t1 = self.timer()
        #数据预处理
        data_list = data_process(self.vcf_path, self.Redis, self.taskID)
        #返回处理后的数据以及需要预测的样本列表
        predict_data,sample_list = data_list.to_dataset()
        #构造迭代器
        loader = DataLoader(data_loader(predict_data),batch_size=1,shuffle=False,num_workers=0)
        result = {}
        t2 = self.timer()
        # print(f'Data process has done! Use time:{t2-t1}','\n','Start data predict')
        #对性状列表中的所有性状进行预测
        for index, (feature) in enumerate(loader):
            feature = feature.to('cuda:0')
            het = []
            self.progressdict['progress'] = f"{(index+1) / len(sample_list) * 100:.2f}%"
            self.insertRedis()
            # print(f"({index+1} / {len(sample_list)})-------{(index+1) / len(sample_list) * 100:.2f}%")
            for trait in self.trait_list:
                self.progressdict['title'] = f"Predicting: Sample {index + 1} ({index+1} / {len(sample_list)})'s trait {trait}"
                self.insertRedis()
                weight_path = os.path.join(self.path, f'{trait}_best.pt')
                net = torch.load(weight_path, map_location="cuda:0")
                net.eval()
                y_het = net(feature)
                #若为质量性状，则返回预测值中概率最大一类的索引
                if trait in self.p_trait:
                    y_het =  np.argmax(y_het.to('cpu').detach().numpy(),axis=1)
                #将该样本的每一个性状加入列表
                    het.append(y_het[0])
                else:
                    het.append(y_het.to('cpu').detach().numpy()[0][0])
            #构建结果字典，键值对： 样本：[性状1，性状2……]
            result[sample_list[index]] = het
        t3 = self.timer()
        # print(r'Predict has done! Use time:{t3-t2}','\n','Start data restore')

        #将结果列表转为dataframe后进行转置，行索引为样本ID，列索引为性状预测值
        result = pd.DataFrame(result).transpose()
        result.columns = self.trait_list

        #对数量性状的归一化数据、质量性状的分类数据进行还原
        traitnum = 0
        for trait in self.trait_list:
            traitnum += 1
            self.progressdict['title'] = f"Restoring trait data: {trait}"
            self.progressdict['progress'] = f"{(traitnum / len(self.trait_list) * 100):.2f}%"
            self.insertRedis()
            #质量性状归一化数据进行还原
            if trait in self.n_trait:
                for i in self.n_data:
                    print(i)
                    if trait in i[0]:
                        max_of_trait,min_of_trait = float(i[0].split(";")[2]),float(i[0].split(";")[4])
                        break
                result[trait] = result[trait]*(max_of_trait - min_of_trait) + min_of_trait
            #根据数据预处理过程中生成的 性状：类别号 字典，对性状进行map还原
            else:
                for i in self.p_data:
                    if trait in i:
                        dic = eval("{" + i.split("{")[1])
                        break
                dic = dict(zip(dic.values(), dic.keys()))
                result[trait] = result[trait].map(dic)
        #将预测数据储存为csv
        result.index.name = "acid"
        result = result.reset_index()
        self.taskdict['result'] = result.to_json()
        # 把结果传出去
        self.insertTaskRedis()
        result.to_csv(os.path.join(self.save_dir, 'predict.csv'), index=False)
        self.progressdict['title'] = "Finish"
        self.progressdict['progress'] = "100%"
        self.insertRedis()
        t4 = self.timer()
        print(f'Restore has done! Use time:{t4-t3} Result has saved in save path')
