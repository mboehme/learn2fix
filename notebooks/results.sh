#!/bin/bash
if [ $# -ne 1 ]; then
  echo "$0 <results.csv>"
  exit
fi
results=$1

if ! [ -e $results ]; then
  echo $results does not exist.
  exit
fi

if [ 0 -eq $(cat $results | wc -l) ]; then
  echo $results is empty.
  exit
fi

n_subjects=$(cat $results | cut -d, -f1 | sort | uniq | wc -l)
avg_labeling=$(echo "scale=2; $(cat $results | cut -d, -f4 | awk '{s+=$1} END {print s}') / $(cat $results | wc -l)" | bc)
no_failing=$(cat $results | cut -d, -f-5 | grep ,0$ | cut -d, -f1 | sort | uniq | wc -l) 
no_labled_fail=$(cat $results | cut -d, -f-6 | grep ,0$ | cut -d, -f1 | sort | uniq | wc -l) 

labeling_effort=$(echo "scale=2; $(cat $results | cut -d, -f4 | awk '{s+=$1} END {print s}') / $(cat $results | cut -d, -f3 | awk '{s+=$1} END {print s}') * 100" | bc)

labeled_fail=$(echo "scale=2; $(cat $results | cut -d, -f6 | awk '{s+=$1} END {print s}') / $(cat $results | cut -d, -f4 | awk '{s+=$1} END {print s}') * 100" | bc)
failure_rate=$(echo "scale=2; $(cat $results | cut -d, -f5 | awk '{s+=$1} END {print s}') / $(cat $results | cut -d, -f3 | awk '{s+=$1} END {print s}') * 100" | bc)
improvement=$(echo "scale=2; $labeled_fail / $failure_rate" | bc)


accuracy=$(echo "scale=2; $(cat $results | cut -d, -f8 | awk '{s+=$1} END {print s}') / $(cat $results | cut -d, -f7 | awk '{s+=$1} END {print s}') * 100" | bc)
accuracy_fail=$(echo "scale=2; $(cat $results | cut -d, -f10 | awk '{s+=$1} END {print s}') / $(cat $results | cut -d, -f9 | awk '{s+=$1} END {print s}') * 100" | bc)




echo "n_subjects      $n_subjects"
echo "avg_labeling    $avg_labeling"
echo "no_failing      $no_failing    #subjects where none of the generated test cases are failing."
echo "no_labled_fail  $no_labled_fail    #subjects where none of the labeled generated test cases are failing."

echo "labeling_effort $labeling_effort"
echo "labeled_fail    $labeled_fail"
echo "failure_rate    $failure_rate"
echo "improvement     $improvement"
echo "accuracy        $accuracy"
echo "accuracy_fail   $accuracy_fail"
