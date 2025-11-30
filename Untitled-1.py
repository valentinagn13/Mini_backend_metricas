#!/usr/bin/env python

# make sure to install these packages before running:
# pip install pandas
# pip install sodapy

import pandas as pd
from sodapy import Socrata

client = Socrata("www.datos.gov.co",
                  "sAmoC9S1twqLnpX9YUmmSTqgp",
                  username="valen@yopmail.com",
                  password="p4wHD7Y.SDGiQmP")
results = client.get("uzcf-b9dh", limit=100000)

# Convert to pandas DataFrame
results_df = pd.DataFrame.from_records(results)

print(results_df)