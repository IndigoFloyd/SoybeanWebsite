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
        self.IsMissing = False
        # Build a list of traits to predict
        n_trait = ['protein', 'oil', 'SdWgt', 'Yield', 'R8', 'R1', 'Hgt', 'Linoleic', 'Linolenic', 'Palmitic', 'Stearic', 'Oleic']
        p_trait = ['MG', 'SQ', 'ST', 'Ldg', 'P_CLR', 'Mot', 'P_FRM', 'SC_L', 'SC_CLR', 'Stem term', 'H_CLR', 'PRR1', 'SCN3', 'FC', 'P_DENS', 'POD']
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

        # Read genotype file and storage path
        self.vcf_path = rf'{genotype_path}'
        self.save_dir = rf'{save_path}'

        # Get the most value of each trait, the dictionary of the corresponding category number and convert it into a list       
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
        # data preprocessing
        data_list = data_process(self.vcf_path, self.Redis, self.taskID)
        # Return the processed data and a list of samples that need to be predicted
        predict_data,sample_list = data_list.to_dataset()
        self.IsMissing = data_list.IsMissing
        # Construct iterator
        loader = DataLoader(data_loader(predict_data),batch_size=1,shuffle=False,num_workers=0)
        result = {}
        t2 = self.timer()
        # print(f'Data process has done! Use time:{t2-t1}','\n','Start data predict')
        # Make predictions for all traits in the trait list
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
                # If it is a quality trait, return the index of the class with the highest probability in the predicted value
                if trait in self.p_trait:
                    y_het =  np.argmax(y_het.to('cpu').detach().numpy(),axis=1)
                # Add each trait of the sample to the list
                    het.append(y_het[0])
                else:
                    het.append(y_het.to('cpu').detach().numpy()[0][0])
                del net
                del y_het
                torch.cuda.empty_cache()
            # Build a result dictionary, key-value pairs: Sample: [trait 1, trait 2...]
            result[sample_list[index]] = het
            torch.cuda.empty_cache()
        t3 = self.timer()
        # print(r'Predict has done! Use time:{t3-t2}','\n','Start data restore')

        # Convert the result list into a dataframe and then transpose, the row index is the sample ID, and the column index is the predicted value of the trait
        result = pd.DataFrame(result).transpose()
        result.columns = self.trait_list

        # Restore the normalized data of quantitative traits and the classified data of qualitative traits
        traitnum = 0
        for trait in self.trait_list:
            traitnum += 1
            self.progressdict['title'] = f"Restoring trait data: {trait}"
            self.progressdict['progress'] = f"{(traitnum / len(self.trait_list) * 100):.2f}%"
            self.insertRedis()
            # Quality traits normalized data for reduction
            if trait in self.n_trait:
                for i in self.n_data:
                    print(i)
                    if trait in i[0]:
                        max_of_trait,min_of_trait = float(i[0].split(";")[2]),float(i[0].split(";")[4])
                        break
                result[trait] = result[trait]*(max_of_trait - min_of_trait) + min_of_trait
            # According to the traits generated during the data preprocessing process: category number dictionary, the map restores the traits
            else:
                for i in self.p_data:
                    if trait in i:
                        dic = eval("{" + i.split("{")[1])
                        break
                dic = dict(zip(dic.values(), dic.keys()))
                result[trait] = result[trait].map(dic)
        # Store forecast data as csv
        result.index.name = "acid"
        result = result.reset_index()
        self.taskdict['result'] = result.to_json()
        # pass the result out
        self.insertTaskRedis()
        result.to_csv(os.path.join(self.save_dir, 'predict.csv'), index=False)
        self.progressdict['title'] = "Finish"
        self.progressdict['progress'] = "100%"
        self.insertRedis()
        t4 = self.timer()
        print(f'Restore has done! Use time:{t4-t3} Result has saved in save path')
