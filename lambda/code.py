# Global imports
import boto3
from random import choice

# Create global clients
ec2_client = boto3.client('ec2')
asg_client = boto3.client('autoscaling')

# ----- Functions
def lambda_handler(event, context):
    ''' Entry point for lambda function. Expects input object in one of the following formats:
        terminate a random instance in an autoscaling group:
            {
                "mode" : "autoscaling"
                "asg_name" :  name of autoscaling group
            }
        terminate a random instance in account:
            {
                "mode" : "random_instance"
            }
    '''

    # check we have a 'mode' in our input object
    if not 'mode' in event.keys():
        raise ValueError("Required key 'mode' was not found in input object")

    # select function based on 'mode'
    mode = event['mode']
    if mode == 'autoscaling':
        # get name of group from input object
        if 'asg_name' in event.keys():
            return_message = terminate_in_asg(event['asg_name'])
        else:
            raise ValueError("Required key 'asg_name' was not found in input object")
    elif mode == 'random_instance':
        return_message = terminate_random()
    else:
        raise ValueError(f"Unexpected mode '{mode}'")

    return {
      'message': return_message
    }

def terminate_random():
    ''' terminate a random instance with a state of 'running' in AWS account. '''
    # get list of all running instance ids
    candidate_instances = get_ec2_instance_ids([{
        'Name' : 'instance-state-name',
        'Values' : ['running']
    }])

    # make sure we have at least one instance to terminate
    num_candidates = len(candidate_instances)
    if num_candidates == 0:
        raise RuntimeError("Could not find any instances in 'running' state")

    # terminate a random ec2 instance from list
    terminated_instance = terminate_random_ec2_instance(candidate_instances)

    return f'Terminated random ec2 instance {terminated_instance} from {num_candidates} possible candidates'

def terminate_in_asg(asg_name):
    ''' terminate a random instance in autoscaling group. 
        Only terminate instances that have a LifecycleState of 'InService' and an instance state of 'running'.
        Returns a message for the lambda caller
    '''
    # array to hold instances eligible for termination
    candidate_instances = list()
    # iterate through instances in asg
    for instance in get_asg_instances(asg_name):
        if instance['LifecycleState'] == 'InService':
            id = instance['InstanceId']
            # check state of instance in ec2
            if get_ec2_instance_state(id) == 'running':
                candidate_instances.append(id)

    # make sure we have at least one instance to terminate
    num_candidates = len(candidate_instances)
    if num_candidates == 0:
        raise RuntimeError(f"Could not find any instances in 'InService' and 'running' state in autoscaling group '{asg_name}'")

    # terminate random instance
    term_instance = terminate_random_ec2_instance(candidate_instances)

    return f'Terminated instance {term_instance} in autoscaling group {asg_name} from {num_candidates} possible candidates'

# ----- Helper functions
def get_ec2_instance_ids(filter):
    ''' Wrapper for describe_instances to return list of instanceids only.
        Parameters:
            filter: filter as described in https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.describe_instances
    '''
    # first time so we have no NextToken
    resp = ec2_client.describe_instances(Filters=filter)

    # create list of instance ids to return
    instanceids = _extract_instanceids(resp)

    # keep making requests until NextToken is not set (no more results)
    while('NextToken' in resp.keys()):
        # get next page of running ec2 instances with our token
        resp = ec2_client.describe_instances(Filters=filter, NextToken=resp['NextToken'])
        # add instance ids to list of instance ids
        instanceids.extend(_extract_instanceids(resp))
    
    return instanceids

def _extract_instanceids(resp):
    ''' extract instance ids from response of describe_instances. Returns list of instance ids.
        Expected input: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.describe_instances
    '''
    return_list = list()
    for reservation in resp['Reservations']:
        for instance in reservation['Instances']:
            return_list.append(instance['InstanceId'])

    return return_list

def get_ec2_instance_state(instanceid):
    ''' Get the state name of an AWS EC2 instance given by instanceid.
        Return values: 'pending'|'running'|'shutting-down'|'terminated'|'stopping'|'stopped'
    '''
    try:
        return ec2_client.describe_instances(
            Filters=[{
              'Name': 'instance-id', 'Values': [instanceid]
            }]
          )['Reservations'][0]['Instances'][0]['State']['Name']
    # If the instance doesn't exist, we'll get an IndexError. Catch & reraise it as a more helpful exception.
    except IndexError:
        raise RuntimeError(f"EC2 instance '{instanceid}' does not exist")

def get_asg_instances(asg_name):
    ''' Get instances in auto scaling group given by asg_name.
      Output format can be found at https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/autoscaling.html#AutoScaling.Client.describe_auto_scaling_groups
    '''
    try:
        return asg_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[asg_name]
          )['AutoScalingGroups'][0]['Instances']
    # If the group doesn't exist, we'll get an IndexError exception. Catch & reraise it as a more helpful exception.
    except IndexError:
        raise RuntimeError(f"Auto scaling group '{asg_name}' does not exist")

def terminate_random_ec2_instance(instanceid_list):
    ''' Helper function to terminate random ec2 instance from list of instance ids. Returns id of terminated instance '''
    # TODO - get list of volumes before terminate, terminate them if they exist after
    # pick random instance
    term_instance = choice(instanceid_list)
    # disable termination protection - idempotent
    ec2_client.modify_instance_attribute(InstanceId=term_instance, DisableApiTermination={'Value':False})
    # terminate it
    ec2_client.terminate_instances(InstanceIds=[term_instance])
    # return id
    return term_instance