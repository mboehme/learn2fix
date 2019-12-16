# Learn2Fix

To facilitate open science and reproducibility, we make our tool (Learn2Fix), data, and scripts available. Following are the concrete instructions to set up and run Learn2Fix on the Codeflaws benchmark to reproduce the results we reported in our paper.

# Installation
## Step-1. Install Codeflaws with GenProg

Set up a docker container for GenProg repair tool
```bash
docker pull squareslab/genprog
docker run -it squareslab/genprog /bin/bash
```

Download and set up any dependencies
```bash
apt-get update
apt-get -y install git time build-essential zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev wget z3 bc

# Install python
pushd /tmp
wget https://www.python.org/ftp/python/3.7.2/Python-3.7.2.tar.xz
tar -xf Python-3.7.2.tar.xz
cd Python-3.7.2
./configure --enable-optimizations
make -j4
make altinstall
ln -s $(which pip3.7) /usr/bin/pip
mv /usr/bin/python /usr/bin/python.old
ln -s $(which python3.7) /usr/bin/python
popd
```

Download and set up the Codeflaws benchmark inside the container
```bash
cd /root
git clone https://github.com/codeflaws/codeflaws
cd codeflaws/all-script
wget http://www.comp.nus.edu.sg/~release/codeflaws/codeflaws.tar.gz
tar -zxf codeflaws.tar.gz
```

## Step-2. Install Learn2Fix
Download and compile Learn2Fix and its dependencies (e.g., INCAL)
```bash
cd /root/codeflaws/all-script
git clone https://github.com/mboehme/learn2fix
export learn2fix="$PWD/learn2fix"
cd $learn2fix
rm -rf latte-integrale-1.7.5
tar -xvzf latte-integrale-1.7.5.tar.gz
cd latte-integrale-1.7.5
./configure
make -j4
make install
# Install Incal
cd $learn2fix
python setup.py build
python setup.py install
pip install cvxopt
pip install plotting
pip install seaborn
pip install wmipa
pip install pywmi
pysmt-install --z3 #confirm with [Y]es
```

Export environment variables
```bash
cd $learn2fix
export PATH=/root/.opam/system/bin/:$PATH
export PATH=$PATH:$PWD/latte-integrale-1.7.5/dest/bin/
cd $learn2fix/notebooks
export PYTHONPATH=$PWD/../incal/experiments
export PYTHONPATH=$PYTHONPATH:$PWD/../incal/extras
export PYTHONPATH=$PYTHONPATH:$PWD/../incal
```

# Run Learn2Fix on Codeflaws
Run the following command to execute Learn2Fix. Learn2Fix produces several CSV files, one for each experimental run (e.g., results_it_1.csv for the first run)
```bash
cd $learn2fix/notebooks
./experiments.sh /root/codeflaws/all-script/codeflaws 2>learn2fix.log
```
Once the experiment completes, concatenate all CSV files to form a single file containing all results
```bash
cat results_it_*.csv > results_all.csv
```
