import numpy as np
from six.moves import xrange
from sklearn import linear_model
from sklearn.mixture import GaussianMixture


# TODO: Transform all arrays to np.array to work only with one and not be changing
class TwitchHighlight:
    def __init__(self, messages_timestamp):
        parse_timestamp_seconds = lambda hms: sum(map(lambda a, b: int(a) * b, hms.split(':'), (3600, 60, 1)))
        self.times = list(map(lambda x: parse_timestamp_seconds(x), messages_timestamp))
        self.messages_per_second = self.get_messages_per_second()
        self.window_size = 9

    def get_messages_per_second(self):
        messages_per_second = np.zeros(self.times[-1] + 1)
        current_second = 0
        for time in self.times:
            while not current_second <= time < current_second + 1:
                current_second += 1
            messages_per_second[current_second] += 1
        return messages_per_second

    def get_candidates(self):
        mov_avg_y = moving_average(self.messages_per_second, self.window_size)
        x = np.arange(self.times[-1] + 1)
        y = subtract_linear_fit(x, mov_avg_y)
        [sts, ends] = self.get_segments(y)
        [sts, ends] = self.filter_segments(y, sts, ends)
        return [TwitchCandidate(sts[i], ends[i]) for i in xrange(len(sts))]

    @staticmethod
    def filter_segments(y, sts, ends):
        sts, ends = TwitchHighlight.remove_no_len_segment(sts, ends)
        features = TwitchHighlight.get_segments_features(y, sts, ends)
        gmm = TwitchHighlight.fit_gmm(features)
        indexes = TwitchHighlight.get_high_rate_msgs(features, gmm)
        sts = np.array(sts)[indexes]
        ends = np.array(ends)[indexes]
        return sts, ends

    @staticmethod
    def remove_no_len_segment(sts, ends):
        diff_not_zero = [(ends[i] - sts[i]) != 0 for i in range(len(sts))]
        sts = [sts[i] for i in range(len(sts)) if diff_not_zero[i]]
        ends = [ends[i] for i in range(len(sts)) if diff_not_zero[i]]
        return sts, ends

    # TODO: Add description
    @staticmethod
    def get_high_rate_msgs(data, gmm):
        gmm_type = TwitchHighlight.get_case_type(gmm)
        indexes = []
        if gmm_type == 1:
            indexes = TwitchHighlight.get_highest_gmm_indexes(data, gmm)
        elif gmm_type == 2:
            indexes = TwitchHighlight.get_two_highest_gmm_indexes(data, gmm)
        elif gmm_type == 3:
            indexes = TwitchHighlight.get_highest_not_max_gmm_indexes(data, gmm)
        return indexes[0]

    @staticmethod
    def get_case_type(gmm):
        type = 0
        n_components = gmm.means_.shape[0]
        max_gmm_small = TwitchHighlight.is_max_gmm_area_small(gmm)
        if n_components == 2:
            type = 1
        elif n_components == 3 and not max_gmm_small:
            type = 1
        elif n_components == 3 and max_gmm_small:
            type = 2
        elif n_components > 3 and not max_gmm_small:
            type = 2
        elif n_components > 3 and max_gmm_small:
            type = 2
        return type

    @staticmethod
    def get_highest_gmm_indexes(data, gmm):
        sorted_max_idx = TwitchHighlight.sort_gmm_max_means(gmm)
        Y_ = gmm.predict(data)
        indexes = np.where(Y_ == sorted_max_idx[0])
        return indexes

    @staticmethod
    def get_highest_not_max_gmm_indexes(data, gmm):
        sorted_max_idx = TwitchHighlight.sort_gmm_max_means(gmm)
        Y_ = gmm.predict(data)
        indexes = np.where(Y_ == sorted_max_idx[1])
        return indexes

    @staticmethod
    def get_two_highest_gmm_indexes(data, gmm):
        sorted_max_idx = TwitchHighlight.sort_gmm_max_means(gmm)
        Y_ = gmm.predict(data)
        indexes1 = np.where(Y_ == sorted_max_idx[0])
        indexes2 = np.where(Y_ == sorted_max_idx[1])
        indexes = []
        indexes.append([])
        indexes[0] = np.concatenate((indexes1[0], indexes2[0]))
        return indexes

    @staticmethod
    def sort_gmm_max_means(gmm):
        means_means = []
        means_means_idx = []
        for i, (mean, cov) in enumerate(zip(gmm.means_, gmm.covariances_)):
            means_means.append(mean[0])
            means_means_idx.append(i)
        sorted_idx = [i[0] for i in sorted(enumerate(means_means), key=lambda x: x[1], reverse=True)]
        return [means_means_idx[i] for i in sorted_idx]

    @staticmethod
    def is_max_gmm_area_small(gmm):
        max_mean_idx = -1
        max_mean = 0
        for i, (mean, cov) in enumerate(zip(gmm.means_, gmm.covariances_)):
            if mean[0] > max_mean:
                max_mean = mean[0]
                max_mean_idx = i
        if (gmm.covariances_[max_mean_idx] <= 1e-5).all():
            return True
        return False

    @staticmethod
    def get_segments(y):
        st = False
        sts = []
        ends = []
        for i, yi in enumerate(y):
            if yi > 0 and st is False:
                st = True
                sts.append(i)
            elif yi == 0 and st is True:
                st = False
                ends.append(i)
        if st:
            ends.append(len(y) - 1)
        return sts, ends

    @staticmethod
    def get_segments_features(y, sts, ends):
        features = np.zeros((len(sts), 2))
        for i in xrange(len(sts)):
            features[i, 0] = np.mean(y[sts[i]:ends[i]])
            features[i, 1] = np.var(y[sts[i]:ends[i]])
        return features

    @staticmethod
    def fit_gmm(data):
        lowest_bic = np.infty
        bic = []
        best_gmm = None
        cv_types = ['spherical', 'tied', 'diag', 'full']
        for cv_type in cv_types:
            for n in range(1, 4):
                gmm = GaussianMixture(n_components=n, covariance_type=cv_type)
                gmm.fit(data)
                bic.append(gmm.bic(data))
                if bic[-1] < lowest_bic:
                    lowest_bic = bic[-1]
                    best_gmm = gmm
        return best_gmm


class TwitchCandidate:
    def __init__(self, st, end):
        self.st = st
        self.end = end


# TODO: Use numpy notation to simplify sum and mean
def moving_average(array, window):
    y = np.zeros(len(array))
    mid_len = int((window - 1) / 2)
    for i in xrange(len(array)):
        sum = 0
        n = 0
        window_st = i - mid_len if i - mid_len > 0 else 0
        window_end = i + mid_len + 1 if i + mid_len + 1 < len(array) else len(array)
        for j in xrange(window_st, window_end):
            sum += array[j]
            n += 1
        y[i] = sum / n
    return y


def subtract_linear_fit(x, y):
    lr = linear_model.LinearRegression()
    lr.fit(x[:, np.newaxis], y)
    y = y - lr.predict(x[:, np.newaxis])
    y = [yi if yi > 0 else 0 for yi in y]
    y = y / max(y)
    return y
