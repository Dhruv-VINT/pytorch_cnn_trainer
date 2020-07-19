"""
CNN Training Script. 
Improvement from Imagenet script is taken from ross wightman
One of the orignal script is here
https://github.com/rwightman/pytorch-image-models/blob/master/train.py
https://github.com/pytorch/examples/tree/master/imagenet
This is just simplified version of both of them, trying to provide flexibility and modularity.

Some Improvement I am trying to make
1. Support mixed precision training with PyTorch 1.6 (soon).
2. Early Stopping. (Done)
3. Add torchvision support. (Done)
4. fit() function (Done)
5. Keras like history object. (TODO)
"""

import torch
from pytorch_cnn_trainer import utils
from tqdm import tqdm
import time

# import model
from collections import OrderedDict

__all__ = ["train_step", "val_step", "fit"]


def train_step(
    model,
    train_loader,
    criterion,
    device,
    optimizer,
    scheduler=None,
    num_batches: int = None,
    log_interval: int = 100,
):
    """
    Performs one step of training. Calculates loss, forward pass, computes gradient and returns metrics.
    Args:
        model : A pytorch CNN Model.
        train_loader : Train loader.
        criterion : Loss function to be optimized.
        device : "cuda" or "cpu"
        optimizer : Torch optimizer to train.
        scheduler : Learning rate scheduler.
        num_batches : (optional) Integer To limit training to certain number of batches.
        log_interval : (optional) Defualt 100. Integer to Log after specified batches.
    """

    start_train_step = time.time()

    model.train()
    last_idx = len(train_loader) - 1
    batch_time_m = utils.AverageMeter()
    # data_time_m = utils.AverageMeter()
    losses_m = utils.AverageMeter()
    top1_m = utils.AverageMeter()
    top5_m = utils.AverageMeter()
    cnt = 0
    batch_start = time.time()
    # num_updates = epoch * len(loader)

    for batch_idx, (inputs, target) in enumerate(train_loader):
        last_batch = batch_idx == last_idx
        # data_time_m.update(time.time() - batch_start)
        inputs = inputs.to(device)
        target = target.to(device)

        # zero the parameter gradients
        optimizer.zero_grad()
        output = model(inputs)

        loss = criterion(output, target)
        cnt += 1
        acc1, acc5 = utils.accuracy(output, target, topk=(1, 5))

        top1_m.update(acc1.item(), output.size(0))
        top5_m.update(acc5.item(), output.size(0))
        losses_m.update(loss.item(), inputs.size(0))

        loss.backward()
        optimizer.step()

        if scheduler is not None:
            scheduler.step()

        batch_time_m.update(time.time() - batch_start)
        if last_batch or batch_idx % log_interval == 0:  # If we reach the log intervel
            print(
                "Batch Train Time: {batch_time.val:.3f} ({batch_time.avg:.3f})  "
                "Loss: {loss.val:>7.4f} ({loss.avg:>6.4f})  "
                "Top 1 Accuracy: {top1.val:>7.4f} ({top1.avg:>7.4f})  "
                "Top 5 Accuracy: {top5.val:>7.4f} ({top5.avg:>7.4f})".format(
                    batch_time=batch_time_m, loss=losses_m, top1=top1_m, top5=top5_m
                )
            )

        if num_batches is not None:
            if cnt >= num_batches:
                end_train_step = time.time()
                metrics = OrderedDict(
                    [("loss", losses_m.avg), ("top1", top1_m.avg), ("top5", top5_m.avg)]
                )
                print("Done till {} train batches".format(num_batches))
                print(
                    "Time taken for train step = {} sec".format(
                        end_train_step - start_train_step
                    )
                )
                return metrics

    metrics = OrderedDict(
        [("loss", losses_m.avg), ("top1", top1_m.avg), ("top5", top5_m.avg)]
    )
    end_train_step = time.time()
    print(
        "Time taken for train step = {} sec".format(end_train_step - start_train_step)
    )
    return metrics


def val_step(model, val_loader, criterion, device, num_batches=None, log_interval=100):
    """
    Performs one step of validation. Calculates loss, forward pass and returns metrics.
    Args:
        model : A pytorch CNN Model.
        val_loader : Validation loader.
        criterion : Loss function to be optimized.
        device : "cuda" or "cpu"
        num_batches : (optional) Integer To limit validation to certain number of batches.
        log_interval : (optional) Defualt 100. Integer to Log after specified batches.
    """
    start_test_step = time.time()
    last_idx = len(val_loader) - 1
    batch_time_m = utils.AverageMeter()
    # data_time_m = utils.AverageMeter()
    losses_m = utils.AverageMeter()
    top1_m = utils.AverageMeter()
    top5_m = utils.AverageMeter()
    cnt = 0
    model.eval()
    batch_start = time.time()
    with torch.no_grad():
        for batch_idx, (inputs, target) in enumerate(val_loader):
            last_batch = batch_idx == last_idx
            inputs = inputs.to(device)
            target = target.to(device)

            output = model(inputs)
            if isinstance(output, (tuple, list)):
                output = output[0]

            loss = criterion(output, target)
            cnt += 1
            acc1, acc5 = utils.accuracy(output, target, topk=(1, 5))
            reduced_loss = loss.data

            losses_m.update(reduced_loss.item(), inputs.size(0))
            top1_m.update(acc1.item(), output.size(0))
            top5_m.update(acc5.item(), output.size(0))
            batch_time_m.update(time.time() - batch_start)

            batch_start = time.time()

            if (
                last_batch or batch_idx % log_interval == 0
            ):  # If we reach the log intervel
                print(
                    "Batch Inference Time: {batch_time.val:.3f} ({batch_time.avg:.3f})  "
                    "Loss: {loss.val:>7.4f} ({loss.avg:>6.4f})  "
                    "Top 1 Accuracy: {top1.val:>7.4f} ({top1.avg:>7.4f})  "
                    "Top 5 Accuracy: {top5.val:>7.4f} ({top5.avg:>7.4f})".format(
                        batch_time=batch_time_m, loss=losses_m, top1=top1_m, top5=top5_m
                    )
                )

            if num_batches is not None:
                if cnt >= num_batches:
                    end_test_step = time.time()
                    metrics = OrderedDict(
                        [
                            ("loss", losses_m.avg),
                            ("top1", top1_m.avg),
                            ("top5", top5_m.avg),
                        ]
                    )
                    print("Done till {} validation batches".format(num_batches))
                    print(
                        "Time taken for validation step = {} sec".format(
                            end_test_step - start_test_step
                        )
                    )
                    return metrics

        metrics = OrderedDict(
            [("loss", losses_m.avg), ("top1", top1_m.avg), ("top5", top5_m.avg)]
        )
        print("Finished the validation epoch")

    end_test_step = time.time()
    print(
        "Time taken for validation step = {} sec".format(
            end_test_step - start_test_step
        )
    )
    return metrics


def fit(
    epochs,
    model,
    train_loader,
    valid_loader,
    criterion,
    device,
    optimizer,
    scheduler=None,
    early_stopper=None,
    num_batches=None,
    log_interval=100,
):
    """
    A fit function that performs training for certain number of epochs.
    Args:
        epochs: Number of epochs to train.
        model : A pytorch CNN Model.
        train_loader : Train loader.
        val_loader : Validation loader.
        criterion : Loss function to be optimized.
        device : "cuda" or "cpu"
        optimizer : PyTorch optimizer.
        scheduler : (optional) Learning Rate scheduler.
        early_stopper: (optional) A utils provied early stopper, based on validation loss.
        num_batches : (optional) Integer To limit validation to certain number of batches.
        log_interval : (optional) Defualt 100. Integer to Log after specified batches.
    """
    for epoch in tqdm(range(epochs)):
        print()
        print("Training Epoch = {}".format(epoch))
        train_metrics = train_step(
            model,
            train_loader,
            criterion,
            device,
            optimizer,
            scheduler,
            num_batches,
            log_interval,
        )
        print()
        print("Validating Epoch = {}".format(epoch))
        valid_metrics = val_step(
            model, valid_loader, criterion, device, num_batches, log_interval
        )

        validation_loss = valid_metrics["loss"]
        if early_stopper is not None:
            early_stopper(validation_loss, model=model)

        if early_stopper.early_stop:
            print("Saving Model and Early Stopping")
            print("Early Stopping. Ran out of Patience for validation loss")
            break

        print("Done Training, Model Saved to Disk")

    return True  # For now, we should probably return an history object like keras.