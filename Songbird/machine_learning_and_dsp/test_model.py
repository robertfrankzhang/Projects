# -*- coding: utf-8 -*-

import glob
import os
import time

import numpy as np
from numpy import mean
from pyAudioAnalysis import audioTrainTest as aT


def find_stats(stats_matrix):
    stats = [class_stats(q) for q in stats_matrix]

    marker = 0
    for obj in stats:
        obj.stats_eval()
        print "F-score for class %s is %s" % (marker, obj.f_score())
        marker = marker + 1

    #Hopefully working paralellization for this part:
    #pros = Pool(num_threads)
    #pros.map(class_stats.stats_eval, stats)

    # Find micro-average F1
    micro_prec = do_division(sum([i.true_pos for i in stats]), sum([i.true_pos + i.false_pos for i in stats]))
    micro_recall = do_division(sum([i.true_pos for i in stats]), sum([i.true_pos + i.false_neg for i in stats]))
    micro_f1 = f_score(micro_prec, micro_recall)
    print "Micro-averaged F1 is %s \n" % micro_f1

    # Find macro-average F1
    macro_prec = mean([i.prec for i in stats])
    macro_recall = mean([i.recall for i in stats])
    macro_f1 = f_score(macro_prec, macro_recall)
    print "Macro-averaged F1 is %s \n" % macro_f1

    return stats


def f_score(prec, recall, Beta=1):
    fscore = do_division((1 + Beta ** 2) * (prec * recall), (Beta ** 2 * prec + recall))
    return fscore

class class_stats:
    def __init__(self, stats_row):
        self.stats_row = stats_row

    def stats_eval(self):
        stats_row = self.stats_row

        true_pos = stats_row[0]
        false_pos = stats_row[1]
        false_neg = stats_row[2]
        true_neg = stats_row[3]


        full_matrix_sum = sum(stats_row)

        accu = do_division((true_pos + true_neg), full_matrix_sum)
        sens = do_division(true_pos, (true_pos + false_neg))
        spec = do_division(true_neg, (true_neg + false_pos))

        prec = do_division(true_pos, (true_pos + false_pos))
        recall = sens

        self.true_pos = true_pos
        self.true_neg = true_neg
        self.false_pos = false_pos
        self.false_neg = false_neg

        self.accu = accu
        self.sens = sens
        self.spec = spec
        self.prec = prec
        self.recall = recall

    def f_score(self, Beta=1):
        prec = self.prec
        recall = self.recall
        fscore = do_division((1 + Beta**2) * (prec * recall), (Beta**2 * prec + recall))
        return fscore



def do_division(a, b):
    if a == 0 and b == 0:
        return 0.0
    else:
        return float(a) / float(b)

def unshared_copy(inList):
    #https://stackoverflow.com/questions/1601269/how-to-make-a-completely-unshared-copy-of-a-complicated-list-deep-copy-is-not
    if isinstance(inList, list):
        return list( map(unshared_copy, inList) )
    return inList


class tester:
    def __init__(self, test_dirs, model_dir=os.getcwd(), modelName='model', classifierType='gradientboosting',
                 level=0.5,
                 verbose=False):
        self.test_dirs = test_dirs
        self.model_dir = model_dir
        self.modelName = modelName
        self.classifierType = classifierType
        self.level = level
        self.verbose = verbose

    def test_model(self):

        test_dirs = self.test_dirs
        level = self.level
        model_dir = self.model_dir
        modelName = self.modelName
        classifierType = self.classifierType
        verbose = self.verbose

        # Used to test an existing model against new samples;
        # Test directories should contain the same categories and be in the same order as the original training data, but should contain seperate samples
        # model_dir is the path to the model file generated by the training function
        # modelName is the name of the model file generated by the trainging function
        # classifierType is the ML method used and should be the same as the training method used. Should be one of: svm, knn, gradientboosting, randomforest, extratrees
        # certainty_threshold: Any results with confidence below this should be treated as indeterminate
        # Level is confidence threshold above which test results should be considered
        # When store_to_mySQL is set to True results will be pushed to mySQL table specified in config.py

        # The following sets up a new table in the given db to store information about each classification; The table will be given the same name as the model file; the table will be dropped initially if a table with the same name already exists.

        start_time = time.clock()

        os.chdir(test_dirs[0])
        for file in glob.glob(u"*.wav"):  # Iterate through each wave file in the directory
            Result, P, classNames = aT.fileClassification(file, os.path.join(model_dir, modelName),
                                                          classifierType)  # Test the file
            break

        if classNames == -1:
            raise Exception("Model file " + os.path.join(model_dir, modelName) + " not found!")

        num_cats = len(classNames)
        temp = []
        for j in xrange(0, num_cats):
            temp.append(0)
        confusion_matrix = []
        for k in xrange(0, num_cats):
            confusion_matrix.append(unshared_copy(temp))

        confidence_above_90 = unshared_copy(temp)
        correct_above_90 = unshared_copy(temp)
        total_num_samples = unshared_copy(temp)
        confidence_corrected_con_matrix = unshared_copy(confusion_matrix)
        stats_matrix = [[0, 0, 0, 0] for x in xrange(0, num_cats)]
        for i in xrange(0, len(test_dirs)):  # Iterate through each test directory
            dir = test_dirs[i]
            os.chdir(dir)
            rootdir, correct_cat = os.path.split(dir)
            for file in glob.glob(u"*.wav"):  # Iterate through each wave file in the directory

                Result, P, classNames = aT.fileClassification(file, os.path.join(model_dir, modelName),
                                                              classifierType)  # Test the file

                if verbose:
                    print '\n', file
                    print Result
                    print classNames
                    print P, '\n'


                threshold = level

                for cls in xrange(0, len(P)):
                    if P[cls] > threshold:
                        if unicode(correct_cat) == unicode(classNames[cls]):
                            # True Positive
                            stats_matrix[cls][0] = stats_matrix[cls][0] + 1
                        else:
                            # False Positive
                            stats_matrix[cls][1] = stats_matrix[cls][1] + 1
                    else:
                        if unicode(correct_cat) == unicode(classNames[cls]):
                            # False Negative
                            stats_matrix[cls][2] = stats_matrix[cls][2] + 1
                        else:
                            # True Negative
                            stats_matrix[cls][3] = stats_matrix[cls][3] + 1

                identified_correctly = (unicode(correct_cat) == unicode(classNames[int(Result)]))
                confidence = max(P)

                indexes = [t for t, x in enumerate(classNames) if unicode(x) == unicode(correct_cat)]
                if unicode(correct_cat) == u'no_cat':
                    pass
                elif not len(indexes):
                    raise Exception(correct_cat + "is not a correctly named category for this model!")
                elif len(indexes) != 1:
                    raise Exception(correct_cat + "matches multiple categories in the model file!")
                cat_index = indexes[0]
                total_num_samples[cat_index] += 1
                confusion_matrix[cat_index][int(Result)] += 1
                if confidence > level:
                    confidence_corrected_con_matrix[cat_index][int(Result)] += 1
                    confidence_above_90[cat_index] += 1
                    if unicode(correct_cat) == unicode(classNames[int(Result)]):
                        assert (identified_correctly)
                        correct_above_90[cat_index] += 1

        acc_above_90 = map(do_division, correct_above_90, confidence_above_90)
        percent_desicive_samples = map(do_division, confidence_above_90, total_num_samples)

        print '\n', "Agregated Results: ", '\n'
        print classNames
        print "acc above ", level, ": ", acc_above_90
        print "percent samples above ", level, ": ", percent_desicive_samples
        print "total samples tested in each category: ", total_num_samples, '\n'
        print "confusion matrix:"
        aT.printConfusionMatrix(np.array(confusion_matrix), classNames)
        print "\n", "confidence adjusted confustion matrix:"
        aT.printConfusionMatrix(np.array(confidence_corrected_con_matrix), classNames)

        print '\n', "Processed ", sum(total_num_samples), " samples in ", time.clock() - start_time, " seconds."

        stats = find_stats(stats_matrix)

        self.stats = stats
        return stats

def basic_roc_plot(fpr, tpr, className):
    #https://stackoverflow.com/questions/25009284/how-to-plot-roc-curve-in-python
    from sklearn import metrics
    roc_auc = metrics.auc(fpr, tpr)
    print "AUC for %s is %s" % (className, roc_auc)
    return roc_auc
    plt.title('Receiver Operating Characteristic for %s' % className)
    plt.plot(fpr, tpr, 'b', label='AUC = %0.2f' % roc_auc)
    plt.legend(loc='lower right')
    plt.plot([0, 1], [0, 1], 'r--')
    plt.xlim([0, 1])
    plt.ylim([0, 1])
    plt.ylabel('True Positive Rate')
    plt.xlabel('False Positive Rate')
    plt.show()

if __name__ == '__main__':
    birds = ['bluejay_all', 'cardinal_song', 'chickadee_song', 'crow_all', 'goldfinch_song', 'robin_song', 'sparrow_song', 'titmouse_song']
    birds = [os.path.join("/run/media/zach/untitled/ML Recordings/xeno-canto/testing", bird, bird + '_clean') for bird
             in
             birds]
    birds.append("/run/media/zach/untitled/ML Recordings/xeno-canto/Testing/no_cat")

    #new_test = tester(test_dirs=birds, model_dir="/home/zach/Documents/bird_samples", modelName="gradientboosting_Test")
    #new_test.test_model()

    print ''
    thresholds = [0.0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9]
    tests = []
    for t in thresholds:
        tests.append(
            tester(test_dirs=birds, model_dir="/home/zach/Documents/bird_samples", modelName="gradientboosting_Test",
                   level=t, verbose=True))

    for r in tests:
        r.test_model()

    # pros = Pool(mp.cpu_count())
    # pros.map(t.test_model() for t in tests)

    num_classes = len(birds)
    per_class_fpr = [[] for a in xrange(num_classes)]
    per_class_tpr = [[] for a in xrange(num_classes)]
    micro_average_fpr = []
    micro_average_tpr = []
    for v in tests:
        micro_average_fpr.append(mean([1 - v.stats[f].spec for f in xrange(num_classes)]))
        micro_average_tpr.append(mean([v.stats[f].sens for f in xrange(num_classes)]))

        for q in xrange(0, num_classes):
            per_class_fpr[q].append(1 - v.stats[q].spec)
            per_class_tpr[q].append(v.stats[q].sens)

    auc_scores = []
    for g in xrange(num_classes):
        auc_scores.append(basic_roc_plot(per_class_fpr[g], per_class_tpr[g], birds[g]))

    macro_average_auc = mean(auc_scores)

    basic_roc_plot(micro_average_fpr, micro_average_tpr, "Micro-average")
    print "AUC for %s is %s" % ("Macro-average", macro_average_auc)




