"""
HTTP client for fetching drought monitor data.
Uses synchronous requests since geopandas operations are synchronous.
"""
import logging
import requests
import zipfile
import io
import os
import tempfile
import geopandas as gpd
from app.config import settings

logger = logging.getLogger(__name__)


class DroughtClient:
	"""Client for fetching drought monitor data from various sources."""

	@staticmethod
	def fetch_current_drought_geojson() -> gpd.GeoDataFrame:
		"""
		Fetch the current drought map from the GeoJSON endpoint.
		
		Returns:
			GeoDataFrame with current drought polygons
		"""
		url = settings.most_recent_drought_information_full_url
		logger.info(f"Fetching current drought data from: {url}")
		
		response = requests.get(url)
		response.raise_for_status()
		
		# Read GeoJSON into GeoDataFrame
		gdf = gpd.read_file(io.BytesIO(response.content))
		gdf['geometry'] = gdf.geometry.make_valid()
		return gdf

	@staticmethod
	def fetch_previous_week_drought_shapefile(date_str: str) -> gpd.GeoDataFrame:
		"""
		Downloads the UNL Drought Monitor Shapefile for a specific date
		and returns a GeoDataFrame.
		
		Args:
			date_str (str): Date in 'YYYYMMDD' format (e.g., '20251202')
		
		Returns:
			GeoDataFrame with drought polygons
		
		Raises:
			Exception: If data not found or extraction fails
		"""
		base_url = settings.last_weeks_drought_information_base_url.rstrip('/')
		url = f"{base_url}/data/shapefiles_m/USDM_{date_str}_M.zip"
		logger.info(f"Downloading drought data from: {url}")
		
		response = requests.get(url)
		if response.status_code == 404:
			raise Exception(f"Data not found for date {date_str}. Ensure it is a Tuesday.")
		
		response.raise_for_status()
		
		# Use a Temporary Directory to handle the file extraction safely
		with tempfile.TemporaryDirectory() as tmp_dir:
			# Extract the Zip contents
			with zipfile.ZipFile(io.BytesIO(response.content)) as z:
				z.extractall(tmp_dir)
			
			# Find the .shp file dynamically
			shapefiles = [f for f in os.listdir(tmp_dir) if f.endswith('.shp')]
			
			if not shapefiles:
				raise Exception("No .shp file found in the downloaded zip archive.")
			
			shp_path = os.path.join(tmp_dir, shapefiles[0])
			
			# Read into GeoPandas
			gdf = gpd.read_file(shp_path)
			gdf['geometry'] = gdf.geometry.make_valid()
		return gdf

