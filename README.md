# colberto
Modules and code related to Colbert experiment
# Setup
In order to run Colberto, you need to make sure you follow the steps in this section.
## Setup your Python environnement
Colberto is still in development. You need to configure your python environment to execute the code. If you only want to execute the latest stable version of the code, perform these steps for the main branch.
1. Install [miniconda](https://docs.anaconda.com/free/miniconda/miniconda-install/) or [Anaconda](https://docs.anaconda.com/free/anaconda/install/) environnement managers
2. Create a virtual environnement for the Colberto project using `conda create -n colberto_mybranch` or the Anaconda GUI interface and active it `conda activate colberto_mybranch`
3. Navigate to the dependencies folder and update the virtual environnement using `conda install --yes --file requirements.txt`. Conda will install the packages required for the current branch. You might need to run `conda config --add channels conda-forge` and `conda config --set channel_priority strict` to add a channel where some pacakge are available.
4. You can then locate your environnement using which `which python` in Linux or `where python` in Windows and import it into your IDE (e.g. VCode with Python pluggin)
## Configuration files
Many configurations files like manufacturer provided text files, binary driver librairies, databases etc... must be provided or built in order for Colberto to operate correctly. Make sure to carefully set up each of them.
### Database
Colberto uses the `Databroker` [database management module](https://blueskyproject.io/databroker/index.html) that is part of BlueSky to save every data and metadata taken with the instrument.
- If this is the first time setting up Colbert, you will have to place a databroker configuration file in one of the search paths of `databroker` (the actual filename is irrelevant). This search path can be obtained by running `import databroker; print(databroker.catalog_search_path())` in python or by consulting the Error message produced when calling `setup()` from the `runtime` module. An example of the configuration file can be found in `samples/engine/example_databroker_configuration.yml`.
- Replace the `CATALOG_NAME` placeholder for the desired database name and `DESTINATION_DIRECTORY` by the desired location of the database. Consult this page for more information on [database mangement](https://blueskyproject.io/databroker/how-to/file-backed-catalog.html) in BlueSky.



## Setting up your Python environnement
See the instructions to this end in the Setup section.
## Updating python environnement

When developping new features in your branch, it is very likely that you will need to add python packages. You can do this using `conda install packagename`. You will then need to update the required package list by naviguating to /dependencies/ and using the command `conda list -e > requirements.txt`. This will dump your current package list into the file so that the packages will be appended to the project requirements. Don't forget to add requirements.txt to your commit.

## Naming Conventions
In this project, we follow standard Python naming conventions to ensure that our code is readable and consistent. Below are the guidelines for naming functions and classes:

### Classes
Classes are named using the CamelCase convention. This means that each word within the class name starts with a capital letter and there are no underscores between words. This helps in distinguishing class names from function and variable names.

Examples:
ImageGenerator
EmployeeRecord

### Functions and Methods
Functions and methods are named using the snake_case convention. This means that all letters are in lowercase and words are separated by underscores. This makes function and method names easy to read and understand.

Examples:
get_depth()
write_image()
send_email()