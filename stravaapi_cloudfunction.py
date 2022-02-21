import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import pandas as pd
from pandas.io.json import json_normalize
from datetime import datetime
import gspread
import df2gspread
from df2gspread import df2gspread as d2g
from oauth2client.service_account import ServiceAccountCredentials

def stravaapi():

	# credentials and urls for strava api
	auth_url = "https://www.strava.com/oauth/token"
	activities_url = "https://www.strava.com/api/v3/athlete/activities"

	payload = {
		'client_id': "75921",
		'client_secret': 'e4136ccfc4728161dd3d3923e8bcba413239c7af',
		'refresh_token': 'a11b0d62b35d73a413f9fb1b1def015b4e0b6046',
		'grant_type': "refresh_token",
		'f': 'json'
	}

	# scope and credentials for uploading to google sheets
	scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
	spreadsheet_key = '1bBSRKEOt_pPgomgLxeHUeooXEhItAIws8DZ5xC19hnw'
	jsonfilename = 'jsonFileFromGoogle.json'

	res = requests.post(auth_url, data=payload, verify=False)
	access_token = res.json()['access_token']
	header = {'Authorization': 'Bearer ' + access_token}
	full_dataset = []
	i = 1
	while i > 0:
		param = {'per_page': 200, 'page': i}
		dataset = requests.get(activities_url, headers=header, params=param).json()
		if len(dataset) == 0:
			break
		else:
			full_dataset = full_dataset + dataset
			i = i+1
	print("Called API")
	
	activities = json_normalize(full_dataset)
	df = pd.DataFrame(activities)
	print("Created df")
	
	df1 = df[['start_date','distance','moving_time','elapsed_time','total_elevation_gain']]

	df1['miles'] = df1['distance'].apply(lambda x: x * 0.000621371)
	df1['date'] = df1['start_date'].apply(lambda x: x[0:10])
	df1['moving_time_min'] = df1['moving_time'].apply(lambda x: x/60)
	df1['elapsed_time_min'] = df1['elapsed_time'].apply(lambda x: x/60)
	df1['total_elevation_feet'] = df1['total_elevation_gain'].apply(lambda x: x * 3.28084)
	
	df1 = df1.groupby(by=["date"]).sum().reset_index()
	print("Created df1")
	
	df2 = df[['start_date','average_heartrate','average_cadence']]
	df2['date'] = df2['start_date'].apply(lambda x: x[0:10])
	df2['average_cadence_min'] = df2['average_cadence'].apply(lambda x: 2 * x)
	df2 = df2.groupby(by=['date']).mean().reset_index()
	print("Created df2")
	
	datelist = pd.date_range(end = datetime.today(), periods=730).tolist()
	date_dict = {'date': []}
	for i in datelist:
		date_dict['date'].append(i)
	date_df = pd.DataFrame(date_dict)
	date_df['date'] = date_df['date'].apply(lambda x: str(x)[0:10])
	print("Created date_df")
	
	df3 = pd.merge(df1, df2, how="inner", left_on=['date'], right_on=['date'])
	df3 = pd.merge(df3, date_df, how="right", left_on=['date'], right_on=['date'])
	df3 = df3.fillna(0)
	print("Created df3")
	
	credentials = ServiceAccountCredentials.from_json_keyfile_name(jsonfilename, scope)
	gc = gspread.authorize(credentials)
	wks_name = 'Sheet1'
	d2g.upload(df3, spreadsheet_key, wks_name, credentials=credentials, row_names=True)
	print("Loaded to Google Sheets")

if __name__ == "__main__":
	stravaapi()