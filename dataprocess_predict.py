import pandas as pd
import numpy as np
import csv
import torch
import json
import subprocess
import re
import math


class data_process():

    def __init__(self, genenotype_file, Redis, taskID):
        self.Redis = Redis
        self.taskID = taskID
        self.progressdict = {"title": "", "progress": "", "predict_finish": False}
        pos_list = pd.read_csv(r"./predict/snp.txt")
        self.pos_list = pos_list.iloc[:,0].to_list()
        self.geneotype_path = genenotype_file
        #self.beagle()
        self.get_row()


    def insertRedis(self):
        msg = json.dumps({self.taskID: self.progressdict})
        self.Redis.set('progressdict', msg)

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
                self.progressdict['title'] = f"Completing Chr{chrNum}({chrNum}/20)"
                self.progressdict['progress'] = f"{int(chrNum) / 20 * 100:.2f}%"
                self.insertRedis()
        process.wait()
        cmd = f'gunzip -f {self.geneotype_path + ".gz"}'
        subprocess.run(cmd, shell=True)

    def get_row(self):
        self.progressdict['title'] = "Skipping headers"
        self.progressdict['progress'] = "20%"
        self.insertRedis()
        skipped = []
        csv.field_size_limit(500 * 1024 * 1024)
        with open(self.geneotype_path, 'r') as csvfile:
            reader = csv.reader(csvfile)
            for i, row in enumerate(reader):
                if row[0].strip()[:2] == '##':
                    skipped.append(i)
            self.skipped = skipped
        self.progressdict['progress'] = "100%"
        self.insertRedis()

    def get_data(self, dataframe):
        self.progressdict['title'] = "Converting data"
        self.progressdict['progress'] = "0%"
        self.insertRedis()
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
                    self.progressdict['progress'] = f"{(((snp+1)+(sample*total_SNP)) / (total_Sample*total_SNP))*100:.2f}%"
                    self.insertRedis()
            one_hot.resize((206,206,3),refcheck=True)
            data.append(torch.from_numpy(one_hot))

        print(f'dataset already completed!')
        print(len(data))
        return data,self.sample_list
    
    def to_dataset(self):
        skip = self.skipped
        df = pd.read_csv(self.geneotype_path, sep=r"\s+", skiprows=skip)
        self.progressdict['title'] = "Mapping"
        self.progressdict['progress'] = "15.8%"
        self.insertRedis()
        df['ID'] = df['#CHROM'].map(str) + '_' + df['POS'].map(
            int).map(str)
        df = df.drop(columns=[
            'QUAL', 'FILTER', 'INFO', 'FORMAT', '#CHROM', 'POS', 'REF', 'ALT'
        ])

        df = df.set_index('ID')
        self.progressdict['progress'] = "100%"
        self.insertRedis()
        self.progressdict['title'] = "Extracting SNP information"
        self.insertRedis()
        for i in range(len(df.columns)):
            self.progressdict['progress'] = f"{(i / len(df.columns))*100:.2f}%"
            self.insertRedis()
            col = df.columns[i]
            df[col] = df[col].str[:3]
        df = df.transpose()
        vcf_pos = df.columns.to_list()
        self.progressdict['title'] = "Filling the missing pos"
        self.progressdict['progress'] = "23.4%"
        self.insertRedis()
        temp = set(self.pos_list).difference(set(vcf_pos))
        if len(temp):
            df2 = np.full((df.shape[0], len(temp)), './.')
            df2 = pd.DataFrame(df2, columns=temp)
            df2.index = df.index.to_list()
            df = pd.concat([df, df2], axis=1)
        self.progressdict['progress'] = "100%"
        self.insertRedis()
        # for pos in range(len(self.pos_list)):
        #     if pos % 500 == 0:
        #         self.progressdict['progress'] = f"{pos / len(self.pos_list) * 100:.2f}%"
        #         self.insertRedis()
        #     if self.pos_list[pos] in vcf_pos:
        #         continue
        #     else:
        #         df[self.pos_list[pos]] = alt
        print(f"df shape {df.shape}")
        predict_df = df[self.pos_list]
        self.progressdict['progress'] = "100%"
        self.insertRedis()
        predict_data,sample_list= self.get_data(predict_df)

        return predict_data,sample_list

























    