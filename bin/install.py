#!/usr/bin/env python3
# -- Global imports
import os
import json
import logging
import sys
import boto3

# -- Global vars
# path to iam resources
iam_path = '/ChaosLambda/'
# chaoslambda execution role name
iam_role_name = 'ChaosLambdaExecutionRole'
# chaoslambda execution policy
iam_policy_name = 'ChaosLambdaExecutionPolicy'

# -- Core functions
def main():
    # get args from command line
    opts = parse_args(sys.argv)
    # set debug if we want it
    set_debug(opts.verbose)

    # get conf from file
    conf = get_conf(readfile(opts.config_file))

    # add IAM components to AWS
    role_arn = setup_iam_role()

    # setup lambda function
    setup_lambda_function()

    if 'auto_scaling_group' in conf.keys():
        pass
        # TODO

    if 'terminate_random' in conf.keys():
        pass
        # TODO

def setup_iam_role():
    ''' Sets up IAM role in AWS with embedded policy for Chaos Lambda function. Idempotent. Returns role ARN. '''
    client = boto3.client('iam')

    # delete role policy if it exists
    try:
        client.delete_role_policy(RoleName=iam_role_name, PolicyName=iam_policy_name)
    except client.exceptions.NoSuchEntityException:
        # swallow
        pass
    # delete role if it exists
    try:
        client.delete_role(RoleName=iam_role_name)
    except client.exceptions.NoSuchEntityException:
        # swallow
        pass

    # create role
    log.debug(f'Creating IAM role {iam_role_name}')
    role_arn = client.create_role(
        Path = iam_path,
        RoleName = iam_role_name,
        Description = 'Lambda execution role for chaoslambda',
        AssumeRolePolicyDocument=json.dumps({
            'Version' : '2012-10-17',
            'Statement' : {
                'Principal': {'Service': ['lambda.amazonaws.com']},
                'Effect': 'Allow',
                'Action': 'sts:AssumeRole'
            }
        })
    )['Role']['Arn']

    # create inline policy
    log.debug(f'Creating inline policy {iam_policy_name} for IAM role {iam_role_name}')
    client.put_role_policy(
        RoleName = iam_role_name,
        PolicyName = iam_policy_name,
        PolicyDocument = json.dumps({
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Action': [
                        'ec2:DescribeInstances',
                        'ec2:TerminateInstances',
                        'ec2:ModifyInstanceAttribute',
                        'autoscaling:DescribeAutoScalingGroups'
                    ],
                    'Resource': [
                        'arn:aws:ec2:*',
                        'arn:aws:autoscaling:*'
                    ]
                }
            ]
        })
    )

    # return role arn
    return role_arn


def setup_lambda_function():
    # TODO
    pass

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

    # validate values
    if not opts.config_file:
        log.error(f'No config file provided')
        exit(1)

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