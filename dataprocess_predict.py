import pandas as pd
import numpy as np
import csv
import torch
import json
import subprocess
import re


class data_process():

    def __init__(self, genenotype_file, Redis, taskID):
        self.Redis = Redis
        self.taskID = taskID
        pos_list = pd.read_csv(r"./predict/snp.txt")
        self.pos_list = pos_list.iloc[:,0].to_list()
        self.geneotype_path = genenotype_file
        #self.beagle()
        self.get_row()


    def insertRedis(self, taskID, jsonStr):
        msg = json.dumps(jsonStr)
        self.Redis.publish(taskID, msg)

    def beagle(self):
        print("starting beagle")
        process = subprocess.Popen(['java', '-jar', 'beagle.22Jul22.46e.jar', f"gt={self.geneotype_path}", f"out={self.geneotype_path[0:-4]}"], stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        while True:
            line = process.stdout.readline()
            if not line:
                break
            line_decode = line.decode()
            if '[Chr' in line_decode:
                chrNum = re.search('Chr(\d+)', line_decode).group(1)
                if chrNum[0] == '0':
                    chrNum = chrNum[1]
                self.insertRedis(self.taskID, {"title": f"Completing Chr{chrNum}({chrNum}/20)"})
                self.insertRedis(self.taskID, {"progress": f"{int(chrNum) / 20 * 100:.2f}%"})
        process.wait()
        cmd = f'gunzip -f {self.geneotype_path + ".gz"}'
        subprocess.run(cmd, shell=True)

    def get_row(self):
        self.insertRedis(self.taskID, {"title": "Skipping headers"})
        self.insertRedis(self.taskID, {"progress": "20%"})
        skipped = []
        csv.field_size_limit(500 * 1024 * 1024)
        with open(self.geneotype_path, 'r') as csvfile:
            reader = csv.reader(csvfile)
            for i, row in enumerate(reader):
                if row[0].strip()[:2] == '##':
                    skipped.append(i)
            self.skipped = skipped
        self.insertRedis(self.taskID, {"progress": "100%"})

    def get_data(self, dataframe):
        self.insertRedis(self.taskID, {"title": "Converting data"})
        data_marix = np.array(dataframe)
        self.data_marix = data_marix
        self.sample_list = list(dataframe.index)
        data =[]
        total_Sample = data_marix.shape[0]
        for sample in range(total_Sample):
            one_hot = np.zeros((1,data_marix[sample].shape[0],3))
            total_SNP = len(data_marix[sample])
            for snp in range(total_SNP):
                if data_marix[sample][snp] == '1|1' or data_marix[sample][snp] == '1/1':
                    one_hot[0,snp,0] = 1
                    one_hot[0,snp,1] = 1
                    one_hot[0,snp,2] = 0
                elif data_marix[sample][snp] == '0|1' or data_marix[sample][snp] == '0/1':
                    one_hot[0,snp,0] = 1
                    one_hot[0,snp,1] = 0
                    one_hot[0,snp,2] = 1
                else:
                    one_hot[0,snp,0] = 0
                    one_hot[0,snp,1] = 1
                    one_hot[0,snp,2] = 1
                if snp % 500 == 0:
                    self.insertRedis(self.taskID, {"progress": f"{(((snp+1)+(sample*total_SNP)) / (total_Sample*total_SNP))*100:.2f}%"})
            one_hot.resize((206,206,3),refcheck=True)
            data.append(torch.from_numpy(one_hot))

        print(f'dataset already completed!')
        print(len(data))
        return data,self.sample_list
    
    def to_dataset(self):
        skip = self.skipped
        df = pd.read_csv(self.geneotype_path, sep=r"\s+", skiprows=skip)
        self.insertRedis(self.taskID, {"title": "Mapping"})
        self.insertRedis(self.taskID, {"progress": "15.8%"})
        df['ID'] = df['#CHROM'].map(str) + '_' + df['POS'].map(
            int).map(str)
        df = df.drop(columns=[
            'QUAL', 'FILTER', 'INFO', 'FORMAT', '#CHROM', 'POS', 'REF', 'ALT'
        ])

        df = df.set_index('ID')
        self.insertRedis(self.taskID, {"progress": "100"})
        self.insertRedis(self.taskID, {"title": "Extracting SNP information"})
        for i in range(len(df.columns)):
            self.insertRedis(self.taskID, {"progress": f"{(i / len(df.columns))*100:.2f}%"})
            col = df.columns[i]
            df[col] = df[col].str[:3]

        df = df.transpose()
        print(f"df shape {df.shape}")
        predict_df = df[self.pos_list]     
        predict_data,sample_list= self.get_data(predict_df)

        return predict_data,sample_list

























    