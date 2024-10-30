import torch
import torch.nn as nn
import torch.nn.functional as F
from models.mlp_cd import MlpCD
import os
import torch.nn.init as init

class BaseModel_EnhancedV2(nn.Module):
    def __init__(self, dropout=.3, out_dim_clincal_features=10, use_clinical_data=True, out_dim_cnn=256, hidden_size_fc1=256, hidden_size_fc=256):
        super(BaseModel_EnhancedV2, self).__init__()
        
        self.use_clinical_data = use_clinical_data
        self.out_dim_clincal_features = out_dim_clincal_features
        
        # Lesion input branch
        self.les_conv1 = nn.Conv3d(1, 32, kernel_size=3, padding=1)
        self.les_pool1 = nn.MaxPool3d(2)
        self.les_bn1 = nn.BatchNorm3d(32)
        
        self.les_conv2 = nn.Conv3d(32, 64, kernel_size=3, padding=1)
        self.les_pool2 = nn.MaxPool3d(2)
        self.les_bn2 = nn.BatchNorm3d(64)
        
        self.les_conv3 = nn.Conv3d(64, 128, kernel_size=3, padding=1)
        self.les_pool3 = nn.MaxPool3d(2)
        self.les_bn3 = nn.BatchNorm3d(128)
        
        self.les_conv4 = nn.Conv3d(128, out_dim_cnn, kernel_size=3, padding=1)
        self.les_pool4 = nn.MaxPool3d(2)
        self.les_bn4 = nn.BatchNorm3d(out_dim_cnn)
        
        self.les_global_pool = nn.AdaptiveAvgPool3d(1)
        self.les_fc1 = nn.Linear(out_dim_cnn, 512)
        self.les_dropout = nn.Dropout(dropout)
        self.les_fc2 = nn.Linear(512, out_dim_cnn)
        
        # Dose input branch
        self.dose_conv1 = nn.Conv3d(1, 32, kernel_size=3, padding=1)
        self.dose_pool1 = nn.MaxPool3d(2)
        self.dose_bn1 = nn.BatchNorm3d(32)
        
        self.dose_conv2 = nn.Conv3d(32, 64, kernel_size=3, padding=1)
        self.dose_pool2 = nn.MaxPool3d(2)
        self.dose_bn2 = nn.BatchNorm3d(64)
        
        self.dose_conv3 = nn.Conv3d(64, 128, kernel_size=3, padding=1)
        self.dose_pool3 = nn.MaxPool3d(2)
        self.dose_bn3 = nn.BatchNorm3d(128)
        
        self.dose_conv4 = nn.Conv3d(128, out_dim_cnn, kernel_size=3, padding=1)
        self.dose_pool4 = nn.MaxPool3d(2)
        self.dose_bn4 = nn.BatchNorm3d(out_dim_cnn)
        
        self.dose_global_pool = nn.AdaptiveAvgPool3d(1)
        self.dose_fc1 = nn.Linear(out_dim_cnn, 512)
        self.dose_dropout = nn.Dropout(dropout)
        self.dose_fc2 = nn.Linear(512, out_dim_cnn)
            
        if self.use_clinical_data:
            self.cd_backbone = MlpCD()
            path_to_mlpcd_weights = os.path.join(os.path.dirname(__file__), 'saved_models', 'mlp_cd.ckpt')
            checkpoint = torch.load(path_to_mlpcd_weights)
            checkpoint['state_dict'] = {key.replace('model.', ''): value for key, value in checkpoint['state_dict'].items()}
            self.cd_backbone.load_state_dict(checkpoint['state_dict'])
            self.cd_backbone.final_fc = nn.Identity()
            
            for param in self.cd_backbone.fc1.parameters():
                param.requires_grad = False
            for param in self.cd_backbone.fc2.parameters():
                param.requires_grad = False
                
        input_dim = out_dim_cnn*2 + out_dim_clincal_features if self.use_clinical_data else out_dim_cnn*2
            
        self.dropout = nn.Dropout(p=dropout)
        self.relu = nn.ReLU()
        
        self.final_fc1 = nn.Linear(input_dim, hidden_size_fc)
        self.bn1 = nn.BatchNorm1d(hidden_size_fc)
        
        # self.final_fc2 = nn.Linear(hidden_size_fc1, hidden_size_fc2)
        # self.bn2 = nn.BatchNorm1d(hidden_size_fc2)        
        
        self.final_fc = nn.Linear(hidden_size_fc, 1)
        
    def forward(self, les_input, dose_input, clinical_input=None):
        
        les_input = les_input.unsqueeze(1)
        dose_input = dose_input.unsqueeze(1)
        
        if self.use_clinical_data:
            clinical_input = clinical_input.squeeze()
        
        # Lesion branch
        x = self.les_pool1(F.relu(self.les_bn1(self.les_conv1(les_input))))        
        x = self.les_pool2(F.relu(self.les_bn2(self.les_conv2(x))))
        x = self.les_pool3(F.relu(self.les_bn3(self.les_conv3(x))))
        x = self.les_pool4(F.relu(self.les_bn4(self.les_conv4(x))))
        
        x = self.les_global_pool(x).view(x.size(0), -1)
        
        x = self.les_dropout(F.relu(self.les_fc1(x)))
        les_output = F.relu(self.les_fc2(x))
        
        # Dose branch
        x = self.dose_pool1(F.relu(self.dose_bn1(self.dose_conv1(dose_input))))
        x = self.dose_pool2(F.relu(self.dose_bn2(self.dose_conv2(x))))
        x = self.dose_pool3(F.relu(self.dose_bn3(self.dose_conv3(x))))
        x = self.dose_pool4(F.relu(self.dose_bn4(self.dose_conv4(x))))
        
        x = self.dose_global_pool(x).view(x.size(0), -1)
        
        x = self.dose_dropout(F.relu(self.dose_fc1(x)))
        dose_output = F.relu(self.dose_fc2(x))
        
        # Clinical branch
        if self.use_clinical_data:
            
            clinical_output = self.cd_backbone(clinical_input)

            if clinical_output.dim() == 1:
                clinical_output = clinical_output.unsqueeze(0)

            combined = torch.cat((les_output, dose_output, clinical_output), dim=1)
            
        else:
            combined = torch.cat((les_output, dose_output), dim=1)
        
        out = self.dropout(self.relu(self.bn1(self.final_fc1(combined))))
        # out = self.dropout(self.relu(self.bn2(self.final_fc2(out))))
        out = self.final_fc(out)
        
        return out