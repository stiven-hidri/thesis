import torch
import torch.nn as nn
from .rnn import RNNModel, GRUModel   
from models.mlp_cd import MlpCD 
from models.resnet34_3d import ResNet34_3d

import os            

device = None

def generate_resnet34_3d(cuda=True, pretrain_path=os.path.join(os.path.dirname(__file__), 'saved_models', 'resnet_34_23dataset.pth')):
    
    model = ResNet34_3d(shortcut_type='A', no_cuda=not cuda)
    
    net_dict = model.state_dict()
    
    pretrain = torch.load(pretrain_path, map_location=device)
    pretrain_dict = {k: v for k, v in pretrain['state_dict'].items() if k in net_dict.keys()}
        
    net_dict.update(pretrain_dict)
    model.load_state_dict(net_dict)
    
    for param in model.conv1.parameters():
        param.requires_grad = False
    for param in model.layer1.parameters():
        param.requires_grad = False
    
    
    model.fc = nn.Identity()
    
    return model
            
class BaseModel_Enhanced(nn.Module):
    def __init__(self, dropout = .1, use_clinical_data=True, out_dim_backbone=512, hidden_size_cd=10, hidden_size_fc1 = 512, hidden_size_fc2 = 256):
        super(BaseModel_Enhanced, self).__init__()

        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        self.use_clinical_data = use_clinical_data
        
        input_dim = out_dim_backbone*2 + hidden_size_cd if self.use_clinical_data else out_dim_backbone*2

        self.backbone = generate_resnet34_3d()
        
        if self.use_clinical_data:
            self.cd_backbone = MlpCD()
            path_to_mlpcd_weights = os.path.join(os.path.dirname(__file__), 'saved_models', 'mlp_cd.ckpt')
            checkpoint = torch.load(path_to_mlpcd_weights, map_location=device)
            checkpoint['state_dict'] = {key.replace('model.', ''): value for key, value in checkpoint['state_dict'].items()}
            self.cd_backbone.load_state_dict(checkpoint['state_dict'])
            self.cd_backbone.final_fc = nn.Identity()
            
            for param in self.cd_backbone.parameters():
                param.requires_grad = False


        self.dropout = nn.Dropout(p=dropout)  # Dropout with 50% probability
        self.relu = nn.ReLU()
        
        self.final_fc1 = nn.Linear(input_dim, hidden_size_fc1)
        self.bn1 = nn.BatchNorm1d(hidden_size_fc1)
        
        self.final_fc2 = nn.Linear(hidden_size_fc1, hidden_size_fc2)
        self.bn2 = nn.BatchNorm1d(hidden_size_fc2)        
        
        self.final_fc3 = nn.Linear(hidden_size_fc2, 1)
        
    
    def forward(self, mr, rtd, clinical_data):
        mr, rtd = mr.unsqueeze(1), rtd.unsqueeze(1)
        
        feat_mr = self.backbone(mr)
        feat_rtd = self.backbone(rtd)
        
        # feat = (feat_mr + feat_rtd) / 2
        
        if self.use_clinical_data:
            feat = torch.cat([feat_mr, feat_rtd, self.cd_backbone(clinical_data)], dim=1)
        else:
            feat = torch.cat([feat_mr, feat_rtd], dim=1)
        
        out = self.dropout(self.relu(self.bn1(self.final_fc1(feat))))
        out = self.dropout(self.relu(self.bn2(self.final_fc2(out))))
        out = self.final_fc3(out)

        return out