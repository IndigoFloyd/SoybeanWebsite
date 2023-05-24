import torch
from torch import nn 
from torch.nn import Module
class CA_Block(nn.Module):
    def __init__(self, channel, h, w, reduction=16):
        super(CA_Block, self).__init__()
 
        self.h = h
        self.w = w
 
        self.avg_pool_x = nn.AdaptiveAvgPool2d((h, 1))
        self.avg_pool_y = nn.AdaptiveAvgPool2d((1, w))
 
        self.conv_1x1 = nn.Conv2d(in_channels=channel, out_channels=channel//reduction, kernel_size=1, stride=1, bias=False)
 
        self.relu = nn.ReLU()
        self.bn = nn.BatchNorm2d(channel//reduction)
 
        self.F_h = nn.Conv2d(in_channels=channel//reduction, out_channels=channel, kernel_size=1, stride=1, bias=False)
        self.F_w = nn.Conv2d(in_channels=channel//reduction, out_channels=channel, kernel_size=1, stride=1, bias=False)
 
        self.sigmoid_h = nn.Sigmoid()
        self.sigmoid_w = nn.Sigmoid()
 
    def forward(self, x):
 
        x_h = self.avg_pool_x(x).permute(0, 1, 3, 2)
        x_w = self.avg_pool_y(x)
 
        x_cat_conv_relu = self.relu(self.conv_1x1(torch.cat((x_h, x_w), 3)))
 
        x_cat_conv_split_h, x_cat_conv_split_w = x_cat_conv_relu.split([self.h, self.w], 3)
 
        s_h = self.sigmoid_h(self.F_h(x_cat_conv_split_h.permute(0, 1, 3, 2)))
        s_w = self.sigmoid_w(self.F_w(x_cat_conv_split_w))
 
        out = x * s_h.expand_as(x) * s_w.expand_as(x)
 
        return out

class AlexNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(

            nn.Conv2d(3,32,kernel_size=3,padding=1,padding_mode='reflect',stride=1,bias=False),
            nn.BatchNorm2d(32),
            nn.Dropout(0.3),
            nn.ReLU(),

            CA_Block(32,206,206,reduction=16),

            nn.Conv2d(32,64,kernel_size=4,padding=1,padding_mode='reflect',stride=2,bias=False),
            nn.BatchNorm2d(64),
            nn.Dropout(0.3),
            nn.ReLU(),

            nn.Conv2d(64,64,kernel_size=3,padding=1,padding_mode='reflect',stride=2,bias=False),
            nn.BatchNorm2d(64),
            nn.Dropout(0.3),
            nn.ReLU(),

            nn.Conv2d(64,64,kernel_size=3,padding=1,padding_mode='reflect',stride=1,bias=False),
            nn.BatchNorm2d(64),
            nn.Dropout(0.3),
            nn.ReLU(),

            nn.Conv2d(64,128,kernel_size=3,padding=1,padding_mode='reflect',stride=1,bias=False),
            nn.BatchNorm2d(128),
            nn.Dropout(0.3),
            nn.ReLU(),
            
            nn.Conv2d(128,128,kernel_size=3,padding=1,padding_mode='reflect',stride=1,bias=False),
            nn.BatchNorm2d(128),
            nn.Dropout(0.3),
            nn.ReLU(),

            nn.Conv2d(128,256,kernel_size=2,stride=2,bias=False),
            nn.BatchNorm2d(256),
            nn.Dropout(0.3),
            nn.ReLU(),

            nn.Conv2d(256,256,kernel_size=3,padding=1,padding_mode='reflect',stride=1,bias=False),
            nn.BatchNorm2d(256),
            nn.Dropout(0.3),
            nn.ReLU(),

            nn.Conv2d(256,512,kernel_size=2,stride=2,bias=False),
            nn.BatchNorm2d(512),
            nn.Dropout(0.3),
            nn.ReLU(),

            nn.Conv2d(512,512,kernel_size=3,padding=1,padding_mode='reflect',stride=1,bias=False),
            nn.BatchNorm2d(512),
            nn.Dropout(0.3),
            nn.ReLU(),
            
            nn.Conv2d(512,1024,kernel_size=3,padding=1,padding_mode='reflect',stride=2,bias=False),
            nn.BatchNorm2d(1024),
            nn.Dropout(0.3),
            nn.ReLU(),
            
            nn.Conv2d(1024,1024,kernel_size=3,padding=1,padding_mode='reflect',stride=1,bias=False),
            nn.BatchNorm2d(1024),
            nn.Dropout(0.3),
            nn.ReLU(),
            
            CA_Block(1024,7,7,reduction=16),           
            
            nn.Flatten(),
            nn.Dropout(0.3),
            nn.ReLU(),

            # nn.Linear(50176,6400),
            # nn.Dropout(0.4),
            # nn.ReLU(),

            nn.Linear(50176,1),
            # nn.Sigmoid()
        )
    def modules(self):
        model_name = 'AlexNet_deep'
        return self.net,model_name
