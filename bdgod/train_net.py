#!/usr/bin/evn python
# -*- coding: utf-8 -*-
import numpy as np
import torch
import torch.nn as nn
from torch.autograd import Variable
from torch import optim
from collections import OrderedDict
from resnet import resnet50, Bottleneck, resnet101
from dog_config import *
from data_augmentation import data_augmentation_img
from vggnet import vgg16
from load_image import load_data
import math


def train(model, loss, optimizer, x_val, y_val):
    x = Variable(x_val.cuda(), requires_grad=False)
    y = Variable(y_val.cuda(), requires_grad=False)
    optimizer.zero_grad()
    fx = model.forward(x)
    output = loss.forward(fx, y)
    output.backward()
    optimizer.step()
    return output.cuda().data[0]


def predict(model, x_val):
    x = Variable(x_val.cuda(), requires_grad=False)
    output = model.forward(x)
    return output.cpu().data.numpy().argmax(axis=1)


def main():
    torch.manual_seed(42)
    print 'loading....'
    trX = np.load('bddog/trX.npy')
    trY = np.load('bddog/trY.npy')
    print 'load train data'
    # trX = torch.from_numpy(trX).float()
    # trY = torch.from_numpy(trY).long()
    teX = np.load('bddog/teX.npy').astype(np.float)
    teY = np.load('bddog/teY.npy')
    print 'load test data'
    teX[:, 0, ...] -= MEAN_VALUE[0]
    teX[:, 1, ...] -= MEAN_VALUE[1]
    teX[:, 2, ...] -= MEAN_VALUE[2]
    teX = torch.from_numpy(teX).float()
    # teY = torch.from_numpy(teY).long()
    print 'numpy data to tensor'
    n_examples = len(trX)
    # n_classes = 100
    # model = torch.load('models/resnet_model_pretrained_adam_2_2_SGD_1.pkl')
    model = resnet101(pretrained=True, model_root=Model_Root)
    print '==============================='
    print model
    # for param in model.parameters():
    #     param.requires_grad = False
    # model.classifier[-1] = nn.Linear(4096, 100)
    # n = model.classifier[-1].weight.size(1)
    # model.classifier[-1].weight.data.normal_(0, 0.01)
    # model.classifier[-1].bias.data.zero_()

    # VGG16 classifier层
    # model.classifier = nn.Sequential(
    #     nn.Linear(512 * 7 * 7, 4096),
    #     nn.ReLU(inplace=True),
    #     nn.Dropout(),
    #     nn.Linear(4096, 4096),
    #     nn.ReLU(inplace=True),
    #     nn.Dropout(),
    #     nn.Linear(4096, 100),
    # )
    # count = 0
    # print '==============================='
    # for module in model.modules():
    #     print '**** %d' % count
    #     print(module)
    #     count+=1
    # print '==============================='
    # count= 0
    # model.classifier[6] = nn.Linear(4096, 100)
    # for m in model.classifier:
    #     if count == 6:
    #         m = nn.Linear(4096, 100)
    #         if isinstance(m, nn.Conv2d):
    #             n = m.kernel_size[0] * m.kernel_size[1] * m.out_channels
    #             m.weight.data.normal_(0, math.sqrt(2. / n))
    #             if m.bias is not None:
    #                 m.bias.data.zero_()
    #         elif isinstance(m, nn.BatchNorm2d):
    #             m.weight.data.fill_(1)
    #             m.bias.data.zero_()
    #         elif isinstance(m, nn.Linear):
    #             n = m.weight.size(1)
    #             m.weight.data.normal_(0, 0.01)
    #             m.bias.data.zero_()
    #     count+=1
    # try:
    #     print model.classifier[0]
    # except Exception as e:
    #     print e

    # print '==============================='
    # for module in model.modules()[-7:]:
    #     print '****'
    #     print(module)
    # resnet50 FC层
    model.group2 = nn.Sequential(
        OrderedDict([
            ('fc', nn.Linear(2048, 100))
        ])
    )
    # ignored_params = list(map(id, model.group2.parameters()))
    # base_params = filter(lambda p: id(p) not in ignored_params,
    #                      model.parameters())
    # print '==============================='
    # print model
    model = model.cuda()
    loss = torch.nn.CrossEntropyLoss(size_average=True)
    loss = loss.cuda()
    # 对局部优化
    # optimizer = optim.SGD(model.group2.parameters(), lr=(1e-03), momentum=0.9,weight_decay=0.001)
    # optimizer = optim.Adam([{'params':model.layer4[2].parameters()},
    #                         {'params':model.group2.parameters()}
    #                         ],lr=(1e-04),eps=1e-08, betas=(0.9, 0.999), weight_decay=0.0005)
    optimizer = optim.Adam([{'params':model.layer4[2].parameters()},
                            {'params':model.group2.parameters()}
                            ],lr=(1e-05))

    # 全局优化
    # optimizer = optim.Adam(model.parameters(),lr=(1e-04),eps=1e-08,betas=(0.9, 0.999),weight_decay =0.0005)
    batch_size = 64
    data_aug_num = 4
    mini_batch_size = batch_size/data_aug_num
    epochs = 1000
    for e in range(epochs):
        cost = 0.0

        num_batches_train = n_examples / mini_batch_size
        print num_batches_train
        for k in range(num_batches_train):
            print k
            start, end = k * mini_batch_size, (k + 1) * mini_batch_size
            batch_trX = trX[start:end]
            batch_trY = trY[start:end]
            batch_train_data_X = np.ones((0,3,224,224))
            batch_train_data_Y = np.ones((0))
            for index in range(mini_batch_size):
                batch_train_data_X = np.concatenate((batch_train_data_X,data_augmentation_img(batch_trX[index])),axis=0)
                temp_y = np.ones((data_aug_num*2))
                temp_y[:] = batch_trY[index]
                batch_train_data_Y = np.concatenate((batch_train_data_Y,temp_y),axis=0)
            print batch_train_data_X.shape
            print batch_train_data_Y.shape
            np.random.seed(23)
            nx = range(len(batch_train_data_X))
            np.random.shuffle(nx)
            batch_train_data_X = batch_train_data_X[nx]
            batch_train_data_Y = batch_train_data_Y[nx]
            batch_train_data_X = batch_train_data_X[:batch_size]
            batch_train_data_Y = batch_train_data_Y[:batch_size]
            batch_train_data_X[:, 0, ...] -= MEAN_VALUE[0]
            batch_train_data_X[:, 1, ...] -= MEAN_VALUE[1]
            batch_train_data_X[:, 2, ...] -= MEAN_VALUE[2]
            torch_batch_train_data_X = torch.from_numpy(batch_train_data_X).float()
            torch_batch_train_data_Y = torch.from_numpy(batch_train_data_Y).long()
            cost_temp = train(model, loss, optimizer, torch_batch_train_data_X, torch_batch_train_data_Y)
            cost +=cost_temp
            if (k+1) % 10 ==0:
                print 'now step train loss is : %f' % (cost_temp)
            if (k+1) % 20 ==0:
                print 'all average train loss is : %f' % (cost / (k+1))
            if (k+1) %100 == 0:
                acc = 0.0
                num_batches_test = len(teX) / batch_size
                for j in range(num_batches_test):
                    start, end = j * batch_size, (j + 1) * batch_size
                    predY = predict(model,teX[start:end])
                    # print predY.dtype
                    # print teY[start:end]
                    acc+=1.*np.mean(predY==teY[start:end])
                    # print ('Epoch %d ,Step %d, acc = %.2f%%'%(e,k,100.*np.mean(predY==teY[start:end])))

                print 'Epoch %d ,Step %d, all test acc is : %f' % (e,k,acc / num_batches_test)
                torch.save(model, 'models/resnet_model_pretrained_%s_%s_%s_7.pkl' % ('adam', str(e), str(k)))
    print 'train over'


if __name__ == '__main__':
    main()