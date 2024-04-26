Azure Resource Manager Template Reference Docset Generator
=======================

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue)](https://www.linkedin.com/in/miladbeigi/)
[![GitHub](https://img.shields.io/badge/GitHub-Follow-lightgrey)](https://github.com/your-github-username)

This project is a Python script that generates a Dash docset for Azure Resource Manager (ARM) template reference documentation. The script downloads the ARM template reference documentation from the Azure Docs website and generates a Dash docset that can be used in the Dash.

## Prerequisites
- Python 3.10.9 or later

## Installation
1. Clone the repository:
    ```bash
    git clone https://github.com/miladbeigi/azure-arm-docset-gen.git
    ```
2. Run the following command to install the required Python packages and save the HTML files:
    ```bash
    make install
    ```
3. Run the following command to generate the docset:
    ```bash
    make build
    ```