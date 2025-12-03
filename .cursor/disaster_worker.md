Your job is to now create a background worker called `disaster_polling_agent` using CeleryBeat & CrewAI. The worker should run every 5 minutes.

 The ultimate goal of this worker (and crew) is to be able to identify and classify metadata gathered from the nws to our internal system. The NWS uses WATCHES and WARNINGS. For our system, we translate WATCHES = EPISODES , WARNINGS = EVENTS. As such, all responses gathered from the nws api must be classified into four groups: "new_events" , "updated_events", "new_episodes", "updated_episodes". Depending upon the classification, the worker will handoff the work to endpoints in an associated controller. You can reference the controllers we made earlier to determine the exact endpoint definitions. To create unique keys for both events and episodes, we use the following pattern from the VTEC  "Office + Phnenomena + Significance + ETN + Year". 


This is where crewAI comes into play. We want to be able to create a crew which will handle most of the responsibility listed below: 

- We can have a single agent crew. The agent can be called "disaster_spotter". Come up with the role, goal, and backstory for this agent.
    - Here is the documentation for the crew https://docs.crewai.com/en/concepts/crews in case you need to reference it. 
    - The model we will use should be gemini-3, we should have the following configs added to config.py
        - GEMINI_MODEL=gemini/gemini-3-pro-preview
        - GEMINI_API_KEY=test

The architecture for crews should be the following, think of a directory structure like: "crews/{crew_name}/{all_files_listed_below}": 
- Each crew must have an executor, think of this is a wrapper class which actually kicks off the crew.
    - The executor classes must have the ability to be retried N times (set to 5 by default, this should be a config value), and gracefully handle exceptions. If the executor exhausts all retries, then create a custom exception we will raise (using the pattern thats already established in the repo) to signify we failed and log accordingly.  
        - The executor can have a base class, and we can inherit for specific instances. This will be our first use of the executor. Something like "disaster polling executor". 
- agent definition yaml file
- task definition yaml file 
- the crew .py file itself

Please note the episode model needs `episode_key: string` added. 

## The first task within the crew should do the following: 

- [] It should poll the NWS API active endpoint https://api.weather.gov/alerts/active (hint, use the http client pattern you made in earlier steps),
	- [] Should be made as a custom tool in crewAI (see example below. Its for a different API, but to be used as a pattern to familairize with custom crew ai tools)
	- [] When interacting with the NWS, this worker should use the  _last disaster poll time_ (contained in the state object) and add the header `If-Modified-Since` to find everything _after_ that date. If no date is available, get all active warnings and watches. Note the NWS API could return 304 if nothing new is found.
	- [] Ensure we add the user agent header we mentioned earlier.

EXAMPLE TOOL:
```
from typing import Type
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from utils.consts import EODHD_API_KEY
from eodhd import APIClient

class EodHdInput(BaseModel):
	to_date: str = Field(description="End date in YYYY-MM-DD format")
	from_date: str = Field(description="Start date in YYYY-MM-DD format")
	ticker: str = Field(description="Ticker symbol")

class EodHdTool(BaseTool):
	name: str = "EodHdTool"
	description: str = "Use this tool to query EODHD API for sentiment scores and news data"
	args_schema: Type[BaseModel] = EodHdInput

	def _run(self, to_date: str, from_date: str, ticker: str) -> str:
		"""
		Query the EODHD sentiment endpoint for the given tickers and date range.
		"""
		if not EODHD_API_KEY:
			return "Error: EODHD_API_KEY not configured"
		
		if not ticker:
			return "Error: Ticker not provided"

		if not from_date:
			return "Error: From date not provided"

		if not to_date:
			return "Error: To date not provided"
		
		client = APIClient(api_key=EODHD_API_KEY)
		sentiment_data = client.get_sentiment(ticker, from_date, to_date)

		return str(sentiment_data)
```

- [] When querying, we should filter by the following:
	- [] `Severity = Extreme OR Severe`, `Urgency = Immediate OR Expected`, `Certainy = Observed OR Likely`, `Status = actual`
- [] The list below are the following event types the poller should match on: 
	Blizzard Warning BZW
	Extreme Wind Warning EWW
	Coastal Flood Warning CFW
	Dust Storm Warning DSW
	Flash Flood Warning FFW
	Flood Warning FLW
	High Wind Warning HWW
	Hurricane Warning HUW
	Severe thunderstorm warning SVR
	Special Marine Warning SMW
	Storm Surge Warning SSW
	Tornado Warning TOR
	Tsunami Warning TSW
	Tropical Storm Warning TRW
	Winter Storm Warning WSW
	Avalanche Warning AVW
	Fire Warning FRW
	Earthquake Warning EQW
	Volcano Warning VOW

## The second task in the crew should do the following

- [] For each result, construct a custom key which makes the watch or warning unique: Office + Phnenomena + Significance + ETN + Year
	- The VTEC is used for this, we must make a key which is Office + Phnenomena + Significance + ETN + Year 
	- Use your knowledge of VTECs to build this key
	These groups represent an action that must be taken with the event or episode data. This is the crossover from the agentic-based poller to the API we are building.

## The third task in the crew should do the following: 
- [] The agent is asked to verify its own key-creation results. To ensure that quality standards are indeed met and that the KEY created by the system matches our expected structure to determine uniqueness. We want the agent to be accurate, and this is how we account for hallucinations.

## The fourth task in the crew should be
- [] Once the keys are made, we would then reference what keys we have in our `active_events` and/or `active_episodes` state object, depending upon what is found, we can separate the events into the update event / create event / update episode / create episode groups. 
	- [] The agent can access the metadata by using another custom tool. This tool can be called "get_active_episodes_and_events_tool". It should be able to access the state object we made and grab the metadata accordingly. The agent can then call this tool as a task in the crew.
    - [] For identifying an update to either an existing EVENT OR EPISODE, cross reference all keys we received from API with the keys of all active events and active episodes. Use your knowledge of the NWS API metadata (i.e., we get a CON, CANCEL, EXP message) where a key exists in our system, we know we are talking about that event/episode and can update metadata accordingly. 
        - If a new event is found to be associated to an active episode, the event goes to the create bucket and the episode goes to the update bucket
        - If a new event is found to NOT be associated to an active episode, the event goes to the create bucket and we need to create an episode to account for this.
            - If the event cannot find an episode to be linked to via geo-mapping (see note* below), then we should create an episode with the event metadata
        - If a new episode is found, we need to create a new episode from it.
        - If an existing event is updated AND its a location update, we need to update the event AND episode. 
        - If an existing event is updated AND its not a location update, we need to update the event only
        - If an existing episode is updated, we need to update the episode only 
    
Note* about connecting events to episodes
	- [] As new events (warnings) continually come in, We need a way to detect if they are associated with an episode. This is crucuial, vital, and critical to our business logic. Using your knowledge of how the NWS structures its metadata in the responses, and using this hint: to determine if an event belongs to an episode, we should map the repoorted "affected_zone" polygon (the "location" information in our custom model) and compare it with all locations for an active episode.
    Then if ANY part is overlapping, we can assume the event and episode are linked successfully. Otherwise, we do not have the episode and we must make both an event and an episode. Use your knowledge of UGC codes to map out where the polygon actually is, obtain any shape files necessary to accomplish this task.
	- [] Thus, we will need this as a tool for the agent as well. The tool can be called "get forecast zone." The tool can function the following way: parse the NWS response geocode.affected_zones, then call the API endpoints, and grab the geometry.polygon.coordinates to map out an affected area. 
    - [] We can then reference our own internal location.shape field (which will have the coordinate array in it) and compare to see if there is overlap

		Example:                     response.affected_zones: "https://api.weather.gov/zones/forecast/PKZ413" , then we call the API response, which yields response 
		```
		{
    "@context": {
        "@version": "1.1"
    },
    "id": "https://api.weather.gov/zones/forecast/PKZ413",
    "type": "Feature",
    "geometry": {
        "type": "Polygon",
        "coordinates": [
            [
                [
                    -177.9968616,
                    53.095572
                ],
                [
                    -179.9999434,
                    53.2009532
                ],
                [
                    -180,
                    56.0445412
                ],
                [
                    -170.9990433,
                    56.0445412
                ],
                [
                    -170.9990433,
                    53.9502396
                ],
                [
                    -171.9999997,
                    53.7000005
                ],
                [
                    -173.4500702,
                    53.6312028
                ],
                [
                    -173.9999997,
                    53.6000005
                ],
                [
                    -175.9999997,
                    53.3000005
                ],
                [
                    -177.9968616,
                    53.095572
                ]
            ]
        ]
    },
    "properties": {
        "@id": "https://api.weather.gov/zones/forecast/PKZ413",
        "@type": "wx:Zone",
        "id": "PKZ413",
        "type": "offshore",
        "name": "Bering Sea Offshore 171W to 180 and South of 56N",
        "effectiveDate": "2025-03-18T18:00:00+00:00",
        "expirationDate": "2200-01-01T00:00:00+00:00",
        "state": null,
        "forecastOffice": "https://api.weather.gov/offices/AFC",
        "gridIdentifier": "ALU",
        "awipsLocationIdentifier": "AFC",
        "cwa": [
            "AFC"
        ],
        "forecastOffices": [
            "https://api.weather.gov/offices/ALU"
        ],
        "timeZone": [
            "America/Anchorage"
        ],
        "observationStations": [],
        "radarStation": null
    }
}
```
