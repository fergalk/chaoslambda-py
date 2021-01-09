# WORK IN PROGRESS

This is a [Chaos Monkey](https://github.com/Netflix/chaosmonkey) implementation for AWS Lambda, written in Python.

Chaos lambda randomly terminates EC2 instances in autoscaling groups.

# TODO
- deployment script/cloudformation template
    - deploy lambda
    - cloudwatch rule to trigger
    - cloudwatch log group
- testing
- add cloudwatch logging on success/failure