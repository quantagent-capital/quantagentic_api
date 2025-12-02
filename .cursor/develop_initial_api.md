# Instructions

You are working in railway and python. Reference the current structure to understand dependency management, runtime, and an initial understanding of the structure. 

Once you understand, I want you to add onto this "helloworld railway app" by using python, FastAPI, redis, and crewAI. You are an expert in these technologies geared to help me set up all the infrastructure and software engineering needed to get started. You will help me implement the API, background workers (which are ai agents -- using crewAI) and perform logic to my specifications. Use snake case naming conventions.


## Step 0, Install and update dependencies 

## Step 1, Create Redis Instance
- [] Spin up the code necessary to utilize a redis instance in docker 
- [] Create a generalized redis client called `quantagent_redis` which can perform all basic CRUD operations for a given key

Step 2, Create Redis schema classes in python, to be used used by both callers, and can leverage the quantagent_redis lower level wrapper we came up with in the previous step. The schema serialization and deserialization (into the custom objects from redis json) should allow for newly added properties to be added easily without breaking this step. I.e., it should be robust and scalable to deseralize and serialize commonly used advanced types (pandas df, for example) 

- [] Location
	episode_id: int
	event_key: string
	state_fips: string
	county_fips: string
	ugc_code: string
	shape: string (polygon)
- [] Episode
	episodeId: int
	start_date: datetime
	end_date: datetime?
	total_damage: int?
	total_hurt: int?
	total_range_miles: int?
	included_event_types: string
	watch_description: string
	area_description: string
	locations: list[locations]
	is_active: boolean
- [] Event
	event_key: string
	episode_id: int?
	event_type: string
	location: location
	start_date: datetime
	end_date: datetime?
	property_damage: int?
	crops_damage: int?
	range_miles: float?
	description: string
	is_active: bool

## Step 2, Create Episode Controller Endpoints & Service Layer classes 
- [] Create an `episode` controller
	- [] create_episode endpoint is stubbed , create_episode service layer is stubbed
	- [] update_episode endpoint is stubbed, update_episode service layer is stubbed
	- [] get_episode endpoint is stubbed  , get_episode service layer is stubbed

## Step 3, Create Episode Controller Scaffolding & Service Layer Classes
- [] Create an `events` controller
	- [] create_event endpoint is stubbed, create_event service layer is stubbed
	- [] update_event endpoint is stubbed, update_event service layer is stubbed
	- [] get_event endpoint is stubbed , get_event service layer is stubbed
	- [] has_episode endpoint is stubbed, has_episode service layer is stubbed 

## Step 4, Create a re-useable HTTP client
- [] Implement scalable, robust, and re-useable HTTP client for callers to use. This will communicate with many external APIs, do your best to implement a base class that is scalalble, robust, and able to interact with more client APIs 
- [] Fundamentally, all calls to the NWS (example endpoint https://api.weather.gov/alerts/active) must have a specific User-Agent:
	- E.G., User-Agent: ( quantagent_capital, jacob@quantagent_capital.ai )

## Step 6, Create state object, to be used as a shared memory class amongst the entire API and all agents
	- [] contains property of `active_events`
	- [] contains property of `active_episodes`
	- [] contains property of `last_disaster_poll_time`

## Step 7, Update README for user friendly startup instructions. Assume the OS is mainly going to be mac









 