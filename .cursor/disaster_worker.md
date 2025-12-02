## Step 7, Create a background worker called `disaster_polling_agent` using CeleryBeat & CrewAI. The worker should run every 5 minutes. The ultimate goal of this worker is to be able to identify and classify metadata gathered from the nws to our internal system. The NWS uses WATCHES and WARNINGS. For our system, we translate WATCHES = EPISODES , WARNINGS = EVENTS. As such, all responses in the api must be classified into four groups: "new_events" , "updated_events", "new_episodes", "updated_episodes". Depending upon the classification, the worker will handoff the work to endpoints in an associated controller. You can reference the controllers we made earlier to determine the exact endpoint definitions. 
- [] It should poll the NWS API active endpoint https://api.weather.gov/alerts/active every 5 minutes (hint, use the http client pattern you made in earlier steps),
- [] When interacting with the NWS, this worker should use the  _last disaster poll time_ (contained in the state object) and add the header `If-Modified-Since` to find everything _after_ that date. If no date is available, get all active warnings and watches. Note the NWS API could return 304 if nothing new is found. 
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
- [] For each result, construct a custom key which makes the watch or warning unique
	- The VTEC is used for this, we must make a key which is Office + Phnenomena + Significance + ETN + Year 
	- Use your knowledge of VTECs to build this key
	- We would then reference what keys we have in our `active_events` and/or `active_episodes` state object, depending upon what is found, we can separate the events into the update event / create event / update episode / create episode groups. These groups represent an action that must be taken with the event or episode data. This is the crossover from the agentic-based poller to the API we are building.   

Notes about service layer
	- [] We need a way to detect if an event is apart of an episode. This is crucuial, vital, and critical to our business logic. Using your knowledge of how the NWS structures its metadata in the responses, and with this hint: determine if an event belongs to an episode, we should map the event polygon (the location information) and compare it with all locations for an active episode. If ANY part is overlapping, we can assume the event and episode are linked successfully. Otherwise, we do not have the episode and we must make both an event and an episode. Use a crewAI agent to do this complicated logic. The agent can accept all the location information and make an assessment accordingly.  

	- [] For identifying an update, locate all the entries in the `references` response property. We also keep an internal list of "active events" keyed by the ID, (and active episodes -- both in the state object we made earlier). Then if we get a CON, CANCEL, EXP message where its referenced, we know we are talking about that event and can update metadata accordingly. 

	- [] A note on locations, in the response property: "affected_zones`, contains a list of API endpoints. When we call the endpoint(s), there is `geomoetry.coordinates`, which is a polygon and can be used to map the _exact_ location given the correct shapefiles. 