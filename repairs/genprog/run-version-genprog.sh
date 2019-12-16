#!/bin/bash
# Script to run spr on subjects in codeflaws directory
#The following variables needs to be changed:
rootdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )" #directory of this script
rundir="$rootdir/genprog-run" # directory in which genprog is called from, a temporary output directory where everything will be copied to during the repair
versiondir="$rootdir/codeflaws" #directory where the codeflaws.tar.gz is extracted
version=$1
genprog="/opt/genprog/bin/genprog" # location of the installed genprog
iteration=$2
testsuite=$3
timelimit=$4

kill_descendant_processes() {
    local pid="$1"
    local and_self="${2:-false}"
    if children="$(pgrep -P "$pid")"; then
        for child in $children; do
            kill_descendant_processes "$child" true
        done
    fi
    if [[ "$and_self" == true ]]; then
        kill -9 "$pid"
    fi
}

print_results(){
  if ! [ -z "$4" ]; then
    echo "$testsuite,$2,$3,$4"
  else 
    echo "$testsuite,$2,$3,,,"
  fi
  exit
}

if [[ "$version" == *"-bug-"* ]]; then
  if ! grep -q "$version" $rootdir/versions-ignored-all.txt; then
    var=$((var+1))
    #get buggy filename from directory name:
    contestnum=$(echo $version | cut -d$'-' -f1)
    probnum=$(echo $version | cut -d$'-' -f2)
    buggyfile=$(echo $version | cut -d$'-' -f4)
    cfile=$(echo "$contestnum-$probnum-$buggyfile".c)
    cilfile=$(echo "$contestnum-$probnum-$buggyfile".cil.c)
    cfixfile=$(echo "$contestnum-$probnum-$buggyfile"-fix.c)
    if [[ "$testsuite" = autogen ]]; then
      diffc=$(ls -1 $versiondir/$version/autogen-$iteration-n* | wc -l)
      posc=$(ls -1 $versiondir/$version/autogen-$iteration-p* | wc -l)
    else
      diffc=$(grep "Diff Cases" $versiondir/$version/$cfile.revlog | awk '{print $NF}')
      posc=$(grep "Positive Cases" $versiondir/$version/$cfile.revlog | awk '{print $NF}')
    fi

    echo "[INFO] Repairing $version ($testsuite, iteration $iteration with $posc positive and $diffc negative test cases)" 1>&2

    DIRECTORY="$versiondir/$version"
    if [ ! -d "$DIRECTORY" ]; then
      echo "[ERROR] FOLDER DOESNT EXIST: $version" 1>&2
      exit 1
    fi

    cd $rundir/
    rm -rf $rundir/tempworkdir-$version-$iteration-$testsuite
    rm -rf $rundir/tempworkdir-$version-$iteration-$testsuite-validation
    cp -r $versiondir/$version $rundir/tempworkdir-$version-$iteration-$testsuite
    cd $rundir/tempworkdir-$version-$iteration-$testsuite

    cp $rootdir/configuration-default configuration-$version
    if [[ "$testsuite" = autogen ]]; then
      sed -i "s/test-genprog.sh/test-genprog-incal.py $iteration $version/g" configuration-$version
    else
      sed -i "s/50s/2s/g" test-genprog.sh #Timeout management
    fi
   
    cp $rootdir/compile.pl compile.pl
    echo "$cfile">>bugged-program.txt
    echo "--pos-tests $posc">>configuration-$version
    echo "--neg-tests $diffc">>configuration-$version
    rm -rf preprocessed
    rm -rf coverage
    mkdir -p preprocessed
    make CC="cilly" CFLAGS="--save-temps -std=c99 -fno-optimize-sibling-calls -fno-strict-aliasing -fno-asm" &> initialbuild
    if grep -q "Error:" initialbuild; then
       if grep -q "Length of array is not" initialbuild; then
         printf "[ERROR] %s\t%s\t%s\n" "$version" "MAKE:ARRAY BUG" "0s" 1>&2
       else
         printf "[ERROR] %s\t%s\t%s\n" "$version" "MAKEFAILED!" "0s" 1>&2
       fi
       exit 1
   fi
   cp $cilfile preprocessed/$cfile
   cp preprocessed/$cfile $cfile
   rm -rf coverage
   rm -rf coverage.path.*
   rm -rf repair.cache
   rm -rf repair.debug.*
   #echo "[INFO] RUNNING CMD:$genprog configuration-$version" 1>&2
   timeout -k 0 $timelimit $genprog configuration-$version &> $rundir/temp-$version-$iteration-$testsuite.out
   timespent=$(grep "TOTAL" "$rundir/temp-$version-$iteration-$testsuite.out" | cut -d'=' -f1 | awk '{print $NF}')
   #echo "[INFO] Time Spent: $timespent" 1>&2
   if [ -z "${timespent}" ]; then
     print_results $version "TIMEOUT" $timelimit
   fi
   if [ ! -f "$rundir/tempworkdir-$version-$iteration-$testsuite/build.log" ]; then
     print_results $version "BUILDFAILED:FILE" $timespent
   elif grep -q "Failed to make" $rundir/tempworkdir-$version-$iteration-$testsuite/build.log; then
     print_results $version "BUILDFAILED" $timespent
   elif  grep -q "nexpected" "$rundir/temp-$version-$iteration-$testsuite.out"; then
     print_results $version "VERIFICATIONFAILED" $timespent
   elif grep -q "Timeout" "$rundir/temp-$version-$iteration-$testsuite.out"; then
     print_results $version "TIMEOUT" $timelimit
   elif grep -q "Repair Found" "$rundir/temp-$version-$iteration-$testsuite.out"; then
     contestnum=$(echo "$version" | cut -d$'-' -f1)
     probnum=$(echo "$version" | cut -d$'-' -f2)
     buggyfile=$(echo "$version" | cut -d$'-' -f4)
     cfile=$(echo "$contestnum-$probnum-$buggyfile".c)
     cfixfile=$(echo "$version-fix".c)
     fixf="$rundir/tempworkdir-$version-$iteration-$testsuite/repair/$cfile"
     #for fixing the asm_booo instruction that GenProg introduced
     sed -i '/booo/d' "$fixf"
     cp $fixf $rootdir/genprog-allfixes/repair-$contestnum-$probnum-$buggyfile-$iteration-$testsuite.c
     validity=$($rootdir/validate-fix-genprog.sh "$version" "$rundir/temp-$version-$iteration-$testsuite.out" "$rundir/tempworkdir-$version-$iteration-$testsuite")
     print_results $version "REPAIR" $timespent $validity
   elif grep -q "no repair" "$rundir/temp-$version-$iteration-$testsuite.out"; then
     print_results $version "NOREPAIR" $timespent
   elif grep -q "Assertion failed" "$rundir/temp-$version-$iteration-$testsuite.out"; then
     print_results $version "COVERAGEFAIL" $timespent
   fi
   echo "[ERROR] No interpretation:" 1>&2
   cat "$rundir/temp-$version-$iteration-$testsuite.out" 1>&2
   print_results $version "????" $timespent
  else
    echo "[INFO] IGNORING:$version" 1>&2
  fi
  #if test -e "$rundir/tempworkdir-$version-$iteration-manual/bugreport.txt";then
  #  echo "BUG"
  #  if grep -q "BOOO" "$rundir/tempworkdir-$version-$iteration-manual/bugreport.txt"; then
  #    printf "%s\tBOOOBUG\n" "$version" >> "$rootdir/genprog-bugs.log"
  #  fi
  #fi
fi
#kill_descendant_processes $$
