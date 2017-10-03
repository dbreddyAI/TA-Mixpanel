
# encoding = utf-8

import os
import sys
import time
import base64
import urlparse
import json
import pytz
from datetime import datetime, timedelta
from mixpanel_query.client import MixpanelQueryClient

def validate_input(helper, definition):
    mixpanel_key = definition.parameters.get('mixpanel_project', None)
    mixpanel_secret = definition.parameters.get('project_tz', None)
    pass

def collect_events(helper, ew):
    # Retrieve runtime variables
    opt_apikey = helper.get_arg('mixpanel_project')['mixpanel_key']
    opt_apisecret = helper.get_arg('mixpanel_project')['mixpanel_secret']
    opt_timezone = helper.get_arg('project_tz')
    inputname = helper.get_input_stanza_names()
    inputsource = helper.get_input_type() + ":" + inputname
    helper.log_info("input_type=mixpanel_export input={0:s} message='Collecting events.'".format(inputname))

    today = datetime.now(pytz.timezone(opt_timezone)).strftime('%Y-%m-%d')
    yesterday = (datetime.now(pytz.timezone(opt_timezone)) - timedelta(1)).strftime('%Y-%m-%d')
    yesterday_epoch = (datetime.now(pytz.timezone(opt_timezone)) - timedelta(2)).strftime('%s')

    # Create checkpoint key
    opt_checkpoint = "mixpanel_export-{0:s}".format(inputname)
    #helper.delete_check_point(opt_checkpoint)
    
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
        if helper.get_check_point(opt_checkpoint) is None:
            last_day =  yesterday
            last_status = yesterday_epoch
            helper.log_info("input_type=mixpanel_export input={0:s} message='no checkpoint retrieved' last_day='{1}' last_status='{2}'".format(inputname,last_day,last_status))
        else:
            cpt_last = helper.get_check_point(opt_checkpoint)
            last_day =  cpt_last['last_day']
            last_status = cpt_last['last_eventtime']        
            helper.log_info("input_type=mixpanel_export input={0:s} message='retrieved checkpoint' checkpoint='{1}'".format(inputname,json.dumps(cpt_last)))
    except Exception as cpt_error:
        helper.log_error("input_type=mixpanel_export input={0:s} message='Unable to retrieve last execution checkpoint!'".format(inputname))
        raise cpt_error
    
    try:
        # Instantiate the client
        query_client = MixpanelQueryClient(opt_apikey, opt_apisecret)
    
        # Query your project's data
        obj = query_client.get_export(last_day, today)

        if obj is None:
            helper.log_info("input_type=mixpanel_export input={0:s} message='No events retrieved from Mixpanel Export API.'".format(inputname))

        i=0
        d=0
        for event in obj:
            event = convert(event) # Remove $ symbols from custom fields
            last_eventtime = event['properties']['time'] # Extract eventtime from event
            # Filter events based on last recorded eventtime to prevent duplicates & allow more frequent polling
            if int(event['properties']['time']) >= last_status:
                record = helper.new_event(source=inputsource, index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=json.dumps(event))
                ew.write_event(record)
                helper.log_debug("input_type=mixpanel_export input={0:s} message='event written to index' event={1:d}".format(inputname,i))
                i = i + 1
            else:
                d = d + 1
            
        #Update last completed execution time
        cpt_state = {}
        cpt_state['last_eventtime'] = last_eventtime
        cpt_state['last_day'] = today
        helper.save_check_point(opt_checkpoint, cpt_state)
        helper.log_info("input_type=mixpanel_export input={0:s} message='Collection complete.' indexed={1:d} discarded={2:d}".format(inputname,i,d))
        helper.log_debug("input_type=mixpanel_export input={0:s} message='Storing checkpoint info.' checkpoint='{1}'".format(inputname,json.dumps(cpt_state)))

    except Exception as error:
        helper.log_error("input_type=mixpanel_export input={0:s} message='An unknown error occurred!'".format(inputname))
        raise error