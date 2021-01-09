# Global imports
import boto3
from random import choice

# Create global clients
ec2_client = boto3.client('ec2')
asg_client = boto3.client('autoscaling')

# --- Functions
def lambda_handler(event, context):
    ''' Entry point for lambda function. Expects event object in one of the following formats:
        Kill a random instance in an autoscaling group:
            {
                "mode" : "autoscaling"
                "asg_name" :  name of autoscaling group
            }
        Kill a random instance in account:
            {
                "mode" : "random_instance"
            }
    '''

    # check we have a 'mode' in our event object
    if not 'mode' in event.keys():
        raise ValueError("Required key 'mode' was not found in event object")

    # select function based on 'mode'
    mode = event['mode']
    if mode == 'autoscaling':
        # get name of group from event object
        if 'asg_name' in event.keys():
            return_message = kill_in_asg(event['asg_name'])
        else:
            raise ValueError("Required key 'asg_name' was not found in event object")
    elif mode == 'random_instance':
        # TODO implement
        raise NotImplementedError('random_instance mode is not ready')
    else:
        raise ValueError(f"Unexpected mode '{mode}'")

    return {
      'message': return_message
    }

def kill_in_asg(asg_name):
    ''' Kill a random instance in autoscaling group. 
        Only kill instances that have a LifecycleState of 'InService' and an instance state of 'running'.
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
    if len(candidate_instances) == 0:
        raise RuntimeError(f"Could not find any instances in 'InService' and 'running' state in autoscaling group '{asg_name}'")

    # pick a random instance
    term_instance = choice(candidate_instances)
  
    # terminate instance
    terminate_instance(term_instance)

    return f'Terminated instance: {term_instance} in autoscaling group {asg_name}'

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
    # If the instance given by instanceid doesn't exist, we'll get an IndexError. Catch & reraise it as a more helpful exception.
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

def terminate_instance(instanceid):
    ''' Helper function to terminate ec2 instance '''
    ec2_client.terminate_instances(InstanceIds=[instanceid])