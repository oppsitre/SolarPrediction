# -*- coding: utf-8 -*-
__author__= 'WANG Kejie<wang_kejie@foxmail.com>'
__date__ = '21/11/2016'

import tensorflow as tf
import numpy as np
import json
from collections import namedtuple
from model import Model
from util import MSE_And_MAE
import solar_prediction_reader

def main(_):
    #get the config
    fp = open('../config.json')
    config = json.load(fp, object_hook=lambda d:namedtuple('X', d.keys())(*d.values()))
    fp.close()

    n_step = config.n_step
    n_target = config.n_target
    n_input_solar = len(config.input_group_solar)
    n_input_temp = len(config.input_group_temp)
    
    epoch_size = config.epoch_size
    print_step = config.print_step

    test_num = config.test_num

    #define the input and output
    x_solar = tf.placeholder(tf.float32, [None, n_step, n_input_solar])
    x_temp = tf.placeholder(tf.float32, [None, n_step, n_input_temp])
    y_ = tf.placeholder(tf.float32, [None, n_target])
    keep_prob = tf.placeholder(tf.float32)

    reader = solar_prediction_reader.Reader(config)
    
    model = Model([x_solar, x_temp], y_, keep_prob, config)

    prediction = model.prediction
    loss = model.loss
    optimize = model.optimize

    #new a saver to save the model
    saver = tf.train.Saver()

    validation_last_loss = float('inf')

    with tf.Session() as sess:
        tf.initialize_all_variables().run()
    
        for i in range(epoch_size+1):         
            # test
            if i%config.test_step == 0:
                solar_test_input, temp_test_input, test_target = reader.get_test_set(test_num)
                test_feed = {x_solar:solar_test_input, x_temp:temp_test_input, keep_prob:1.0}
                test_result = sess.run(prediction, feed_dict=test_feed)

                #calculate the mse and mae
                mse, mae = MSE_And_MAE(test_target, test_result)
                print "Test MSE: ", mse
                print "Test MAE: ", mae

            #train
            batch = reader.next_batch()
            train_feed = {x_solar:batch[0], x_temp:batch[1], y_:batch[2],keep_prob:0.5}
            sess.run(optimize, feed_dict=train_feed)
            print sess.run(loss, feed_dict=train_feed)
            

            #validation
            validation_set = reader.get_validation_set()
            validation_feed = {x_solar:validation_set[0], x_temp:validation_set[1], y_:validation_set[2],keep_prob:0.5}
            validation_loss = sess.run(loss,feed_dict=validation_feed)

            #compare the validation with the last loss
            if(validation_loss < validation_last_loss):
                validation_last_loss = validation_loss
            else:
                break

            # print "validation loss: ", validation_loss

if __name__ == "__main__":
    tf.app.run()