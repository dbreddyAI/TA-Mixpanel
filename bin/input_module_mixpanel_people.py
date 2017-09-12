
# encoding = utf-8

import os
import sys
import time
import datetime
import base64
import urlparse
import json
import kvstore_lib
from mixpanel import Mixpanel

def validate_input(helper, definition):
    mixpanel_key = definition.parameters.get('mixpanel_project', None)
    enable_index = definition.parameters.get('enable_index', None)
    enable_kvstore = definition.parameters.get('enable_kvstore', None)
    enable_kvstore = definition.parameters.get('kvstore_fields', None)
    pass

def collect_events(helper, ew):
    # Retrieve runtime variables
    app_name =  helper.get_app_name()
    opt_apikey = helper.get_arg('mixpanel_project')['mixpanel_secret']
    inputname = helper.get_input_stanza_names()
    inputsource = helper.get_input_type() + ":" + inputname
    session = helper.context_meta
    helper.log_info("input_type=mixpanel_people input={0:s} message='collecting Mixpanel Engage API events'".format(inputname))
    
    #Set module level kvstore variables
    enable_kv = helper.get_arg('enable_kvstore')
    kvstore_fields = helper.get_arg('kvstore_fields')
    enable_index = helper.get_arg('enable_index')

    # Set time to filter returned results by timestamp
    #start_time = (time.time() - 30)

    # Create checkpoint key
    #opt_checkpoint = "mixpanel_people-" + inputname
    
    #Check for last query execution data in kvstore & generate if not present
    #try:
    #    last_status = helper.get_check_point(opt_checkpoint) or start_time
    #    helper.log_debug("[" + inputname + "] Mixpanel People API - Last successful checkpoint time: " + str(last_status))
    #except Exception as e:
    #    helper.log_error("[" + inputname + "] Mixpanel People API - Unable to retrieve last execution checkpoint!")
    #    raise e

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

    #Configure KVStore if enabled
    if enable_kv is True:
        
        #Create base kvstore connectivity 
        kvs = kvstore_lib.KVClient(session['server_uri'], session['session_key'], helper.service)

        #Set KVStore to write events if not configured to input name else report_id
        opt_kvstore = "TA_Mixpanel_People_{0:s}".format(inputname)
        helper.log_debug("input_type=mixpanel_people input={0:s} kvstore={1:s} message='kvstore name configured'".format(inputname,opt_kvstore))

        #Create KVStore in specified app
        kvs_create = kvs.create_collection(collection=opt_kvstore, app=app_name)
        helper.log_info("input_type=mixpanel_people input={0:s} kvstore={1:s} message='kvstore already present or has been created'".format(inputname,opt_kvstore))
        
        #Configure KVStore field object to POST to KVStore
        try:
            lookup_name = opt_kvstore
            kv_fields_list = [] #List of fields returned by API formatted for kvstore config
            lookup_fields_list = [] #List of fields returned by API formatted for lookup config
            
            kvstore_fields = json.loads(kvstore_fields)
            if isinstance(kvstore_fields, dict):
                helper.log_debug("input_type=mixpanel_people input={0:s} kvstore={1:s} message='loaded fields configuration from input setup' fields='{2}'".format(inputname,opt_kvstore,json.dumps(kvstore_fields)))

                for key, value in kvstore_fields.items():
                    lookup_key = key
                    field_key = "field.{0:s}".format(key)
                    if value != ["array","number","bool","string","cidr","time"]:
                        value = "string"
                    field_value = value
                
                    field = [(field_key, field_value)]
                    #Configure fields to POST for lookup creation
                    lookup_fields_list.append(lookup_key)
                    kv_fields_list.append(lookup_key)
                    
                    #Create kvstore configuration with fields returned
                    add_field = kvs.config_collection(collection=opt_kvstore, app=app_name, data=field)
                    helper.log_debug("input_type=mixpanel_people input={0:s} kvstore={1:s} message='configuring kvstore field' field={2}".format(inputname,opt_kvstore,json.dumps(field)))

                #Create object to log status
                lookup_fields = ",".join(['"{}"'.format(x) for x in lookup_fields_list])
                create_lookup = kvs.config_lookup(lookup=lookup_name, app=app_name, fields=lookup_fields)
                helper.log_info("input_type=mixpanel_people input={0:s} lookup_name={1:s} message='configured lookup fields' count={2:d}".format(inputname,lookup_name,len(lookup_fields_list)))
                helper.log_debug("input_type=mixpanel_people input={0:s} lookup_name={1:s} message='configured lookup fields' fields='{2}'".format(inputname,lookup_name,lookup_fields))
        except Exception as config_fields:
            helper.log_error("input_type=mixpanel_people input={0:s} message='unable to load fields configuration from input setup'".format(inputname))
            helper.log_error("input_type=mixpanel_people input={0:s} function=config_fields status='failure' message='{1}'".format(inputname,config_fields))
    
        #Purge all existing data from KVStore
        enable_purge = True
        if enable_purge is True:
            kvs_purge = kvs.delete_collection_data(collection=opt_kvstore, key_id=None, app=app_name)
            helper.log_info("input_type=mixpanel_people input={0:s} kvstore={1:s} message='kvstore data purged'".format(inputname,opt_kvstore))
    
    try:
        # Leverage helper function to send http request
        api = Mixpanel(api_secret=opt_apikey)
        
        parameters = {'selector': ''}
        response = api.request(['engage'], parameters)
    
        # Return API response code
        #r_status = response.status_code
        # Return API request status_code
        #if r_status is not 200:
        #    helper.log_error("input_type=mixpanel_people input=" + inputname + " message='API query unsuccessful.' status_code=" + str    (r_status))
        #    response.raise_for_status()

        if response['results'] is None:
            helper.log_info("input_type=mixpanel_people input={0:s} message='No events retrieved from Mixpanel People API.'".format(inputname))

        parameters['session_id'] = response['session_id']
        parameters['page']=0
        global_total = response['total']
            
        # Log session_id for debug
        helper.log_debug("input_type=mixpanel_people input='{0:s}' session_id='{1:s}' message='Session id set.'".format(inputname,response['session_id']))
        # Log total records returned by query
        helper.log_info("input_type=mixpanel_people input={0:s} message='Total people records available.' total_records={1:d}".format(inputname,global_total))

        has_results = True
        total = 0 #iterator for records returned from Mixpanel
        i = 0 #iterator for indexed records processed
        k = 0 #iterator for kvstore records processed
        while has_results:
            responser = response['results']
            total += len(responser)
            has_results = len(responser) == 1000
            for data in responser:
                data = convert(data)
                
                #Checks if indexing enabled and writes events to specified index
                if enable_index is True:
                    event = helper.new_event(source=inputsource, index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=json.dumps(data))
                    ew.write_event(event)
                    i = i + 1 #Count records indexed
                    helper.log_debug("input_type=mixpanel_people input={0:s} message='indexed events' status=successful event_count={1:d}".format(inputname,i))
                    
                #Checks if kvstore is enabled and writes events based on kvstore settings
                if enable_kv is True:
                    #Create timestamp for kvstore metadata
                    time_updated = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                    data['_updated'] = time_updated #Add meta value for troubleshooting
                    
                    #Insert of records is all that is allowed
                    insert_new = kvs.insert_collection_data(collection=opt_kvstore, app=app_name, owner="nobody", data=data)
                    k = k + 1 #Count records stored to kvstore
                    helper.log_debug("input_type=mixpanel_people input={0:s} kvstore={1:s} message='record inserted in kvstore' status=successful event_count={2:d}".format(inputname,opt_kvstore,k))

            helper.log_debug("input_type=mixpanel_people input={0:s} processed={1:d} total_events={2:d} page={3:d}".format(inputname,total,global_total,parameters['page']))
            parameters['page'] += 1
            if has_results:
                response = api.request(['engage'], parameters)
            
        #Update last completed execution time
        #helper.save_check_point(opt_checkpoint, last_status)
        helper.log_info("input_type=mixpanel_people input={0:s} message='Collection complete.' indexed={1:d} kvstore={2:d} total_records={3:d}".format(inputname,i,k,global_total))
        #helper.log_debug("[" + inputname + "] Mixpanel People API - Storing checkpoint time: " + str(last_status))

    except Exception as error:
        helper.log_error("input_type=mixpanel_people input={0:s} message='An unknown error occurred!'".format(inputname))
        raise error