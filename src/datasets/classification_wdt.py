import os
import pickle
from torch.utils.data import Dataset
from utils.augment import combine_aug
from torchvision import transforms


class ClassifierDatasetSplitWDT(Dataset):
    def __init__(self, data: dict, split_name: str, p_augmentation=.0, augmentation_techniques=[]):
        self.data = data
        self.split_name = split_name
        self.p_augmentation = p_augmentation
        self.augmentation_techniques = augmentation_techniques
        self.DATA_PATH = os.path.join(os.path.dirname(__file__), '..','..', 'data', 'processed')
        with open(os.path.join(self.DATA_PATH, f'statistics.pkl'), 'rb') as f:
            self.statistics = pickle.load(f)

    def __len__(self):
        return len(self.data['label'])
    
    def __getitem__(self, idx):
        mr_rtd_fusion = self.data['mr_rtd_fusion'][idx]
        clinic_data = self.data['clinic_data'][idx]
        label = self.data['label'][idx]
        
        if self.split_name == 'train':
            mr_rtd_fusion, _ = combine_aug(mr_rtd_fusion, rtd=None, p_augmentation=self.p_augmentation, augmentations_techinques=self.augmentation_techniques)
        
        return mr_rtd_fusion, clinic_data, label

    def __iter__(self):
        for i in range(self.__len__()):
            yield self.__getitem__(i)

class ClassifierDatasetWDT(Dataset):
    def __init__(self, p_augmentation=.3, augmentation_techniques=['shear', 'gaussian_noise', 'flip', 'rotate', 'brightness']):
        super().__init__()
        self.p_augmentation = p_augmentation
        self.augmentation_techniques = augmentation_techniques
        self.DATA_PATH = os.path.join(os.path.dirname(__file__), '..','..', 'data', 'processed')
        self.train, self.test, self.val = self.__load__()

    def __len__(self):
        return len(self.train['label'])

    def __load__(self) -> None:
        with open(os.path.join(self.DATA_PATH, 'train_set.pkl'), 'rb') as f:
            train = pickle.load(f)
            
        with open(os.path.join(self.DATA_PATH, 'test_set.pkl'), 'rb') as f:
            test = pickle.load(f)
            
        with open(os.path.join(self.DATA_PATH, 'val_set.pkl'), 'rb') as f:
            val = pickle.load(f)
            
        

        return train, test, val
    
    def create_splits(self):
        return ClassifierDatasetSplitWDT(self.train, 'train', p_augmentation=self.p_augmentation, augmentation_techniques=self.augmentation_techniques), ClassifierDatasetSplitWDT(self.test, 'test'), ClassifierDatasetSplitWDT(self.val, 'val')
