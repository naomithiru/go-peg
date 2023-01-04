This repository contains all the working code, files and notebooks used to develop the [GO-PEG Tracing Usecase project](https://github.com/gopeg/feedback/issues/24).

The project uses [python]() to preprocess the data, and [Hale Studio](https://github.com/halestudio/hale) to harmonize it. Finally, the data can be used on the [Graph Tracing Engine](https://github.com/VlaamseMilieumaatschappij/BE-GOOD---Graph-Tracing-Engine) for the tracing action.


## Preprocessing

This application is designed to take in data, process it, and return an output. It is built with python and utilizes Geospatial libraries.

To get started with this application, you will need to do the following:

Clone or download the repository onto a local machine.

To run the preprocessing code, use a conda environment.
Install [Miniconda](https://docs.conda.io/en/latest/miniconda.html) or [Anaconda](https://docs.anaconda.com/anaconda/install/windows/) in your Windows, Linux or macOS.

Then, create a conda environment from the environment.yml file

  ```conda env create -f environment.yml```


Use the sample data directory for the source data.

Run the app using the command python main.py

View the output of the processed data in the harmonized data folder.

## Harmonization
To harmonize the data, use the files in the schema directory. An alignment project can begin from opening a hale file, which has Codelist Properties and Dataset Default Properties prefilled.  

The .align files can be used to load existing mappings.

Any necessary changes to suit your project can be made to your local copy of these files.

Further instructions can be found in the documentation folder.

### Documentation
For more information on how to use this application, please refer to the documentation folder in the repository. Here, you will find detailed instructions on how to input and manipulate data, as well as troubleshooting tips in case you encounter any issues.

### Contributions
If you would like to contribute to the development of this application, please feel free to create a pull request with your proposed changes. All contributions are welcome and appreciated!

### Support
If you need help using this application or have any questions, please don't hesitate to reach out. You can find contact information in the CONTRIBUTORS.md file. We are happy to assist you in any way we can.
