#!/bin/bash
#rootdir="/home/ubuntu/codeforces-crawler/CodeforcesSpider" #directory of this script
rootdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )" #directory of this script
rundir=$rootdir/genprog-run # directory in which genprog is called from 
version="$1"
filen="$2"
repairdir="$3"

contestnum=$(echo $version | cut -d$'-' -f1) 
probnum=$(echo $version | cut -d$'-' -f2)
buggyfile=$(echo $version | cut -d$'-' -f4)
cfile=$(echo "$contestnum-$probnum-$buggyfile".c)
cexefile=$(echo "$contestnum-$probnum-$buggyfile")
correctfile=$(echo $version | cut -d$'-' -f5)
goldenfile=$(echo "$contestnum-$probnum-$correctfile".c)

validdir=$repairdir-validation

runalltest(){
         i="$1"
         origversion="$2"
         goldenpass="$3"
         filen=$validdir/test-valid.sh
	 passt=0
	 failt=0
	 totalt=0
	 alltests=($(grep -E "p[0-9]+\)" $filen | cut -d')' -f 1))
	 for t in "${alltests[@]}"
	 do
	     timeout -k 2s 2s $filen "$t"&>/dev/null
	     if [ $? -ne 0 ]; then
		failt=$((failt+1))
	     else
		passt=$((passt+1))
	     fi
	     totalt=$((totalt+1))
	 done
         if [ ! -z "$goldenpass" ]; then
           echo "$passt,$goldenpass,$totalt"
         else
           echo $passt
         fi
         #pkill $cexefile
         #pkill test-valid.sh
}


if grep -q "Repair Found" $filen; then
   fixf="$repairdir/repair/$cfile"
   cp -r $repairdir $validdir
   cd $validdir
   cp $validdir/preprocessed/$cfile $cfile  
   make clean &>/dev/null
   make CFLAGS="-std=c99 -fno-optimize-sibling-calls -fno-strict-aliasing -fno-asm" &> /dev/null
   runalltest "orig-$cfile" "$version" "" > /dev/null
   cp "$cfile" "$cfile.orig"
   #copy and compile the fix file before running validation tests 
   cp $goldenfile $cfile
   make clean &> /dev/null
   make CFLAGS="-std=c99 -fno-optimize-sibling-calls -fno-strict-aliasing -fno-asm" &> /dev/null

  
   goldenpasst=$(runalltest "golden-$goldenfile" "$version" "")
   #echo "GOLDEN:$goldenpasst"

   cp $fixf $cfile
   make clean &> /dev/null
   make CFLAGS="-std=c99 -fno-optimize-sibling-calls -fno-strict-aliasing -fno-asm" &> /dev/null

   runalltest "fix-$cfile" "$version" "$goldenpasst"
   
  #restore the file
  cp "$cfile.orig" "$cfile" 
  #rm -rf "$repairdir"
fi
