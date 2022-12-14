import os
import torch
import torch.nn.functional as F
import pytorch_lightning as pl
from torch import optim
import segmentation_models_pytorch as smp
from segmentation_models_pytorch.datasets.spine_dataset import Spine_Dataset

from torch.utils.data import DataLoader, random_split
from configs import parse_args
from custom_loss.dice_score import dice_loss
import matplotlib.pyplot as plt
from train_spine import YoneModel

path = "./spine_proj/resnet50-wbce/checkpoints/"
file_name = os.listdir(path)
file_path = os.path.join(path, file_name[0])

args = parse_args()

model = YoneModel.load_from_checkpoint(
    file_path,
    arch=args.arch,
    encoder_name=args.backbone,
    encoder_weights=None,
    in_channels=1,
    out_classes=1,
    lr=args.learning_rate,
)

# 1. create dataset
dataset = Spine_Dataset(
    images_dir=args.images_dir,
    masks_dir=args.masks_dir,
    augmentation=args.aug,
)

# 2. split dataset
n_val = int(len(dataset) * args.val_percent)
n_train = len(dataset) - n_val
train_set, val_set = random_split(dataset, [n_train, n_val], generator=torch.Generator().manual_seed(0))

# 3. generate dataloader
loader_args = dict(batch_size=args.batch_size, num_workers=16, pin_memory=True)
train_dataloader = DataLoader(dataset=train_set, shuffle=True, **loader_args)  # type: ignore os.cpu_count()
val_loader = DataLoader(dataset=val_set, shuffle=True, **loader_args)
train_dataloader = DataLoader(dataset=dataset, shuffle=True, **loader_args)

batch = next(iter(val_loader))

with torch.no_grad():
    model.eval()
    logits = model(batch["img"])
pr_masks = (logits > 0.5).long()

cnt = 0
for image, gt_mask, pr_mask in zip(batch["img"], batch["mask"], pr_masks):
    cnt = cnt + 1
    plt.figure(figsize=(10, 5))

    plt.subplot(1, 3, 1)
    plt.imshow(image.numpy().transpose(1, 2, 0))  # convert CHW -> HWC
    plt.title("Image")
    plt.axis("off")

    plt.subplot(1, 3, 2)
    plt.imshow(gt_mask.numpy().squeeze())  # just squeeze classes dim, because we have only one class
    plt.title("Ground truth")
    plt.axis("off")

    plt.subplot(1, 3, 3)
    plt.imshow(pr_mask.numpy().squeeze())  # just squeeze classes dim, because we have only one class
    plt.title("Prediction")
    plt.axis("off")
    plt.savefig(f"./predicted_results/compare{cnt}.png")
    plt.show()
