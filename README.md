# WORK IN PROGRESS

This is a [Chaos Monkey](https://github.com/Netflix/chaosmonkey) implementation for AWS Lambda, written in Python.

Chaos lambda can either terminate random instances in specified auto scaling groups, or random instances in the AWS account.

# TODO
- deployment script
    - cloudwatch log group
- add cloudwatch logging on success/failure