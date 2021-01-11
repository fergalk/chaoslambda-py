#!/usr/bin/env python3
# -- Global imports

import os
import json
import logging
import sys

# -- Core functions
def main():
    # get args from command line
    opts = parse_args(sys.argv)
    # set debug if we want it
    set_debug(opts.verbose)

    # get conf from file
    conf = get_conf(readfile(opts.config_file))

# -- Secondary functions
def parse_args(args_to_parse):
    ''' Function to parse args. Returns an optparse options object '''
    # local imports
    from optparse import OptionParser

    # create parser
    parser = OptionParser()
    # add options
    parser.add_option('-c', '--config-file', help='path to json config file', dest='config_file', metavar='FILE')
    parser.add_option('-v', '--verbose', action='store_true', help='debugging output', dest='verbose')

    # parse - we only care about the first element in array as the second is our args
    opts = parser.parse_args(args=args_to_parse)[0]

    # validate args
    if not opts.config_file:
        log.error(f'No config file provided')
        exit(1)

    # return
    return opts

def set_debug(debug):
    ''' If debug is true, set global log level to debug, otherwise set to info. '''
    if debug:
        log.setLevel(logging.DEBUG)
    else:
        log.setLevel(logging.INFO)


def get_conf(input):
    ''' Decode & lint the config from the string given by input. Expected contents (json):
        {
            "auto_scaling_group" : [
                {
                    "name": asg_name,
                    "cron_expression": cron_expression
                },
                ...
            ],
            "terminate_random" : [
                cron_expression,
                cron_expression
                ...
            ]
        }
        At least one of auto_scaling_group & terminate_random is required.
        Returns data from file as a dict.
    '''
    # decode json       
    conf_dict = json.loads(input)

    # -- linting
    # validate number of keys in dict
    if len(conf_dict.keys()) == 0 :
        log.error(f'No keys found in config file')
        exit(1)

    # validate that all keys in the dict are valid
    for key in conf_dict.keys():
        if not key in ('auto_scaling_group', 'terminate_random'):
            log.error(f'Unknown key {key} in config file')
            exit(1)

    # validate that all the 'auto_scaling_group' dicts are valid
    if 'auto_scaling_group' in conf_dict.keys():
        # counter for formatting
        dict_number = 1
        # iterate through dicts
        for asg_dict in conf_dict['auto_scaling_group']:
            if sorted(asg_dict.keys()) != sorted(['name', 'cron_expression']):
                log.error(f'auto_scaling_group {dict_number} in config file malformed')
                exit(1)
            # bump counter
            dict_number += 1

    # print a debug message
    log.debug(f'Input file linted successfully')

    return conf_dict

# -- Helper functions
def readfile(filename):
    ''' Open file, read, close file, return contents '''
    fo = open(filename, 'r')
    contents = fo.read()
    fo.close()
    return contents

# -- Setup logging
logging.basicConfig(format='%(levelname)s: %(message)s')
log = logging.getLogger('global')


# -- Run main
if __name__ == '__main__':
    main()