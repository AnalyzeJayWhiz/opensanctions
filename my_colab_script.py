# -*- coding: utf-8 -*-
"""zavod.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1A5tcTUm0CykFeigcfsGIpaCrXxigPTMO
"""

import os
import subprocess
import sys

import os
import sys
import subprocess

# Define the folder where the data will be stored (relative to the GitHub Actions environment)
drive_folder = '/home/runner/work/opensanctions'  # Adjust this based on your repo structure
os.makedirs(drive_folder, exist_ok=True)

# Change working directory to the folder where the data will be stored
os.chdir(drive_folder)

# Install system dependencies (without sudo in GitHub Actions)
subprocess.run(['apt-get', 'update'], check=True)
subprocess.run(['apt-get', 'install', '-y', 'libicu-dev', 'libsnappy-dev', 'build-essential'], check=True)

# Install required Python packages
subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyicu', 'plyvel', 'xlrd', 'normality', 'zavod', 'rigour', 'nomenklatura'], check=True)

# Install OpenSanctions and other dependencies
subprocess.run([sys.executable, '-m', 'pip', 'install', '-e', './zavod[dev]'], check=True)

# Disable default user config for Pywikibot
os.environ['PYWIKIBOT_NO_USER_CONFIG'] = '1'

# Set the user-config.py path for Pywikibot
user_config_path = os.path.join(drive_folder, 'user-config.py')
with open(user_config_path, 'w') as f:
    f.write("mylang = 'en'\nfamily = 'wikipedia'")

# Set the PYWIKIBOT_DIR to the cloned OpenSanctions directory
os.environ['PYWIKIBOT_DIR'] = os.path.join(drive_folder, 'opensanctions')

# Install requirements for the OpenSanctions repo (for any extra dependencies you might need)
requirements_path = os.path.join(drive_folder, 'opensanctions', 'contrib', 'delta', 'requirements.txt')
subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', requirements_path], check=True)

# Run zavod crawl (make sure the dataset path is correct and relative to the repo structure)
dataset_path = os.path.join(drive_folder, 'opensanctions', 'datasets', 'ae', 'local_terrorists', 'ae_local_terrorists.yml')
subprocess.run(['zavod', 'crawl', dataset_path], check=True)

# Set the ZAVOD_RESOLVER_PATH to the correct location in the OpenSanctions repo
os.environ['ZAVOD_RESOLVER_PATH'] = os.path.join(drive_folder, 'opensanctions', 'zavod', 'zavod', 'resolver')

# Run zavod export with the correct path for GitHub Actions
export_path = os.path.join(drive_folder, 'analysis')  # Adjust this based on your repo structure
subprocess.run(['zavod', 'export', export_path], check=True)
