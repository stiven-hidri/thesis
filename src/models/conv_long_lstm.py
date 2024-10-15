import torch
import torch.nn as nn
import torchvision.models as models
import timm
from torchvision.models import shufflenet_v2_x1_5
class InceptionV2Features(nn.Module):
    def __init__(self, inception_v2_is_chosen=False, out_features=256):
        super(InceptionV2Features, self).__init__()
        
        self.inception_v2_is_chosen = inception_v2_is_chosen
        
        if self.inception_v2_is_chosen:
        
            self.backbone = timm.create_model('inception_resnet_v2', pretrained=False, num_classes=0)
            
            self.backbone.conv2d_1a.conv = nn.Conv2d(
                in_channels=2,  # Change from 3 to 2 channels
                out_channels=self.backbone.conv2d_1a.conv.out_channels,
                kernel_size=(3, 3),
                stride=(1, 1),
                padding=(1, 1),
                bias=self.backbone.conv2d_1a.conv.bias
            )
            
            self.fc = nn.Linear(self.backbone.conv2d_7b.conv.out_channels, out_features)
        else:
            self.backbone = shufflenet_v2_x1_5()
            
            self.backbone.conv1[0] = nn.Conv2d(2, 24, kernel_size=(3, 3), stride=(2, 2), padding=(1, 1), bias=False)
            
            # self.backbone.conv1 = nn.Conv2d(
            #     in_channels=2,  # Change to 2 for grayscale
            #     out_channels=self.backbone.conv1.out_channels,
            #     kernel_size=(7, 7),
            #     stride=(2, 2),
            #     padding=(3, 3),
            #     bias=False
            # )
            
            # # Remove the final fully connected layer
            self.fc = nn.Linear(self.backbone.fc.in_features, out_features)
            self.backbone.fc = nn.Identity()

    def forward(self, x):
        return self.fc(self.backbone(x))

# LSTM Model
class ConvLongRNN(nn.Module):
    def __init__(self, dropout:.3, hidden_size=45, num_layers = 2, output_dim=1, out_features=256, input_clinical_data = 48, output_clinical_data = 10, inception_v2_is_chosen=False):
        super(ConvLongRNN, self).__init__()
        
        self.backbone = InceptionV2Features(out_features=out_features, inception_v2_is_chosen=inception_v2_is_chosen)
        self.lstm = nn.LSTM(
            input_size=out_features+output_clinical_data,  # Assumes InceptionV2 outputs 2048 features
            hidden_size=hidden_size, 
            num_layers=num_layers, 
            batch_first=True,
            dropout=dropout
        )
        
        self.fc_clinical_data = nn.Linear(input_clinical_data, output_clinical_data)

        self.fc = nn.Linear(hidden_size, output_dim)  # Binary classification (recurrence or stability)

    def forward(self, mr, rtd, clinical_data):
        
        batch_size, depth, height, width = mr.shape
        channels = 2
        
        combined = torch.stack([mr, rtd], dim=2).view(-1, channels, height, width)

        features = self.backbone(combined).view(batch_size, depth, -1)
        features_clinical_data = torch.relu(self.fc_clinical_data(clinical_data)).unsqueeze(1).repeat(1, depth, 1)
        
        final_features = torch.cat((features, features_clinical_data), dim=-1)

        lstm_out, _ = self.lstm(final_features)

        output = self.fc(lstm_out[:, -1, :])

        return output
    
    # def forward(self, mr, rtd):
        
    #     batch_size, depth, height, width = mr.shape
        
    #     combined = torch.stack([mr, rtd], dim=2)
        
    #     channels = combined.shape[2]
        
    #     reshaped_input = combined.view(-1, channels, height, width)

    #     features = self.backbone(reshaped_input)

    #     features = features.view(batch_size, depth, -1)

    #     lstm_out, _ = self.lstm(features)

    #     output = self.fc(lstm_out[:, -1, :])

    #     return output

