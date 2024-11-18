import os
import pickle
import matplotlib.pyplot as plt
import numpy as np
from utils.augment import *
from utils.utils import clear_directory_content
import torchio as tio

def test_augmentation():
    path_to_data = os.path.join(os.path.dirname(__file__),'..', 'data', 'processed', 'global_data.pkl')
    transform_big = tio.Compose([
        tio.RandomFlip(axes=(0, 1, 2), flip_probability=0.5),
        tio.RandomElasticDeformation(
            num_control_points=7,
            max_displacement=5.0,
            locked_borders=2,
            image_interpolation='linear'
        )
    ])
    transform_small = tio.Compose([
        tio.RandomFlip(axes=(0, 1, 2), flip_probability=0.5)
    ])
    
    OUTPUT_PATH = os.path.join(os.path.dirname(__file__), 'display', 'augmentation')
    os.makedirs(OUTPUT_PATH, exist_ok=True)
    clear_directory_content(OUTPUT_PATH)
    
    with open(path_to_data, 'rb') as input_file:
        data = pickle.load(input_file)
        MAX_SAMPLES = 10
        chosen_samples = random.sample(range(len(data['mr'])), k=MAX_SAMPLES)
        for cnt, i_sample in enumerate(chosen_samples):
            print(f"{cnt+1}/{MAX_SAMPLES}", end='\r')
            mr, rtd = torch.tensor(data['mr'][i_sample]).unsqueeze(0), torch.tensor(data['rtd'][i_sample]).unsqueeze(0)
            
            subject = tio.Subject(
                mr=tio.ScalarImage(tensor=mr), 
                rtd=tio.ScalarImage(tensor=rtd)
            )
            
            transformed_subject = transform_big(subject) if mr.shape[1]*mr.shape[2]*mr.shape[3] > 20**3 else transform_small(subject)
            mr_aug = transformed_subject['mr'].data
            rtd_aug = transformed_subject['rtd'].data
            
            stuff = [np.array(mr.squeeze()), np.array(mr_aug.squeeze()), np.array(rtd.squeeze()), np.array(rtd_aug.squeeze())]
            
            c = min(8, stuff[0].shape[2])
            indexes =  np.linspace(0, stuff[0].shape[2], c, dtype=int)[1:-1]
            c-=2
            fig, axes = plt.subplots(len(stuff), c, figsize=(20, 10))
                
            for i, s in enumerate(stuff):
                axes[i, 0].set_title(['MRI', 'MRI augmented', 'RTD', 'RTD augmented'][i])    
                for j in range(c):
                    axes[i, j].imshow(s[:, :, indexes[j]])
                    axes[i, j].axis('off')
        
            plt.savefig(os.path.join(os.path.dirname(__file__), 'display', 'augmentation', f'{i_sample}_aug.png'), dpi=300)
            plt.close()
                        
    print("Done!", end='\r')

if __name__ == '__main__':
    test_augmentation()

