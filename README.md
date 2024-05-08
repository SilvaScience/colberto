# colberto
Modules and code related to Colbert experiment
# Contributing
## Setting up your Python environnement
1. Install [miniconda](https://docs.anaconda.com/free/miniconda/miniconda-install/) or [Anaconda](https://docs.anaconda.com/free/anaconda/install/) environnement managers
2. Create a virtual environnement for the Colberto project using `conda create -n colberto_mybranch` or the Anaconda GUI interface and active it `conda activate colberto_mybranch`
3. Navigate to the dependencies folder and update the virtual environnement using `conda install --yes --file requirements.txt`. Conda will install the packages required for the current branch.
4. You can then locate your environnement using which `which python` in Linux or `where python` in Windows and import it into your IDE (e.g. VCode with Python pluggin)
## Updating python environnement

When developping new features in your branch, it is very likely that you will need to add python packages. You can do this using `conda install packagename`. You will then need to update the required package list by naviguating to /dependencies/ and using the command `conda list -e > requirements.txt`. This will dump your current package list into the file so that the packages will be appended to the project requirements. Don't forget to add requirements.txt to your commit.
