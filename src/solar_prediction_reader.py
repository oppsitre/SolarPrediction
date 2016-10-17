
from __future__ import division
import numpy as np
import pickle

hour_in_a_day = 24

class Reader:

    def _data_reshape(self, input, groups, start, length):
        data = []
        for group_head in groups:
            data.append(input[group_head][start:start+length])
        data = zip(*data)
        return np.array(data)

    def _target_pattern(self, target_raw_data):
        n_target = len(target_raw_data[0])
        pattern = []
        for i in range(hour_in_a_day):
            pattern.append([0]*n_target)
        num = [0]*hour_in_a_day
        for i in range(len(target_raw_data)):
            for j in range(len(target_raw_data[i])):
                pattern[i%hour_in_a_day][j] += target_raw_data[i][j]
            num[i%hour_in_a_day] += 1
        for i in range(hour_in_a_day):
            for j in range(n_target):
                pattern[i][j] /= num[i]

        return pattern

    def __init__(self, data_path, config):
        #load data
        pickle_input_data = open(data_path,'rb')
        input_data_pd = pickle.load(pickle_input_data)

        input_data_pd['Avg Airmass'] = input_data_pd['Avg Airmass'].replace(-1.0, 0.0)
        input_data_pd['Avg Total Cloud Cover [%]'] = input_data_pd['Avg Total Cloud Cover [%]'].replace(-1.0, 0.0)
        input_data_pd['Avg Opaque Cloud Cover [%]'] = input_data_pd['Avg Opaque Cloud Cover [%]'].replace(-1.0, 0.0)

        #feature scale
        
        #load config
        self.n_step = config.n_step
        self.n_model = config.n_model
        self.data_step = config.data_step
        data_length = config.data_length
        train_prop = config.train_prop
        self.batch_size = config.batch_size

        #data preprocess
        input_group_solar = config.input_group_solar
        input_group_temp = config.input_group_temp
        target_group = config.target_group

        # target_raw_data = input_data_pd['Avg Global CMP22 (vent/cor) [W/m^2]']
        # pattern = self._target_patten(target_raw_data)
        # target_raw_data = [target_raw_data[i] - pattern[i%24] for i in range(len(target_raw_data))]
        # target_raw_data = target_raw_data[self.n_step+n_predict-1:self.n_step+n_predict-1+data_length]
        # target_raw_data = zip(*[target_raw_data])
        # print pattern, len(pattern)
        #target_raw_data = self._data_reshape(input_data_pd, target_group, self.n_step+n_predict-1, data_length)
        

        #select the data and reshape the data
        target_raw_data = self._data_reshape(input_data_pd, target_group, 0, len(input_data_pd))
        #get the target pattern
        self.pattern = self._target_pattern(target_raw_data)

        #feature scale
        input_data_pd = (input_data_pd - input_data_pd.mean()) / input_data_pd.std()
        solar_raw_data = self._data_reshape(input_data_pd, input_group_solar, 0, data_length)
        temp_raw_data = self._data_reshape(input_data_pd, input_group_temp, 0, data_length)

        self.solar_data = []
        self.temp_data = []
        self.target_data = []   
        #minus the pattern from the raw data
        n_target = len(target_raw_data[0])
        for i in range(len(target_raw_data)):
            tmp = []
            for j in range(n_target):
                tmp.append(target_raw_data[i][j] - self.pattern[i%hour_in_a_day][j])
            self.target_data.append(tmp)
        
        #get the solar and temp data by organizing the raw data with the time step
        ptr = 0
        while ptr + self.n_step <= data_length:
            self.solar_data.append(solar_raw_data[ptr:ptr+self.n_step])
            self.temp_data.append(temp_raw_data[ptr:ptr+self.n_step])
            ptr += self.data_step

        self.batch_index = 0
        self.train_batch_num = int(train_prop * len(self.solar_data)) // self.batch_size
        print train_prop, len(self.solar_data), self.batch_size, self.train_batch_num
        
        self.test_input_start = self.train_batch_num * self.batch_size
        self.test_target_start = self.test_input_start*self.data_step + self.n_step

    def get_pattern(self):
        return self.pattern

    def next_batch(self):
        """return a batch of train and target data"""
        start = self.batch_index * self.batch_size
        end = (self.batch_index + 1) * self.batch_size 
        solar_data_batch = np.array(self.solar_data[start : end])
        temp_data_batch = np.array(self.temp_data[start : end])

        target_data_batch = []
        for i in range(self.n_model):
            ptr = start*self.data_step + self.n_step + i + 10
            tmp = []
            for j in range(self.batch_size):
                tmp.append(self.target_data[ptr])
                ptr += self.data_step
            target_data_batch.append(np.array(tmp))
        
        self.batch_index = (self.batch_index + 1)%self.train_batch_num

        return [solar_data_batch, temp_data_batch, target_data_batch]

    def get_test_set(self, test_num):
        test_targets = []
        for i in range(test_num):  
            for j in range(self.n_model):
                test_targets.append(self.target_data[self.test_target_start+i*self.data_step+j+10 : 
                                                    self.test_target_start+i*self.data_step+j+11])
        return [self.solar_data[self.test_input_start:self.test_input_start+test_num], 
                self.temp_data[self.test_input_start:self.test_input_start+test_num], 
                test_targets]