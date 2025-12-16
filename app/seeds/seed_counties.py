import sys
from pathlib import Path

# Add project root to Python path so we can import from app
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import logging
from typing import List
import pandas as pd
import requests
import zipfile
import io

from app.schemas.counties import County
from app.schemas.location import Coordinate, Location
from app.state import State
from app.redis_client import quantagent_redis
from app.logging_config import setup_logging

# Setup logging
setup_logging(level="INFO")
logger = logging.getLogger(__name__)

def get_official_county_data():
	# 1. The Official Census Bureau URL (2025 Data)
	url = "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2025_Gazetteer/2025_Gaz_counties_national.zip"
	
	logger.info(f"Downloading from {url}...")
	response = requests.get(url)
	
	# 2. Extract the txt file from the zip in memory
	with zipfile.ZipFile(io.BytesIO(response.content)) as z:
		# The file inside has a predictable name, usually ending in .txt
		file_name = [name for name in z.namelist() if name.endswith('.txt')][0]
		with z.open(file_name) as f:
			# 3. Load into Pandas
			# The Census file is Pipe-Separated (delimiter='|') and has trailing whitespace
			df = pd.read_csv(f, sep='|', dtype={'GEOID': str})
	
	# 4. Clean up column names (strip whitespace)
	df.columns = [c.strip() for c in df.columns]
	logger.info(f"Cleaned up column names: {df.columns}")

	# 5. Rename to match your schema
	# GEOID is the full 5-digit FIPS (State+County)
	# INTPTLAT/LONG are the centroids
	df_clean = df[['GEOID', 'USPS', 'NAME', 'INTPTLAT', 'INTPTLONG']].copy()
	df_clean.columns = ['fips_code', 'state', 'county_name', 'latitude', 'longitude']
	
	return df_clean

def transform_county_data(df: pd.DataFrame) -> List[County]:
	counties = []
	for index, row in df.iterrows():
		counties.append(County(
			fips=row['fips_code'],
			state_abbr=row['state'],
			state_fips=Location.get_state_fips(row['state']),
			name=row['county_name'],
			centroid=Coordinate(latitude=row['latitude'], longitude=row['longitude'])))
	return counties

def load_counties_to_redis(counties: List[County]):
	for county in counties:
		quantagent_redis.create(f"{State.REDIS_COUNTY_KEY_PREFIX}{county.fips}", county.to_redis_json())

if __name__ == "__main__":
	logger.info("Seeding counties...")
	# Run it
	df_counties = get_official_county_data()
	logger.info(f"Loaded {len(df_counties)} counties from the Census Bureau")
	counties = transform_county_data(df_counties)
	logger.info(f"Transformed {len(counties)} counties")
	load_counties_to_redis(counties)
	logger.info(f"Successfully loaded {len(counties)} counties to Redis")

