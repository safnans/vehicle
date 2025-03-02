# -*- coding: utf-8 -*-
"""Safna_Nadepilly_Saleem_milestone3.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1r5UvMs-SijBIGaBgzNsLg0l8sht5akcT

## Deep Learning Applications : Milestone 4
# Vehicle Insurance Fraud Classification Using Deep Learning
> Name : Safna Nadepilly Saleem

> Student ID : NSS22605404

> Database : https://www.kaggle.com/datasets/gauravduttakiit/vehicle-insurance-fraud-classification

> Google Drive : https://drive.google.com/drive/folders/1e8kTS9H6sdRwGeMvO1A3V1vDIxgwpAZo?usp=sharing

> Google Colab : https://colab.research.google.com/drive/1r5UvMs-SijBIGaBgzNsLg0l8sht5akcT?usp=sharing

youtube video:https://youtu.be/WBfKiiuDRBg?si=jRTwtTdfjyErjLqz
"""

!pip install efficientnet_pytorch

"""Important Libraries"""

from google.colab import drive
drive.mount('/content/drive')

import os
import torch
import torchvision.transforms as transforms
from torch.utils.data import DataLoader, random_split
from efficientnet_pytorch import EfficientNet
from torchvision.datasets import ImageFolder
from torch.optim import Adam
from torch.nn import CrossEntropyLoss
import logging
from PIL import Image
from torch.cuda.amp import autocast, GradScaler
from torch.optim.lr_scheduler import ReduceLROnPlateau

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define constants
DATA_DIR = '/content/drive/MyDrive/data/new_train'
TEST_DATA_DIR = '/content/drive/MyDrive/data/test'
TRAIN_VAL_SPLIT_RATIO = 0.8
BATCH_SIZE = 32
NUM_EPOCHS = 10
LEARNING_RATE = 0.001
IMAGE_SIZE = (224, 224)
MEAN = [0.485, 0.456, 0.406]
STD = [0.229, 0.224, 0.225]

class ImageClassifier:
    def __init__(self, num_classes):
        self.model = EfficientNet.from_pretrained('efficientnet-b0', num_classes=num_classes)
        self.model.classes = None

    def train(self, train_loader, val_loader, criterion, optimizer, scheduler, device, scaler):
        best_val_accuracy = 0.0
        early_stopping_counter = 0
        for epoch in range(NUM_EPOCHS):
            train_loss, train_accuracy = self._train_epoch(train_loader, criterion, optimizer, device, scaler)
            val_accuracy = self.evaluate(val_loader, device)

            logger.info(f'Epoch {epoch+1}/{NUM_EPOCHS}, Train Loss: {train_loss:.4f}, Train Accuracy: {train_accuracy:.2f}%, Val Accuracy: {val_accuracy:.2f}%')
            print(f'Epoch {epoch+1}/{NUM_EPOCHS}, Train Loss: {train_loss:.4f}, Train Accuracy: {train_accuracy:.2f}%, Val Accuracy: {val_accuracy:.2f}%')

            # Check if validation accuracy has improved, if not increment early stopping counter
            if val_accuracy > best_val_accuracy:
                best_val_accuracy = val_accuracy
                early_stopping_counter = 0
                # Save the model checkpoint
                torch.save(self.model.state_dict(), '/content/drive/MyDrive/data/Model/best_model.pth')
            else:
                early_stopping_counter += 1

            # Check if early stopping criteria is met
            if early_stopping_counter >= 3:  # You can adjust this threshold
                logger.info("Early stopping activated.")
                break

            # Step the scheduler
            scheduler.step(val_accuracy)

    def _train_epoch(self, train_loader, criterion, optimizer, device, scaler):
        self.model.train()
        running_loss = 0.0
        correct = 0
        total = 0

        for inputs, labels in train_loader:
            inputs, labels = inputs.to(device), labels.to(device)

            optimizer.zero_grad()

            # Use mixed precision training
            with autocast():
                outputs = self.model(inputs)
                loss = criterion(outputs, labels)

            # Scale the loss and call backward() to create scaled gradients
            scaler.scale(loss).backward()

            # Unscale the gradients of optimizer's assigned params in-place
            scaler.unscale_(optimizer)

            # Since the gradients of optimizer's assigned params are unscaled,
            # clips as usual:
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)

            # optimizer's gradients are already unscaled, so scaler.step does not unscale them,
            # although this is not necessary unless perform_backward is called again before optimizer.step()
            scaler.step(optimizer)

            # Updates the scale for next iteration
            scaler.update()

            running_loss += loss.item()
            _, predicted = outputs.max(1)
            total += labels.size(0)
            correct += predicted.eq(labels).sum().item()

        epoch_loss = running_loss / len(train_loader)
        epoch_accuracy = 100. * correct / total

        return epoch_loss, epoch_accuracy

    def evaluate(self, data_loader, device):
        self.model.eval()
        correct = 0
        total = 0

        with torch.no_grad():
            for inputs, labels in data_loader:
                inputs, labels = inputs.to(device), labels.to(device)
                outputs = self.model(inputs)
                _, predicted = torch.max(outputs.data, 1)
                total += labels.size(0)
                correct += (predicted == labels).sum().item()

        accuracy = 100 * correct / total

        return accuracy

    def predict_image_class(self, image_path, data_transforms, device):
        image = Image.open(image_path)
        preprocess = transforms.Compose([
            transforms.Resize(IMAGE_SIZE),
            transforms.ToTensor(),
            transforms.Normalize(mean=MEAN, std=STD)
        ])
        input_tensor = preprocess(image)
        input_batch = input_tensor.unsqueeze(0)
        input_batch = input_batch.to(device)

        with torch.no_grad():
            output = self.model(input_batch)

        _, predicted = torch.max(output, 1)
        predicted_class_index = predicted.item()

        class_names = self.model.classes
        predicted_class_label = class_names[predicted_class_index]

        return predicted_class_label, image

def prepare_data_loaders(data_dir, batch_size, train_val_split_ratio, image_size, mean, std):
    # Define data transforms
    data_transforms = transforms.Compose([
        transforms.Resize(image_size),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        transforms.Normalize(mean=mean, std=std)
    ])

    # Load dataset
    dataset = ImageFolder(root=data_dir, transform=data_transforms)

    # Split the dataset into training and validation sets
    train_size = int(train_val_split_ratio * len(dataset))
    val_size = len(dataset) - train_size
    train_dataset, val_dataset = random_split(dataset, [train_size, val_size])

    # Create data loaders
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)

    return train_loader, val_loader, dataset.classes

def main():
    # Prepare data loaders
    train_loader, val_loader, classes = prepare_data_loaders(DATA_DIR, BATCH_SIZE, TRAIN_VAL_SPLIT_RATIO, IMAGE_SIZE, MEAN, STD)

    # Initialize image classifier
    num_classes = len(classes)
    classifier = ImageClassifier(num_classes)
    classifier.model.classes = classes

    # Define loss function and optimizer
    criterion = CrossEntropyLoss()
    optimizer = Adam(classifier.model.parameters(), lr=LEARNING_RATE)

    # Define learning rate scheduler
    scheduler = ReduceLROnPlateau(optimizer, mode='max', patience=2, verbose=True)

    # Initialize GradScaler for mixed precision training
    scaler = GradScaler()

    # Move model to appropriate device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    classifier.model.to(device)

    # Train the model
    classifier.train(train_loader, val_loader, criterion, optimizer, scheduler, device, scaler)

    # Load the best model
    classifier.model.load_state_dict(torch.load('/content/drive/MyDrive/data/Model/best_model.pth'))

    # Define data transforms for the test dataset
    data_transforms = transforms.Compose([
        transforms.Resize(IMAGE_SIZE),
        transforms.ToTensor(),
        transforms.Normalize(mean=MEAN, std=STD)
    ])

    # Evaluate on the test dataset
    test_loader = DataLoader(ImageFolder(root=TEST_DATA_DIR, transform=data_transforms), batch_size=BATCH_SIZE, shuffle=False)
    test_accuracy = classifier.evaluate(test_loader, device)
    logger.info(f"Test Accuracy: {test_accuracy:.2f}%")
    print(f"Test Accuracy: {test_accuracy:.2f}%")

    # Perform image prediction
    image_path = '/content/drive/MyDrive/data/checking/1028.jpg'
    predicted_class_label, image = classifier.predict_image_class(image_path, data_transforms, device)
    logger.info(f"Predicted class for the image: {predicted_class_label}")
    print(f"Predicted class for the image: {predicted_class_label}")
    image.show()

main()

