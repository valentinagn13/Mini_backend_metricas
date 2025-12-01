#!/usr/bin/env python

# make sure to install these packages before running:
# pip install pandas
# pip install sodapy
# pip install python-dotenv

import os
import pandas as pd
from sodapy import Socrata
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SOCRATA_DOMAIN = os.getenv("SOCRATA_DOMAIN", "www.datos.gov.co")
SOCRATA_API_KEY = os.getenv("SOCRATA_API_KEY", "")
SOCRATA_USERNAME = os.getenv("SOCRATA_USERNAME", "")
SOCRATA_PASSWORD = os.getenv("SOCRATA_PASSWORD", "")

client = Socrata(SOCRATA_DOMAIN,
                  SOCRATA_API_KEY,
                  username=SOCRATA_USERNAME,
                  password=SOCRATA_PASSWORD)
results = client.get("uzcf-b9dh", limit=100000)

# Convert to pandas DataFrame
results_df = pd.DataFrame.from_records(results)

print(results_df)