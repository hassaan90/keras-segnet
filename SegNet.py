from typing import Tuple, List, Text, Dict, Any, Iterator

import numpy as np

from keras.engine.training import Model as tModel
from keras.applications.vgg16 import VGG16
from keras.layers import Input, Flatten
from keras.layers.core import Lambda
from keras.engine.topology import Layer
from keras.layers.pooling import MaxPooling2D
from keras.models import Model
from keras.layers.convolutional import Conv2D, UpSampling2D, ZeroPadding2D
from keras.layers.normalization import BatchNormalization
from keras.layers import Activation
from keras.utils import plot_model
from keras.backend import argmax, gradients, sum, repeat_elements
from keras import regularizers

class DePool2D(UpSampling2D):
    '''
    https://github.com/nanopony/keras-convautoencoder/blob/c8172766f968c8afc81382b5e24fd4b57d8ebe71/autoencoder_layers.py#L24
    Simplar to UpSample, yet traverse only maxpooled elements.
    '''

    def __init__(self, pool2d_layer: MaxPooling2D, *args, **kwargs):
        self._pool2d_layer = pool2d_layer
        super().__init__(*args, **kwargs)

    def get_output(self, train: bool=False) -> Any :
        X = self.get_input(train)
        if self.dim_ordering == 'th':
            output = repeat_elements(X, self.size[0], axis=2)
            output = repeat_elements(output, self.size[1], axis=3)
        elif self.dim_ordering == 'tf':
            output = repeat_elements(X, self.size[0], axis=1)
            output = repeat_elements(output, self.size[1], axis=2)
        else:
            raise Exception('Invalid dim_ordering: ' + self.dim_ordering)

        return gradients(
            sum(
                self._pool2d_layer.get_output(train)
            ),
            self._pool2d_layer.get_input(train)
        ) * output


def create_segnet(shape: Tuple[int,int,int], nb_class: int, indices: bool) -> tModel :
    # base on https://github.com/alexgkendall/SegNet-Tutorial/blob/master/Models/segnet_train.prototxt
    # and https://github.com/alexgkendall/SegNet-Tutorial/blob/master/Example_Models/segnet_model_driving_webdemo.prototxt

    # input_shape: (include_top is False のときのみ) 
    # ex. (3, 224, 244) or (224, 224, 3)
    # 正確に3つの入力チャンネルを持つ必要があり、幅と高さは48以上でなければなりません。
    input_tensor = Input(shape=shape) # type: object
    encoder = VGG16(
        include_top=False, 
        weights='imagenet', 
        input_tensor=input_tensor,
        input_shape=shape,
        pooling="None" ) # type: tModel
    #encoder.summary()

    L = [layer for i, layer in enumerate(encoder.layers) ] # type: List[Layer]
    #for layer in L: layer.trainable = False # freeze VGG16
    L.reverse()

    x = encoder.output

    # Block 5
    if indices: x = DePool2D(L[0], size=L[0].pool_size, input_shape=encoder.output_shape[1:])(x)
    else:       x = UpSampling2D(  size=L[0].pool_size, input_shape=encoder.output_shape[1:])(x)
    x = Activation('relu')(BatchNormalization()(Conv2D(L[1].filters, L[1].kernel_size, padding=L[1].padding, kernel_initializer="he_normal", bias_initializer='zeros', kernel_regularizer=regularizers.l2(0.001))(x)))
    x = Activation('relu')(BatchNormalization()(Conv2D(L[2].filters, L[2].kernel_size, padding=L[2].padding, kernel_initializer="he_normal", bias_initializer='zeros', kernel_regularizer=regularizers.l2(0.001))(x)))
    x = Activation('relu')(BatchNormalization()(Conv2D(L[3].filters, L[3].kernel_size, padding=L[3].padding, kernel_initializer="he_normal", bias_initializer='zeros', kernel_regularizer=regularizers.l2(0.001))(x)))
    # Block 4
    if indices: x = DePool2D(L[4], size=L[4].pool_size)(x)
    else:       x = UpSampling2D(  size=L[4].pool_size)(x)
    x = Activation('relu')(BatchNormalization()(Conv2D(L[5].filters, L[5].kernel_size, padding=L[5].padding, kernel_initializer="he_normal", bias_initializer='zeros', kernel_regularizer=regularizers.l2(0.001))(x)))
    x = Activation('relu')(BatchNormalization()(Conv2D(L[6].filters, L[6].kernel_size, padding=L[6].padding, kernel_initializer="he_normal", bias_initializer='zeros', kernel_regularizer=regularizers.l2(0.001))(x)))
    x = Activation('relu')(BatchNormalization()(Conv2D(L[7].filters, L[7].kernel_size, padding=L[7].padding, kernel_initializer="he_normal", bias_initializer='zeros', kernel_regularizer=regularizers.l2(0.001))(x)))
    # Block 3
    if indices: x = DePool2D(L[8], size=L[8].pool_size)(x)
    else:       x = UpSampling2D(  size=L[8].pool_size)(x)
    x = ZeroPadding2D(padding=(0, 1))(x)
    x = Activation('relu')(BatchNormalization()(Conv2D(L[10].filters, L[10].kernel_size, padding=L[10].padding, kernel_initializer="he_normal", bias_initializer='zeros', kernel_regularizer=regularizers.l2(0.001))(x)))
    x = Activation('relu')(BatchNormalization()(Conv2D(L[11].filters, L[11].kernel_size, padding=L[11].padding, kernel_initializer="he_normal", bias_initializer='zeros', kernel_regularizer=regularizers.l2(0.001))(x)))
    # Block 2
    if indices: x = DePool2D(L[12], size=L[12].pool_size)(x)
    else:       x = UpSampling2D(   size=L[12].pool_size)(x)
    x = Activation('relu')(BatchNormalization()(Conv2D(L[13].filters, L[13].kernel_size, padding=L[13].padding, kernel_initializer="he_normal", bias_initializer='zeros', kernel_regularizer=regularizers.l2(0.001))(x)))
    x = Activation('relu')(BatchNormalization()(Conv2D(L[14].filters, L[14].kernel_size, padding=L[14].padding, kernel_initializer="he_normal", bias_initializer='zeros', kernel_regularizer=regularizers.l2(0.001))(x)))
    # Block 1
    if indices: x = DePool2D(L[15], size=L[15].pool_size)(x)
    else:       x = UpSampling2D(   size=L[15].pool_size)(x)
    x = Activation('relu')(BatchNormalization()(Conv2D(L[16].filters, L[16].kernel_size, padding=L[16].padding, kernel_initializer="he_normal", bias_initializer='zeros', kernel_regularizer=regularizers.l2(0.001))(x)))
    x = Activation('relu')(BatchNormalization()(Conv2D(L[17].filters, L[17].kernel_size, padding=L[17].padding, kernel_initializer="he_normal", bias_initializer='zeros', kernel_regularizer=regularizers.l2(0.001))(x)))

    x = Conv2D(nb_class, (1, 1), padding='valid', kernel_initializer="he_normal", bias_initializer='zeros', kernel_regularizer=regularizers.l2(0.001))(x)

    x = Activation('softmax')(x)
    
    predictions = x

    segnet = Model(inputs=encoder.inputs, outputs=predictions) # type: tModel

    return segnet


if __name__ == '__main__':
    segnet = create_segnet((480, 360, 3), 12, indices=False)
    segnet.summary()
    plot_model(segnet, to_file='segnet.png', show_shapes=True, show_layer_names=True)
    with open('segnet_model.json', 'w') as f: f.write(segnet.to_json())
    exit()
