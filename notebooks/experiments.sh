#!/bin/bash
if [ $# -ne 1 ]; then
  echo "$0 <codeflaws directory>" 1>&2
  exit
fi
if ! [ -d "$1" ]; then
  echo "Not a directory: $1" 1>&2
  exit
fi

if [ -z "$(which cilly)" ]; then
  echo "cilly compiler not found!" 1>&2
  exit
fi

codeflaws_dir=$1
repair_dir=$codeflaws_dir/../
rm $codeflaws_dir/*/autogen* &> /dev/null
rm $codeflaws_dir/*/incal* &> /dev/null

if ! [ -e $repair_dir/learn2fix ]; then
  echo $repair_dir/learn2fix does not exist.
  exit
fi
cp $repair_dir/learn2fix/repairs/genprog/* $repair_dir/
if [ -e $repair_dir/genprog-run ]; then
  echo "[INFO] Saving $repair_dir/genprog-run.." 1>&2
  rm -rf $repair_dir/genprog-run.old 2> /dev/null
  mv $repair_dir/genprog-run $repair_dir/genprog-run.old
fi
mkdir $repair_dir/genprog-run

#TODO Where is genprog_allfixes created?
if [ -e $repair_dir/genprog-allfixes ]; then
  echo "[INFO] Saving $repair_dir/genprog-allfixes.." 1>&2
  rm -rf $repair_dir/genprog-allfixes.old 2> /dev/null
  mv $repair_dir/genprog-allfixes $repair_dir/genprog-allfixes.old
fi
mkdir $repair_dir/genprog-allfixes


for s in $(ls -1d $codeflaws_dir/*/); do
  found=false;
  for f in $(ls -1 $s/*input*); do if [ $(wc -l $f | cut -d" " -f1) -gt 1 ]; then found=true; continue; fi; done;
  if [ "$found" = false ]; then
    if [ $(cat $s/input-neg1 | grep -x -E '[[:blank:]]*([[:digit:]]+[[:blank:]]*)*' | wc -l) -eq 1 ]; then
      #echo $s
      subject=$(echo $s | rev | cut -d/ -f2 | rev)
      buggy=$(echo $subject | cut -d- -f1,2,4)
      golden=$(echo $subject | cut -d- -f1,2,5)
      if [ 0 -eq $(grep "$subject" $codeflaws_dir/codeflaws-defect-detail-info.txt | grep "WRONG_ANSWER" | wc -l) ]; then
        echo "[INFO] Skipping non-semantic bug $subject" 1>&2
        continue
      fi
      if ! [ -f "$s/$buggy" ]; then
        gcc -fno-optimize-sibling-calls -fno-strict-aliasing -fno-asm -std=c99 -c $s/$buggy.c -o $s/$buggy.o &> /dev/null
        gcc $s/$buggy.o -o $s/$buggy -lm -s -O2 &> /dev/null
      fi
      if ! [ -f "$s/$golden" ]; then
        gcc -fno-optimize-sibling-calls -fno-strict-aliasing -fno-asm -std=c99 -c $s/$golden.c -o $s/$golden.o &> /dev/null
        gcc $s/$golden.o -o $s/$golden -lm -s -O2 &> /dev/null
      fi
      cp $repair_dir/learn2fix/repairs/genprog/test-genprog-incal.py $s/

      for i in $(seq 1 $(nproc --all)); do
        #will produce the i-th test suite and do the repair subsequently
        (
          autotest=$(timeout 11m ./Learn2Fix.py -t 10 -s $s -i $i)

          if [ $? -eq 0 ]; then
            manual=$($repair_dir/run-version-genprog.sh $subject $i manual)
            autogen=$($repair_dir/run-version-genprog.sh $subject $i autogen)
            # Parse output and echo comma-separated values (attached to output from Learn2Fix)
            #./extract_genprog_results.sh $subject $i $repair_dir/genprog-summary.log
            echo $autotest | tr -d '\n'
            echo ,$manual | tr -d '\n'
            echo ,$autogen
          fi
        ) >> results_it_$i.csv &
      done
      wait
    else
      echo "[INFO] Skipping non-numeric input subject: $s" 1>&2
    fi
  else
    echo "[INFO] Skipping multi-line input subject: $s" 1>&2
  fi
done

