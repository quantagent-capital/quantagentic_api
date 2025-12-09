## Your job is to implement the internal CREATE EVENT logic. 

### Here are the nuances of the NWS and our polling: 
- The NWS will give us duplicate WARNINGS (events). Thus, we should account for this in our internal system.

- In the disaster poller, when we get a response from the crew, we have this object ClassifiedAlertsOutput. We will focus on the `create_events` bucket for this task. 

- Thus, we need to check if any of the `new_events.FilteredNWSAlert.key` match an existing redis key in the state, if there is NO match, it is a new event. And thus, we should call our create_event endpoint accordingly. If there is a match, we can do nothing about the alert. 

- The poller should simply call the endpoint, and not be blocked waiting for a response. The poller doesn't care about the response from the API. It can be "fire and forget" or something of that like. The key here is that, when reaching out to our API, the poller isn't blocked. 

### Here are the requirements for the request structure and endpoint interaction: 

1. For each new event, send an http request to the create_event. 
2. The request should be NON BLOCKING for the poller. Meaning, it doesn't care about the response, nor should it wait for the API to finish processing. 
3. The body of the request for these endpoints can change to be list[FilteredNWSAlert]
4. The `event` model should have a list of locations associated with it, isntead of a single location
5. the `location` model should utilize `episode_key` instead of `episode_id`
6. the `location.shape` should be an array of `coordinates` , where `coordinates` is a class that contains a float for `latitude` / `longitude`

### Create a shell for a new crew
1. New crew directory / class structure is stubbed, we can call it `event_profile_crew``
2. Executor is stubbed, models are stubbed 
3. Task file is stubbed 
4. agent file is stubbed  

### Here are the requirements for the event service layer 
1. We receive the list of FilteredNWSAlerts
2. Instantiate the crew, assume the result of the crew can be an `event` model
3. Save the event to the redis database, save the event_key to the `active_events` state object

For each `affected_zones_ugc_endpoints` , call the endpoint, review the response, and MAP to countyFIPS



# take in list of endpoints 
# call affected area, one by one 
# map to location. 
#  