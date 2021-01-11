#!/usr/bin/env python3
import install
import pytest
import json
import logging

# -- arg parsing & setup
def test_parse_args_no_args():
    ''' Test the parse_args() function with no args - should try to exit '''
    with pytest.raises(SystemExit):
        install.parse_args([])

def test_parse_args_with_file():
    ''' Test the parse_args() function with a config file '''
    assert install.parse_args(['-c', 'somerandomfile.json']).config_file == 'somerandomfile.json'

def test_log_verbose():
    ''' Test that the -v flag results in a log level of DEBUG '''
    # parse test args
    opts = install.parse_args(['-c', 'somerandomfile.json', '-v'])
    # set the log level
    install.set_debug(opts.verbose)
    # should be debug
    assert install.log.level == logging.DEBUG

def test_log_non_verbose():
    ''' Test that omitting the -v flag results in a log level of INFO '''
    # parse test args
    opts = install.parse_args(['-c', 'somerandomfile.json'])
    # set the log level
    install.set_debug(opts.verbose)
    # should be info
    assert install.log.level == logging.INFO

# -- get_conf()
def test_get_conf_invalid_key():
    ''' Run get_conf with an invalid key in the json '''
    conf = json.dumps({
        'auto_scaling_group' : [
            {'name': 'somerandomgroup'}
        ],
        'terminate_random' : ['0 9 * * *'],
        'thiskeydoesnotbelong':'here'
    })
    
    with pytest.raises(SystemExit):
        install.get_conf(conf)

def test_get_conf_empty_json():
    ''' Run get_conf with no content in the json '''
    conf = json.dumps({})
    
    with pytest.raises(SystemExit):
        install.get_conf(conf)

def test_get_conf_valid_bad_asg():
    ''' Run get_conf with a bad auto scaling group entry '''
    conf = json.dumps({
        'auto_scaling_group' : [
            {'name': 'somerandomgroup'}
        ],
        'terminate_random' : ['0 9 * * *']
    })
    
    with pytest.raises(SystemExit):
        install.get_conf(conf)

def test_get_conf_valid():
    ''' Run get_conf with valid config json '''
    conf = json.dumps({
        'auto_scaling_group' : [
            {'name': 'somerandomgroup', 'cron_expression': '0 9 * * *'}
        ],
        'terminate_random' : ['0 9 * * *']
    })
    
    assert install.get_conf(conf)['terminate_random'][0] == '0 9 * * *'