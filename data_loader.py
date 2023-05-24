from typing import Any
import torch
import numpy as np
class data_loader (torch.utils.data.Dataset):
    def __init__(self,data):
        self.data = data

    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, index):
        genotype = self.data[index].permute(2,0,1).float()
        # label = torch.Tensor([0 for i in range(len(genotype))])
        return genotype
