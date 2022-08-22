from googleapiclient.discovery import build
from google.oauth2 import service_account
import pandas as pd
import numpy as np
import bs4 as bs
from bs4 import BeautifulSoup
import requests
import re
import math

# This is a dictionary with key = name of the app and value = url of the app on sasi
apps_to_track = {'DISCOS': 'https://sasi.unionworks.co.uk/app/discos-smart-bogo-cart-upsell', 'All In One Automatic Discounts': 'https://sasi.unionworks.co.uk/app/all-in-one-automatic-discounts', 'Free gifts BOGO buy x get y': 'https://sasi.unionworks.co.uk/app/freegifts',
                 'Quantity Breaks & Discounts': 'https://sasi.unionworks.co.uk/app/pricing-by-quantity', 'Discounted Bundle Upsell, BOGO': 'https://sasi.unionworks.co.uk/app/upsellify-pro', 'VolumeBoost - Volume Discount': 'https://sasi.unionworks.co.uk/app/volume-discount-by-hulkapps'}

# This function accept an url and create a soup


def initiate_soup(url):
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html.parser")
    return soup

# This function finds information in the soup and create a DataFrame


def get_info(soup, app_name):
    first_columns_info = list()
    second_columns_info = list()
    third_columns_info = list()
    table_info = soup.findAll('table')[0].findAll('tr')
    # Find all informations in the first table on SASI website including (Category Positions and which pages the app is on for that category)
    for row in table_info:
        try:
            first_column = row.findAll('td')[0].findAll(
                'a')[0].contents[0] + ' -> ' + row.findAll('td')[0].findAll('a')[1].contents[0]
        except IndexError:
            first_column = row.findAll('td')[0].findAll('a')[0].contents[0]
        second_column = row.findAll('td')[1].contents[0].strip()
        third_column = row.findAll('td')[2].find('span').contents[0]
        first_columns_info.append(first_column)
        second_columns_info.append(second_column)
        third_columns_info.append(third_column)
    today = str(pd.to_datetime('today')).split(' ')[0]
    df = pd.DataFrame(data={'Date': today, 'App': app_name, 'Category': first_columns_info,
                      'Category Positions': second_columns_info, 'Page': third_columns_info})
    # Find rating of the app
    rating = soup.find('span', {'class': 'stars'}).contents[1].strip()
    # Find review of the app
    review = re.findall(r'\b\d+\b', soup.find('p',
                        attrs={'class': None}).contents[2].replace(',', ''))[0]
    # Create rating and reviews column
    df['Rating'] = rating
    df['Reviews'] = review
    return df


# In this part we'll create an empty DataFrame
df = pd.DataFrame()
# Then we'll loop through the dictionary defined at the top of the script, initiate the soup, create a dataframe (temp_df) then concat it to the empty DataFrame
for app in apps_to_track:
    soup = initiate_soup(apps_to_track[app])
    temp_df = get_info(soup, app)
    df = pd.concat([df, temp_df], axis=0, ignore_index=True)


df['Category Apps Count'] = df['Category Positions'].apply(
    lambda x: x.split('/')[1].strip())
df['Category Positions'] = df['Category Positions'].apply(
    lambda x: x.split('/')[0].strip())
df = df[['Date', 'App', 'Category', 'Category Positions',
         'Category Apps Count', 'Page', 'Rating', 'Reviews']]

# Create data to write to spreadsheet
data = []

for i in df.to_numpy():
    data.append(list(i))

# Write to googlesheet
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = 'keys.json'

credentials = None
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)

# The ID and range of the SDU_rank_tracking spreadsheet
SPREADSHEET_ID = '140o7843BrmErT4nKDaiRCmnarTQtveBbd84HBMBJMFs'
RANGE = 'Category Tracking Raw Data!A:F'
service = build('sheets', 'v4', credentials=credentials)

# Call the Sheets API
sheet = service.spreadsheets()

# Deciding range (we'll find how many rows the sheet is currently have then append to the next row)
result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE).execute()
value = result.get('values', [])
rows = len(value) + 1
RANGE2 = 'Category Tracking Raw Data!A{}'.format(rows)

# Write to the spreadsheet
sheet.values().update(spreadsheetId=SPREADSHEET_ID,
                      range=RANGE2,
                      valueInputOption="USER_ENTERED",
                      body={"values": data}).execute()
