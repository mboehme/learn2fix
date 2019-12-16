#!/usr/bin/env python

import sys
import numpy as np
import subprocess

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
        test_output = subprocess.check_output(["timeout", "-k", "2s", "2s", program], stdin=process.stdout,encoding="utf-8")
    except:
        pass

    unformatted_output = unformat_output(test_output)

    return unformatted_output

# Execute test_input on buggy and golden program. Return false (test failure) if output differs
def ask_human(test_input, bug_prog, gold_prog):
    actual_output = run_test(test_input, bug_prog)
    expected_output = run_test(test_input, gold_prog)
    return actual_output == expected_output


iteration = sys.argv[1]
subject = sys.argv[2]
test = sys.argv[3]

bug_dir = subject.rstrip("/")
temp = bug_dir.split("/")[-1].split("-")
bug_prog = "./"+temp[0] + "-" + temp[1] + "-" + temp[3]
gold_prog = "./"+temp[0] + "-" + temp[1] + "-" + temp[4]
subject_name = bug_dir.split("/")[-1]

test_suite = []
test_data = np.genfromtxt("autogen-"+iteration+"-"+test)
test_suite.append(unformat_input(test_data, 0))
test_suite = np.array(test_suite)

if ask_human(test_suite[0], bug_prog, gold_prog):
  sys.exit(0)
else:
  sys.exit(1)



