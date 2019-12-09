#!/bin/bash

SUBJECT=$1
ITERATION=$2
GENLOG=$3

genprog_fpass=0
genprog_gpass=0
genprog_total=0
incal_fpass=0
incal_gpass=0
incal_total=0

for result in $(cat $GENLOG | grep "$SUBJECT"); do
  tool=$(echo $result | cut -d, -f2)
  iteration=$(echo $result | cut -d, -f3)
  if [ "$iteration" != "$ITERATION" ]; then continue; fi
  success=$(echo $result | cut -d, -f4)
  rtime=$(echo $result | cut -d, -f5)
  if [ "$success" == "YES" ]; then
    if [ "$tool" == "GenProg" ]; then
      genprog_fpass=$(echo $result | cut -d, -f7)
      genprog_gpass=$(echo $result | cut -d, -f8)
      genprog_total=$(echo $result | cut -d, -f9)
    fi
    if [ "$tool" == "GenProg-Incal" ]; then
      incal_fpass=$(echo $result | cut -d, -f7)
      incal_gpass=$(echo $result | cut -d, -f8)
      incal_total=$(echo $result | cut -d, -f9)
    fi
  fi
done

total=$(( genprog_total > incal_total ? genprog_total : incal_total ))
echo ,$genprog_fpass,$genprog_gpass,$incal_fpass,$incal_gpass,$total
