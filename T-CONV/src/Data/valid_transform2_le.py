import datetime
import numpy
from load_dataset import Dataset
import sys
import fuel
import Data as data


class VStream(object):
    def __init__(self, trip_id, call_type, origin_call, origin_stand, taxi_id, \
                 timestamp, day_type, missing_data, latitude, longitude, dest_latitude, dest_longitude, conv_dim=5):
        self.trip_id = trip_id
        self.call_type = call_type
        self.origin_call = origin_call
        self.origin_stand = origin_stand
        self.taxi_id = taxi_id
        self.timestamp = timestamp
        self.day_type = day_type
        self.missing_data = missing_data
        self.latitude = latitude
        self.longitude = longitude
        self.dest_latitude = dest_latitude
        self.dest_longitude = dest_longitude

        self.id = -1
        self.size = len(self.latitude)

        self.max_splits = 10
        self.splits = []
        self.isplit = 0
        self.rng = numpy.random.RandomState(fuel.config.default_seed)
        self.level2_lat = (data.train_gps_std[0]) / (250)
        self.level2_lon = (data.train_gps_std[1]) / (200)
        self.k = 5
        self.conv_dim = 30
        self.epoch = 0

    def get_size(self):
        return self.size

    def normalize(self, traj, islatitude):
        if islatitude == True:
            return (traj - data.train_gps_mean[0]) / data.train_gps_std[0]
        else:
            return (traj - data.train_gps_mean[1]) / data.train_gps_std[1]

    def get_first_snapshot(self, latitudes, longitudes):
        snapshot = numpy.zeros(( self.conv_dim, self.conv_dim,2), dtype=numpy.float32)
        half_dim = self.conv_dim // 2

        dev_latitude = self.level2_lat  # 100m each cell.
        dev_longitude = self.level2_lon

        center_x = latitudes[0]
        center_y = longitudes[0]
        lefttop_x = center_x - half_dim * dev_latitude
        lefttop_y = center_y - half_dim * dev_longitude

        # array_last = numpy.zeros((1,dim, dim),dtype='float32')
        ink = 1.0
        length = len(latitudes)
        # sel = 0
        for i in range(length):
            k = i
            x = int((latitudes[k] - lefttop_x) / dev_latitude)
            y = int((longitudes[k] - lefttop_y) / dev_longitude)
            # print(x,y)
            if (x >= 0 and x < self.conv_dim and y >= 0 and y < self.conv_dim):
                snapshot[x][y][0] = self.normalize(latitudes[k], True)  # ink
                snapshot[x][y][1] = self.normalize(longitudes[k], False)  #
            # ink = ink / 2.0
            # sel += 1
            else:
                break
        # print (sel)
        return snapshot

    def get_last_snapshot(self, latitudes, longitudes):
        snapshot = numpy.zeros((self.conv_dim, self.conv_dim,2), dtype=numpy.float32)
        half_dim = self.conv_dim // 2
        dev_latitude = self.level2_lat  # 100m each cell.
        dev_longitude = self.level2_lon
        center_x = latitudes[-1]
        center_y = longitudes[-1]
        lefttop_x = center_x - half_dim * dev_latitude
        lefttop_y = center_y - half_dim * dev_longitude

        # array_last = numpy.zeros((1,dim, dim),dtype='float32')
        ink = 1.0
        length = len(latitudes)
        # sel = 0
        for i in range(length):
            k = length - 1 - i
            x = int((latitudes[k] - lefttop_x) / dev_latitude)
            y = int((longitudes[k] - lefttop_y) / dev_longitude)
            # print(x,y)
            if (x >= 0 and x < self.conv_dim and y >= 0 and y < self.conv_dim):
                snapshot[x][y][0] = self.normalize(latitudes[k], True)  # ink
                snapshot[x][y][1] = self.normalize(longitudes[k], False)  #
            # ink = ink / 2.0
            # sel += 1
            else:
                break
        # print (sel)
        return snapshot

    def get_sample_data(self):  # get a row of the data, and the sub-traj with randomized length is selected
	'''
        while self.isplit >= len(self.splits):
            if self.id < self.size - 1:
                # print(self.list[0])
                self.id += 1

            else:
                self.id = 0
                print ('finish data epoch %s' % self.epoch)
                self.epoch += 1

            if (len(self.latitude[self.id]) > 10):
                self.splits = range(0,len(self.latitude[self.id]), len(self.latitude[self.id]) // 10)
		#self.splits = range(len(self.latitude[self.id])*9//10, len(self.latitude[self.id]) *9//10+1)
            else:
                continue

            if len(self.splits) > self.max_splits:
                self.splits = self.splits[:self.max_splits]
            self.isplit = 0

        i = self.isplit
        self.isplit += 1
        n = self.splits[i] + 1
	'''
        if self.id < self.size - 1:
            self.id += 1
        else:
            self.id = 0
            # iprint ('finish epoch %s' % self.epoch)
            self.epoch += 1
        if (self.id % 10000 == 0):
            print(self.id)


        # print self.isplit, n
        trip_id_ = self.trip_id[self.id]
        call_type_ = self.call_type[self.id]
        origin_call_ = self.origin_call[self.id]
        origin_stand_ = self.origin_stand[self.id]
        taxi_id_ = self.taxi_id[self.id]
        timestamp_ = self.timestamp[self.id]
        day_type_ = self.day_type[self.id]
        missing_data_ = self.missing_data[self.id]

        date = datetime.datetime.utcfromtimestamp(timestamp_)
        yearweek = date.isocalendar()[1] - 1
        week_of_year_ = numpy.int8(51 if yearweek == 52 else yearweek)
        day_of_week_ = numpy.int8(date.weekday())
        qhour_of_day_ = numpy.int8(date.hour * 4 + date.minute / 15)

        latitudes_ = self.latitude[self.id]
        longitudes_ = self.longitude[self.id]
        first_snapshot_ = self.get_first_snapshot(latitudes_, longitudes_)
        last_snapshot_ = self.get_last_snapshot(latitudes_, longitudes_)
        snapshot_ = numpy.concatenate((first_snapshot_, last_snapshot_), axis=2)
        first_latitude_ = self.normalize(self.latitude[self.id][0], True)
        first_longitude_ = self.normalize(self.longitude[self.id][0], False)
        last_latitude_ = self.normalize(latitudes_[-1], True)
        last_longitude_ = self.normalize(longitudes_[-1], False)

        dest_latitude_ = self.dest_latitude[self.id]
        dest_longitude_ = self.dest_longitude[self.id]

        return trip_id_, call_type_, origin_call_, origin_stand_, taxi_id_, \
               day_type_, missing_data_, week_of_year_, day_of_week_, qhour_of_day_, \
               snapshot_, first_latitude_, first_longitude_, \
               last_latitude_, last_longitude_, dest_latitude_, dest_longitude_

    # return the filtered result
    def get_data_batch_conv(self, batchsize):
        trip_id_ = numpy.empty(shape=(batchsize,), dtype='S19')
        call_type_ = numpy.empty(shape=(batchsize,), dtype=numpy.int8)
        origin_call_ = numpy.empty(shape=(batchsize,), dtype=numpy.int32)
        origin_stand_ = numpy.empty(shape=(batchsize,), dtype=numpy.int8)
        taxi_id_ = numpy.empty(shape=(batchsize,), dtype=numpy.int16)
        timestamp_ = numpy.empty(shape=(batchsize,), dtype=numpy.int32)
        day_type_ = numpy.empty(shape=(batchsize,), dtype=numpy.int8)
        missing_data_ = numpy.empty(shape=(batchsize,), dtype=numpy.bool)

        week_of_year_ = numpy.empty(shape=(batchsize,), dtype=numpy.int16)
        day_of_week_ = numpy.empty(shape=(batchsize,), dtype=numpy.int16)
        qhour_of_day_ = numpy.empty(shape=(batchsize,), dtype=numpy.int16)
        snapshot_ = numpy.empty(shape=(batchsize,  self.conv_dim, self.conv_dim,4), dtype=numpy.float32)

        first_latitude_ = numpy.empty(shape=(batchsize, 1), dtype=numpy.float32)
        first_longitude_ = numpy.empty(shape=(batchsize, 1), dtype=numpy.float32)
        last_latitude_ = numpy.empty(shape=(batchsize, 1), dtype=numpy.float32)
        last_longitude_ = numpy.empty(shape=(batchsize, 1), dtype=numpy.float32)
        dest_latitude_ = numpy.empty(shape=(batchsize, 1), dtype=numpy.float32)
        dest_longitude_ = numpy.empty(shape=(batchsize, 1), dtype=numpy.float32)

        for i in range(batchsize):
            [trip_id_[i], call_type_[i], origin_call_[i], origin_stand_[i], taxi_id_[i], \
             day_type_[i], missing_data_[i], week_of_year_[i], day_of_week_[i], qhour_of_day_[i], \
             snapshot_[i], first_latitude_[i], first_longitude_[i], \
             last_latitude_[i], last_longitude_[i], dest_latitude_[i], dest_longitude_[i]] \
                = self.get_sample_data()

        return self.epoch, origin_call_, origin_stand_, day_type_, taxi_id_, \
               week_of_year_, day_of_week_, qhour_of_day_, snapshot_, \
               numpy.concatenate((first_latitude_, first_longitude_, last_latitude_, last_longitude_), axis=1), \
               numpy.concatenate((dest_latitude_, dest_longitude_), axis=1)

