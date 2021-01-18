#!/usr/bin/env python3
# -- Global imports
import os
import json
import logging
import sys
import boto3


# -- Global vars
# chaoslambda lambda function name
lambda_function_name = 'ChaosLambda'
# location of lambda code file
lambda_code_file = '{scriptdir}{path_sep}..{path_sep}lambda{path_sep}code.py'.format(
    scriptdir = os.path.dirname(os.path.realpath(__file__)), # directory of install script
    path_sep = os.path.sep
)
# information URL - added to AWS resources
info_url = 'https://github.com/fergalk/chaoslambda-py'
# cloudformation stack name
cf_stack_name = 'ChaosLambdaDeployment'

# -- Core functions
def main():
    # get args from command line
    opts = parse_args(sys.argv)

    # set debug if we want it
    set_debug(opts.verbose)

    if opts.destroy:
        # user specified -D, delete cf stack
        log.info('Destroying AWS resources')
        if delete_cloudformation_stack(cf_stack_name):
            # stack existed
            log.info('Removed all AWS resources')
            exit(0)
        else:
            log.warning('There were no resources to remove')
            exit(1)

    else:
        # user didn't specify -D, create/update resources
        # get conf from file
        conf = get_conf(read_file(opts.config_file))
        # generate cloudformation template
        cf_template = gen_cloudformation_template(conf)
        # if -T specified, print our cloudformation template 
        if opts.template_out:
            write_file(opts.template_out, cf_template)
        # upload cloudformation template
        upload_cloudformation_template(cf_template, cf_stack_name)
        # upload lambda code
        upload_lambda_code()
        # log a message
        log.info('Deployment successful!')
        exit(0)

def parse_args(args_to_parse):
    ''' Function to parse args. Returns an optparse options object '''
    # local imports
    from optparse import OptionParser

    # create parser
    parser = OptionParser()
    # add options
    parser.add_option('-c', '--config-file', help='path to json config file', dest='config_file', metavar='FILE')
    parser.add_option('-T', '--template-out', help='print generated cloudformation template to file', dest='template_out', metavar='FILE')
    parser.add_option('-D', '--destroy', help='remove all ChaosLambda components from AWS', dest='destroy', action='store_true')
    parser.add_option('-v', '--verbose', action='store_true', help='debugging output', dest='verbose')

    # parse - first element in array is options object, second we can ignore
    opts = parser.parse_args(args=args_to_parse)[0]

    # -- validate args
    if opts.destroy and opts.config_file:
        log.error('Options -c and -d are mutually exclusive')
        exit(1)

    if opts.destroy and opts.template_out:
        log.error('Options -T and -d are mutually exclusive')
        exit(1)

    if (not opts.config_file) and (not opts.destroy) :
        log.error(f'No config file provided')
        exit(1)

    return opts

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
            "random" : [
                cron_expression,
                cron_expression
                ...
            ]
        }
        At least one of auto_scaling_group & random is required.
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
        if not key in ('auto_scaling_group', 'random'):
            log.error(f'Unknown key {key} in config file')
            exit(1)

    # validate that all the 'auto_scaling_group' dicts are valid
    if 'auto_scaling_group' in conf_dict.keys():
        # counter for formatting
        dict_number = 1
        # iterate through dicts
        for asg_dict in conf_dict['auto_scaling_group']:
            if sorted(asg_dict.keys()) != sorted(['name', 'cron_expression']):
                log.error(f'auto_scaling_group {dict_number} in config file is malformed')
                exit(1)
            # bump counter
            dict_number += 1

    # print a debug message
    log.debug(f'Config file linted successfully')

    return conf_dict

def gen_cloudformation_template(conf):
    ''' Generate a cloudformation template to create our AWS components. Returns template as string. '''
    # create skeleton from static components
    template = {
        'AWSTemplateFormatVersion' : '2010-09-09',
        'Description' : f'Deploy components for ChaosLambda. More info at {info_url}',
        'Resources' : {
            'LambdaRole' : {
                'Type' : 'AWS::IAM::Role',
                'Properties' : {
                    'AssumeRolePolicyDocument' : {
                        'Version': '2012-10-17',
                        'Statement': [{
                            'Effect': 'Allow',
                            'Principal': {
                                'Service': 'lambda.amazonaws.com'
                            },
                            'Action': 'sts:AssumeRole'
                        }]},
                    'Description' : f'Execution role for ChaosLambda. More info at {info_url}',
                    'ManagedPolicyArns' : [ 'arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole' ],
                    'RoleName' : 'ChaosLambdaExecutionRole',
                    'Policies' : [{
                        'PolicyName' : 'ChaosLambdaPolicy',
                        'PolicyDocument' : {
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
                                        '*'
                                    ]
                                }
                            ]
                        }
                    }]
                }
            },
            'LambdaFunction' : {
                'Type' : 'AWS::Lambda::Function',
                'Properties' : {
                    'Code': { 'ZipFile' : 'pass' }, # dummy contents, upload full contents once stack creation is complete
                    'Description' : f'Lambda function for ChaosLambda. More info at {info_url}',
                    'FunctionName' : lambda_function_name,
                    'Handler' : 'code.handler',
                    'Timeout' : 60,
                    'Role' : { 'Fn::GetAtt' : ['LambdaRole', 'Arn'] },
                    'Runtime' : 'python3.8'
                }
            },
            'LambdaEventPermission' : {
                'Type' : 'AWS::Lambda::Permission',
                'Properties' : {
                    'Action' : 'lambda:InvokeFunction',
                    'FunctionName' : {'Ref':'LambdaFunction'},
                    'Principal' : 'events.amazonaws.com'
                }
            },
        }
    }

    # -- Generate dynamic components
    # counter for generating dynamic resource & rule names. 
    res_counter = 0

    # add any auto scaling groups
    if 'auto_scaling_group' in conf.keys():
        for group in conf['auto_scaling_group']:
            # name of asg
            groupname = group['name']
            # schedule for rule
            cron_expr = group['cron_expression']
            # add resource to cf template
            log.debug(f'Adding cloudwatch rule for asg {groupname}, schedule cron({cron_expr}) to cloudformation template')
            template['Resources'][f'ScheduledRule{res_counter}'] = {
                'Type' : 'AWS::Events::Rule',
                'Properties' : {
                    'Description' : f'Execution scheduler for ChaosLambda. Terminates random EC2 instance in {groupname} on schedule cron({cron_expr}). More info at {info_url}',
                    'Name' : f'ChaosLambdaScheduler-{res_counter}',
                    'ScheduleExpression' : f'cron({cron_expr})',
                    'State' : 'ENABLED',
                    'Targets' : [{
                        'Arn' : { 'Fn::GetAtt' : ['LambdaFunction', 'Arn'] },
                        'Id' : 'execute_lambda',
                        'Input' : json.dumps({
                            'mode' : 'autoscaling',
                            'asg_name' : groupname
                        })
                    }]
                }
            }
            # bump
            res_counter += 1

    # add rules for terminating random instance in account
    if 'random' in conf.keys():
        for cron_expr in conf['random']:
            # add resource to cf template
            log.debug(f'Adding cloudwatch rule for random instance, schedule cron({cron_expr}) to cloudformation template')
            template['Resources'][f'ScheduledRule{res_counter}'] = {
                'Type' : 'AWS::Events::Rule',
                'Properties' : {
                    'Description' : f'Execution scheduler for ChaosLambda. Terminates random EC2 instance in account on schedule cron({cron_expr}). More info at {info_url}',
                    'Name' : f'ChaosLambdaScheduler-{res_counter}',
                    'ScheduleExpression' : f'cron({cron_expr})',
                    'State' : 'ENABLED',
                    'Targets' : [{
                        'Arn' : { 'Fn::GetAtt' : ['LambdaFunction', 'Arn'] },
                        'Id' : 'execute_lambda',
                        'Input' : json.dumps({'mode' : 'random'})
                    }]
                }
            }
            # bump
            res_counter += 1

    return json.dumps(template, indent=4)

def upload_cloudformation_template(template, name):
    ''' Creates/updates cloudformation template given by name. Expects template as string in json format. '''
    # create boto3 client
    client = boto3.client('cloudformation')

    # parameters for update_stack/create_stack
    stack_params = {
        'StackName' : name,
        'TemplateBody' : template,
        'Capabilities' : ('CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM')
    }

    # parameters for boto3 waiters
    wait_params = {
        'StackName' : name,
        'WaiterConfig' : {'Delay':2}
    }

    # check if stack exists, and what its state is
    try:
        if client.describe_stacks(StackName=name)['Stacks'][0]['StackStatus'] in ('ROLLBACK_COMPLETE', 'DELETE_COMPLETE'):
            log.debug(f'Cloudformation stack {name} already exists, but state is ROLLBACK_COMPLETE or DELETE_COMPLETE')
            delete_stack = True
            # we're deleting it anyway, so set to false
            stack_exists = False
        else:
            log.debug(f'Cloudformation stack {name} already exists and does not require deletion')
            delete_stack = False
            stack_exists = True
    except client.exceptions.ClientError:
        log.debug(f'Cloudformation stack {name} does not exist')
        stack_exists = False
    else:
        if delete_stack:
            # if the stack state is ROLLBACK_COMPLETE or DELETE_COMPLETE, delete it first
            log.info(f'Deleting stack {name} as its state is ROLLBACK_COMPLETE or DELETE_COMPLETE')
            delete_cloudformation_stack(name)
            log.info('Stack deletion completed')

    # if our stack exists, update it, otherwise create it
    if stack_exists:
        log.info(f'Updating cloudformation stack {name}')
        try:
            client.update_stack(**stack_params)
        except client.exceptions.ClientError:
            # no updates to be made
            log.info('Cloudformation stack update rejected as no updates are required')
        else:
            log.debug('Waiting for stack update to complete')
            client.get_waiter('stack_update_complete').wait(**wait_params)
            log.info('Stack update complete')
    else:
        log.info(f'Creating cloudformation stack {name}')
        client.create_stack(**stack_params)
        log.debug('Waiting for stack create to complete')
        client.get_waiter('stack_create_complete').wait(**wait_params)
        log.info('Stack creation complete')

def upload_lambda_code():
    ''' Uploads the lambda code in lambda_code_file to lambda function lambda_function_name '''
    log.info(f'Updating code for lambda function {lambda_function_name} to code in {lambda_code_file}')
    boto3.client('lambda').update_function_code(
        FunctionName = lambda_function_name,
        ZipFile = create_deployment_package(lambda_code_file),
        Publish = True
    )

# -- Helper functions
def set_debug(debug):
    ''' If debug is true, set global log level to debug, otherwise set to info. '''
    if debug:
        log.setLevel(logging.DEBUG)
    else:
        log.setLevel(logging.INFO)

def read_file(filename):
    ''' Open file, read, close file, return contents '''
    fo = open(filename, 'r')
    contents = fo.read()
    fo.close()
    return contents

def write_file(filename, contents):
    ''' Open file, write contents, close file '''
    fo = open(filename, 'w')
    fo.write(contents)
    fo.close()

def create_deployment_package(code_path):
    ''' Returns a byte stream representing the lambda function code in code_path as a zip file. Renames the lambda function code to code.py '''
    import tempfile, zipfile
    # -- zip files
    # generate temporary zip file name - portable
    zip_file_name = '{dirname}{path_sep}{filename}.zip'.format(
        dirname = tempfile._get_default_tempdir(),
        path_sep = os.path.sep,
        filename = next(tempfile._get_candidate_names())
    )
    # create archive
    zip = zipfile.ZipFile(zip_file_name, mode='w')
    # add file to archive
    zip.write(code_path, arcname='code.py')
    # close
    zip.close()

    # -- read file
    fo = open(zip_file_name, 'rb')
    contents = fo.read()
    fo.close()
    
    # -- delete file
    os.remove(zip_file_name)

    # return filename
    return contents

def delete_cloudformation_stack(stack_name):
    ''' Delete cloudformation stack given by cf_stack_name and wait for deletion to complete. Returns True if stack deleted, False if stack didn't exist. '''
    client = boto3.client('cloudformation')

    try:
        # check if stack exists
        client.describe_stacks(StackName=stack_name)
    except client.exceptions.ClientError:
        # doesn't exist
        log.debug(f'Cf stack {stack_name} does not exist')
        return False
    else:
        # does exist
        client.delete_stack(StackName=stack_name)
        log.debug(f'Waiting for cf stack {stack_name} deletion to complete')
        client.get_waiter('stack_delete_complete').wait(StackName=stack_name, WaiterConfig = {'Delay':2})
        return True

# -- Setup logging
logging.basicConfig(format='%(levelname)s: %(message)s')
log = logging.getLogger('global')

# -- Run main
if __name__ == '__main__':
    main()