# Learn2Fix
Learn2Fix is a human-in-the-loop automatic repair technique for programs that take numeric inputs. Given a test input that reproduces the bug, Learn2Fix uses mutational fuzzing to generate alternative test inputs, and presents some of those to the human to ask whether they also reproduce the bug. Meanwhile, Learn2Fix uses the [Incal](https://github.com/ML-KULeuven/incal) constraint learning tool to construct a Satisfiability Modulo Linear Real Arithmetic SMT(LRA) constraint that is satisfied only by test inputs labeled as reproducing the bug. SMT provides a natural representation of program semantics and is a fundamental building block of symbolic execution and semantic program repair. The learned SMT constraint serves as an automatic bug oracle that can predict the label of new test inputs. Iteratively, the oracle is trained to predict the user’s responses with increasing accuracy. Using the trained oracle, the user can be asked more strategically. The key challenge that Learn2Fix addresses is to maximize the oracle’s accuracy, given only a limited number of queries to the user.

* You can find the technical details in our ICST'20 paper: https://arxiv.org/abs/1912.07758
* To cite our paper, you can use the following bibtex entry:
```bibtex
@inproceedings{learn2fix,
 author = {B\"ohme, Marcel and Geethal, Charaka and Pham, Van-Thuan},
 title = {Human-In-The-Loop Automatic Program Repair},
 booktitle = {Proceedings of the 2020 IEEE International Conference on Software Testing, Verification and Validation},
 series = {ICST 2020},
 year = {2020},
 location = {Porto, Portugal},
 pages = {1-12},
 numpages = {12}
}
```
Learn2Fix is implemented in Python, quickly set up in a Docker container, and uses the following projects:
* Incal constraint learner: [Paper](https://www.ijcai.org/proceedings/2018/0323.pdf), [Tool](https://github.com/ML-KULeuven/incal)
* GenProg test-driven repair: [Paper](https://web.eecs.umich.edu/~weimerw/p/weimer-tse2012-genprog.pdf), [Tool](https://github.com/squareslab/genprog-code)
* CodeFlaws repair benchmark: [Paper](https://codeflaws.github.io/postercameraready.pdf), [Tool](https://codeflaws.github.io/)

# How to run Learn2Fix
To facilitate open science and reproducibility, we make our tool (Learn2Fix), data, and scripts available. Following are the concrete instructions to set up and run Learn2Fix on the Codeflaws benchmark to reproduce the results we reported in our paper.

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
# Install LattE
wget https://github.com/latte-int/latte/releases/download/version_1_7_5/latte-integrale-1.7.5.tar.gz
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

# How to reproduce our results
## Run Learn2Fix on Codeflaws
Run the following command to execute Learn2Fix. Learn2Fix produces several CSV files, one for each experimental run (e.g., results_it_1.csv for the first run)
```bash
cd $learn2fix/notebooks
./experiments.sh /root/codeflaws/all-script/codeflaws 2>learn2fix.log
```
Once the experiment completes, concatenate all CSV files to form a single file containing all results
```bash
cat results_it_*.csv > results_all.csv
```

## Run Plot.Rmd on the files that are produced
See Plot.Rmd and our data under the results folder
```bash
ls $learn2fix/results
```
