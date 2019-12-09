#!/usr/bin/env python
from inspect import signature
import os
import re
import subprocess
import numpy as np
import csv
import threading
import argparse
import glob

from decimal import Decimal,DecimalException

# Don't forget to point PYTHONPATH to
# export PYTHONPATH=$PYTHONPATH:$PWD/../incal/experiments
# export PYTHONPATH=$PYTHONPATH:$PWD/../incal/extras
# export PYTHONPATH=$PYTHONPATH:$PWD/../incal

import sys
from examples import ice_cream_problem
from pywmi.plot import plot_data, plot_formula
from pywmi.sample import uniform
from pywmi.smt_check import evaluate
import random
from violations.core import RandomViolationsStrategy
from k_cnf_smt_learner import KCnfSmtLearner
from pywmi.smt_print import pretty_print

from pysmt.shortcuts import REAL, INT, Or, And, LE, Real,ArrayType, Symbol,String, BOOL, GT, LT, Not, Plus, Times, GE, Ite, Equals, Minus, Implies
from pywmi import Domain
#random.seed(666)
#np.random.seed(666)
from parameter_free_learner import learn_bottom_up
from pywmi import smt_to_nested
from pywmi.smt_print import pretty_print
import time

def learn_f(_data, _labels, _i, _k, _h):
    learner = KCnfSmtLearner(_k, _h, RandomViolationsStrategy(10), "mvn")
    initial_indices = [i for i in range(len(_data))]
    random.shuffle(initial_indices)
    return learner.learn(domain, _data, _labels, initial_indices)

#Automatically detect the domain:charaka
def get_subject_domain(input_size):
    variables=[]
    var_types={}
    var_domains={}

    for i in range(1,input_size+1):
        variables.append("i"+str(i))
        var_types["i"+str(i)]=REAL
        var_domains["i"+str(i)]=(-0x800000000, 0x800000000)

    variables.append("o")
    var_types["o"]=REAL
    var_domains["o"]=(-0x800000000, 0x800000000)

    return Domain(variables,var_types,var_domains)


# Write: Convert input value(s) into string
def format_input(test_input):

    input_vals=""
    if((type(test_input) is np.ndarray) or (type(test_input) is list)):

        for i_val in test_input:
            input_vals+=str(int(i_val))+" "

        input_vals=input_vals.strip()

    else:
        input_vals=str(int(test_input))


    return input_vals

    #return str(int(test_input))

# Read: Convert input string into value(s)
def unformat_input(test_input, input_size):
    if((type(test_input) is np.ndarray) or (type(test_input) is list)):
        if test_input.size != input_size and input_size > 0:
            sys.exit("[ERROR "+subject_name+"] Input has variable length")
        return test_input

    if input_size > 1:
        sys.exit("[ERROR "+subject_name+"] Input has variable length")
    return int(test_input)

# Read: Convert output string into value.
def unformat_output(test_output):
    if test_output == "": return 0
    if test_output.strip().lower() == "yes": return 1
    if test_output.strip().lower() == "no" : return 0

    try: return int(test_output)
    except:
        try: return int(round(float(test_output),0))
        except: sys.exit("[ERROR "+subject_name+"] Unknown output")

# Execute test_input on program and return output value
def run_test(test_input, program):
    formatted_input = format_input(test_input)
    process = subprocess.Popen(('echo', formatted_input), stdout=subprocess.PIPE)
    test_output=""
    try:
        test_output = subprocess.check_output(["timeout","-k","2s","2s", program], stdin=process.stdout,encoding="utf-8")
    except:
        pass

    unformatted_output = unformat_output(test_output)

    return unformatted_output

# Execute test_input on buggy and golden program. Return false (test failure) if output differs
def ask_human(test_input, bug_dir, bug_prog, gold_prog):
    actual_output = run_test(test_input, bug_dir+"/"+bug_prog)
    expected_output = run_test(test_input, bug_dir+"/"+gold_prog)
    return actual_output == expected_output

# Returns a test suite with duplicate test cases removed
# This function increases the dimension of the array. Therefore, I replace it with my previous one:charaka.

def custom_mutation(seed_input):
    input_val = np.copy(seed_input)

    mutate_functions=["add_one", "subtract_one", "add_ten", "subtract_ten",
                      "add_one", "subtract_one", "add_ten", "subtract_ten",
                      "random_integer", "random_integer_100", "multiply_ten", "divide_ten"] #make_zero

    def add_one(input_val):
        return input_val + 1

    def subtract_one(input_val):
        return input_val - 1

    def add_ten(input_val):
        return input_val + 10

    def subtract_ten(input_val):
        return input_val - 10

    def multiply_ten(input_val):
        return input_val * 10

    def divide_ten(input_val):
        return input_val/10

    def make_zero(input_val):
        return 0

    def random_integer_100(input_val):
       return np.random.randint(-100, 100)

    def random_integer(input_val):
        try:
            if input_val > 0:
                return np.random.randint(-2 * input_val, 2 * input_val)
            elif input_val < 0:
                return np.random.randint(2 * input_val, -2 * input_val)
            else:
                return random_integer_100(input_val)
        except: return random_integer_100(input_val)


    if((type(input_val) is np.ndarray) or (type(input_val) is list)):

        random_indexes=np.random.randint(len(input_val),size=len(input_val))

        for r_ind in random_indexes:
            stack_size=np.random.randint(low=1,high=10)
            random_ops=random.choices(mutate_functions,k=stack_size)

            for op in random_ops:
                input_val[r_ind]=locals()[op](input_val[r_ind])
    else:

        stack_size=np.random.randint(low=1,high=10)
        random_ops=random.choices(mutate_functions,k=stack_size)

        for op in random_ops:
            input_val=locals()[op](input_val)

    # * Implement *generational* approach (rather than mutating a given input, you generate a random input >independently< of the given input)
    # * Extend fuzzing and training to a vector if input values (in the mutational approach, you choose a random index to apply the mtuation operator to.)
    return input_val

# Returns a mutated variant of seed_input. Avoids duplicates
def getMutatedTestCase(test_suite, seed_input):
    while True:
        mutated_input = custom_mutation(seed_input)
        mutated_output = run_test(mutated_input, bug_dir + "/" + bug_prog)
        mutated_testcase = np.append(mutated_input, mutated_output)

        no_duplicate = True
        for t in test_suite:
            if all(ti in t  for ti in mutated_testcase):
                no_duplicate = False
                break
        if no_duplicate:
            return np.array(mutated_testcase)

parser = argparse.ArgumentParser()
parser.add_argument("-s", "--subject", help="Path to Codeflaws bug", required=True)
parser.add_argument("-i", "--iteration", help="ID of the current iteration", default=1, type=int)
parser.add_argument("-t", "--timeout", help="Maximal time budget (in minutes) for an experimental repetition", default=10, type=int)
parser.add_argument("-S", "--max_no_progress", help="Maximal number of test inputs generated without asking the human", default=20, type=int)
parser.add_argument("-N", "--committee_size", help="Maximal number of test inputs generated without asking the human", default=10, type=int)
parser.add_argument("-M", "--committee_majority", help="Minimal predicted failure probability while still asking the human", default=0.5, type=float)
parser.add_argument("-l", "--max_labels", help="Maximial number of times asking the human", default=20, type=int)
parser.add_argument("-d", "--debug", help="Enable debugging.", action='store_true')
args = parser.parse_args()


iteration = args.iteration
timeout = args.timeout

committee_size = args.committee_size
committee_majority = args.committee_majority
max_labels = args.max_labels
debug = args.debug

bug_dir = args.subject.rstrip("/")
temp = bug_dir.split("/")[-1].split("-")
bug_prog = temp[0] + "-" + temp[1] + "-" + temp[3]
gold_prog = temp[0] + "-" + temp[1] + "-" + temp[4]
subject_name = bug_dir.split("/")[-1]

if debug:
    print("[INFO] Subject: " + subject_name)
    print("[INFO] Settings: timeout=%d min, max_labels=%d, committee_size=%d, committee_majority=%.1f" % (timeout, max_labels, committee_size, committee_majority))

# compile
if (not os.path.exists(bug_dir + "/" + bug_prog)):
    filename = bug_dir + "/" + bug_prog
    os.system("gcc -fno-optimize-sibling-calls -fno-strict-aliasing -fno-asm -std=c99 -c " + filename + ".c -o " + filename + ".o")
    os.system("gcc " + filename + ".o -o " + filename + " -lm -s -O2")

if (not os.path.exists(bug_dir + "/" + gold_prog)):
    filename = bug_dir + "/" + gold_prog
    os.system("gcc -fno-optimize-sibling-calls -fno-strict-aliasing -fno-asm -std=c99 -c " + filename + ".c -o " + filename + ".o")
    os.system("gcc " + filename + ".o -o " + filename + " -lm -s -O2")

# read test inputs (excluding heldout)
test_inputs = []
for _, _, file_list in os.walk(bug_dir):
    for f in file_list:
        if re.search('^input', f):
            data_f = np.genfromtxt(bug_dir+"/"+f)
            test_inputs.append(unformat_input(data_f, 0))

test_inputs = np.array(test_inputs)
test_outputs = np.array([run_test(test_input, bug_dir+"/"+bug_prog) for test_input in test_inputs])
test_labels = np.array([ask_human(test_input, bug_dir, bug_prog, gold_prog) for test_input in test_inputs])

if np.sum(test_labels) == test_labels.size:
    sys.exit("[ERROR "+subject_name+"] No failing test cases")

# Construct domain
if (type(test_inputs[0]) is np.ndarray) or (type(test_inputs[0]) is list):
    input_size = len(test_inputs[0])
else:
    input_size = 1
domain = get_subject_domain(input_size)

failing_index = np.nonzero(test_labels == False)[0][np.random.randint(test_labels.size - np.sum(test_labels))]
failing_testcase = np.append(test_inputs[failing_index], test_outputs[failing_index])

# TODO Maybe invert labels to leran "error condition"?
trainer_test_suite = np.array([failing_testcase])
trainer_labels = np.array([False])
(_,_,learned_model),_,_ = learn_bottom_up(np.array(trainer_test_suite), trainer_labels, learn_f, 1, 1, 1, 1)

n_human_labeled = 0
n_generated = 0
n_failing = 0

mutated_failing = []
mutated_failing.append(trainer_test_suite[0])

oracle_committee = []

timeout = time.time() + 60 * timeout
if debug: print("[INFO] Start learning (iteration: "+str(iteration)+")...")

while time.time() < timeout and n_human_labeled < max_labels:
    if np.random.randint(0,100) < 50:
      seed_input = mutated_failing[np.random.randint(len(mutated_failing))][:-1]
    else:
      seed_input = trainer_test_suite[0][:-1]
    fuzzed_test_case = getMutatedTestCase(trainer_test_suite, seed_input)
    predict_label = evaluate(domain,learned_model,np.array(fuzzed_test_case))
    n_generated += 1
    if False == ask_human(fuzzed_test_case[:-1], bug_dir, bug_prog, gold_prog):
        n_failing += 1

    all_fail_prob = (trainer_labels.size - np.sum(trainer_labels)) / trainer_labels.size

    # If the current test_input is predicted as failing
    # OR if we have mostly labled failing test cases and the current test input is predicted as passing
    if predict_label == False or (trainer_labels.size > 10 and all_fail_prob > 0.9 and predict_label == True):
        # ask human to label, and
        human_label = ask_human(fuzzed_test_case[:-1], bug_dir, bug_prog, gold_prog)
        # add to trainer_test_suite
        trainer_test_suite = np.append(trainer_test_suite, [fuzzed_test_case], axis=0)
        trainer_labels = np.append(trainer_labels, [human_label], axis=0)
        # re-train automated oracle
        (_,_,learned_model),_,_ = learn_bottom_up(trainer_test_suite, trainer_labels, learn_f, 1, 1, 1, 1)

        n_human_labeled += 1
        oracle_committee = []

        if(human_label == False):
            mutated_failing.append(fuzzed_test_case)
        if debug: print("[INFO] Fail Prob = 1.0, Human Label = %s" % human_label)
    else:
        fail_votes = 0

        # Construct committee if needed
        if len(oracle_committee) == 0:
            for i in range(committee_size):
                if np.random.randint(0,100) < 50:
                    seed_input = mutated_failing[np.random.randint(len(mutated_failing))][:-1]
                else:
                    seed_input = trainer_test_suite[0][:-1]
                secondary_fuzzed_test_case = getMutatedTestCase(trainer_test_suite, seed_input)
                secondary_trainer_test_suite = np.append(trainer_test_suite, [secondary_fuzzed_test_case], axis=0)

                secondary_trainer_labels_pass=np.append(trainer_labels,[True],axis=0)
                secondary_trainer_labels_fail=np.append(trainer_labels,[False],axis=0)

                (_,_,learned_model_pass),_,_ = learn_bottom_up(secondary_trainer_test_suite, secondary_trainer_labels_pass, learn_f, 1, 1, 1, 1)
                (_,_,learned_model_fail),_,_ = learn_bottom_up(secondary_trainer_test_suite, secondary_trainer_labels_fail, learn_f, 1, 1, 1, 1)

                oracle_committee.append(learned_model_pass)
                oracle_committee.append(learned_model_fail)

        for member in oracle_committee:
            predict_label = evaluate(domain, member, np.array(fuzzed_test_case))
            if predict_label == False:
                fail_votes += 1

        fail_prob = fail_votes/(2*committee_size)

        # If the probability of the current test input failing is high
        # OR if we have mostly labeled failing test cases and the probability of the current test input failing is low
        if fail_prob >= committee_majority or (trainer_labels.size > 10 and all_fail_prob > 0.9 and fail_prob < 1 - committee_majority):
            # ask human to label, and
            human_label = ask_human(fuzzed_test_case[:-1], bug_dir, bug_prog, gold_prog)
            # add to trainer_test_suite
            trainer_test_suite = np.append(trainer_test_suite, [fuzzed_test_case], axis=0)
            trainer_labels = np.append(trainer_labels, [human_label], axis=0)
            # re-train automated oracle
            (_,_,learned_model),_,_ = learn_bottom_up(trainer_test_suite, trainer_labels, learn_f, 1, 1, 1, 1)

            n_human_labeled += 1
            oracle_committee = []

            # add to labelled failing test cases.
            if human_label == False:
                mutated_failing.append(fuzzed_test_case)
            if debug: print("[INFO] Fail Prob = %.1f, Human Label = %s" % (fail_prob, human_label))

        else:
            # TODO count negative test cases that are not labeled?
            if debug: print("[INFO] Fail Prob = %.1f, NO Human Label" % fail_prob)


# RESULTS

# Read validation (incl. heldout) test suite
heldout_test_inputs = []
for _, _, file_list in os.walk(bug_dir):
    for f in file_list:
        if re.search('^heldout-input', f):
            data_f = np.genfromtxt(bug_dir+"/"+f)
            heldout_test_inputs.append(unformat_input(data_f, input_size))
        if re.search('^input', f):
            data_f = np.genfromtxt(bug_dir+"/"+f)
            heldout_test_inputs.append(unformat_input(data_f, input_size))

#if debug:
#    print("Heldout:")
#    for test_input in heldout_test_inputs:
#        print(format_input(test_input))

heldout_test_inputs = np.array(heldout_test_inputs)
heldout_test_outputs = np.array([run_test(test_input, bug_dir+"/"+bug_prog) for test_input in heldout_test_inputs])
heldout_test_labels = np.array([ask_human(test_input, bug_dir, bug_prog, gold_prog) for test_input in heldout_test_inputs])
heldout_test_suite = []
for i_ts in range(heldout_test_inputs.shape[0]):
    heldout_test_suite.append(np.append(heldout_test_inputs[i_ts], heldout_test_outputs[i_ts]))
heldout_test_suite = np.array(heldout_test_suite)

if debug: print(learned_model)
predicted_labels = evaluate(domain, learned_model, heldout_test_suite)

n_elems = heldout_test_labels.size
n_true = np.sum(heldout_test_labels)
n_false = n_elems - n_true

n_correct = 0
n_fail_correct = 0
for l in range(len(heldout_test_labels)):
    if(predicted_labels[l] == heldout_test_labels[l]):
        n_correct += 1
        if(heldout_test_labels[l] == False):
            n_fail_correct+=1

if debug:
    print(mutated_failing)

    print("GENERATION")
    print("Number of labeled / generated test cases: " + str(n_human_labeled) + " / " + str(n_generated))
    print("Number of labeled / failing   test cases: " + str(len(mutated_failing)-1) + " / " + str(n_failing))

    if n_failing > 0 and n_generated > 0 and n_human_labeled > 0:
        improvement = ((len(mutated_failing)-1) / n_human_labeled) / (n_failing / n_generated)
        print("How much more likely to label a fail. test: %.1f times." % improvement)

    print("")
    print("VALIDATION")
    print("Number of correctly labeled / all test cases: " + str(n_correct) + " / " + str(n_elems))
    print("Number of correctly labeled / failing tcases: " + str(n_fail_correct) + " / " + str(n_false))

    print("Accuracy: "+str((n_correct/n_elems)*100))

print(bug_dir.split("/")[-1]+","+str(iteration)+","+str(n_generated)+","+str(n_human_labeled)+","+str(n_failing)+","+str(len(mutated_failing)-1)+
      ","+str(n_elems)+","+str(n_correct)+","+str(n_false)+","+str(n_fail_correct))

#save the test suite to files for repair tools
lindex = 0 #label index
pindex = 1 #starting index for positive test cases
nindex = 1 #starting index for negative test cases

#Remove existing incal files (Cleanup)
incalFiles = glob.glob(bug_dir + '/' + 'autogen-' + str(iteration) + '-*', recursive=False)
for f in incalFiles:
    os.remove(f)

for tl in trainer_labels:
    cur_tc = trainer_test_suite[lindex]
    cur_input = cur_tc[:len(cur_tc) - 1]
    #cur_output = cur_tc[-1]
    cur_output = run_test(cur_input, bug_dir+"/"+gold_prog)
    fin = bug_dir + "/" + "autogen-"+str(iteration)
    if tl == True:
        fin = fin + "-p" + str(pindex)
        pindex = pindex + 1
    else:
        fin = fin + "-n" + str(nindex)
        nindex = nindex + 1
    autogen_test_file = open(fin, "w+")
    autogen_test_file.write(format_input(cur_input)+"\n")
    autogen_test_file.close()
    lindex = lindex + 1


