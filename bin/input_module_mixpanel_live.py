
# encoding = utf-8

import os
import sys
import time
import datetime
import base64
import urlparse
import json

def validate_input(helper, definition):
    mixpanel_key = definition.parameters.get('mixpanel_project', None)
    pass

def collect_events(helper, ew):
    # Retrieve runtime variables
    opt_apikey = helper.get_arg('mixpanel_project')['mixpanel_secret']
    opt_project = helper.get_arg('mixpanel_project')['name']
    inputname = helper.get_input_stanza_names()
    inputsource = helper.get_input_type() + ":" + inputname
    helper.log_info("input_type=mixpanel_live input={0:s} project={1:s} message='Collecting events.'".format(inputname,opt_project))

    # Set time to filter returned results by timestamp
    start_time = (time.time() - 30)

    # Create checkpoint key
    opt_checkpoint = "mixpanel_live-{0:s}".format(inputname)

    # Function to remove $ symbols from custom fields
    def convert(input):
        if isinstance(input, dict):
            return {convert(key): convert(value) for key, value in input.iteritems()}
        elif isinstance(input, list):
            return [convert(element) for element in input]
        elif isinstance(input, unicode):
            return input.strip('$')
        else:
            return input
    
    #Check for last query execution data in kvstore & generate if not present
    try:
        last_status = helper.get_check_point(opt_checkpoint) or start_time
        helper.log_debug("input_type=mixpanel_live input={0:s} message='Last successful checkpoint time.' last_status={1:f}".format(inputname,last_status))
    except Exception as e:
        helper.log_error("input_type=mixpanel_live input={0:s} message='Unable to retrieve last execution checkpoint!'".format(inputname))
        raise e
        
    auth_token = base64.b64encode(opt_apikey + ":").decode("ascii")
    header =  {'Authorization': 'Basic {}'.format(auth_token)}
    parameter = {}
    parameter['client_version'] = 3
    parameter['start_time'] = last_status
    url = 'https://mixpanel.com/api/2.0/live'
    method = 'GET'
    
    try:
        # Leverage helper function to send http request
        response = helper.send_http_request(url, method, parameters=parameter, payload=None, headers=header, cookies=None, verify=True, cert=None, timeout=25, use_proxy=True)
        helper.log_debug("input_type=mixpanel_live input={0:s} message='Last successful checkpoint time.' url={1:s} parameters={2:s}".format(inputname,url,parameter))

        # Return API response code
        r_status = response.status_code
        # Return API request status_code
        if r_status is not 200:
            helper.log_error("input_type=mixpanel_live input={0:s} message='API request unsuccessful.' status_code={1:d}".format(inputname,r_status))
            response.raise_for_status()
        # Return API request as JSON
        obj = response.json()

        if obj is None:
            helper.log_info("input_type=mixpanel_live input={0:s} message='No events retrieved from Mixpanel Live API.'".format(inputname))
            exit()
        
        i=0
        for event in obj['event_list']:
            event = convert(event)
            last_eventtime = event['ts']
            if int(event['ts']) >= last_status:
                event = helper.new_event(source=inputsource, index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=json.dumps(event))
                ew.write_event(event)
                i = i + 1
            
        #Update last completed execution time
        helper.save_check_point(opt_checkpoint, last_eventtime)
        helper.log_info("input_type=mixpanel_live input={0:s} project={1:s} message='Collection complete.' indexed={2:d}".format(inputname,opt_project,i))
        helper.log_debug("input_type=mixpanel_live input={0:s} project={1:s} message='Storing checkpoint.' last_eventtime={2:f}".format(inputname,opt_project,last_eventtime))

    except Exception as error:
        helper.log_error("input_type=mixpanel_live input={0:s} project={1:s} message='An unknown error occurred!'".format(inputname,opt_project))
        raise error