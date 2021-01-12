# WORK IN PROGRESS

This is a [Chaos Monkey](https://github.com/Netflix/chaosmonkey) implementation for AWS Lambda, written in Python.

Chaos lambda can either terminate random instances in specified auto scaling groups, or random instances in the AWS account.

# MVP TODOs
- deployment script
    - add option to print cloudformation template
    - allow runs without config file, or with an empty config file
    - add dry run option
    - lint cron expressions in config file
- documentation
    - high level overview
    - deployment
        - via script
        - manually using cloudformation

# enhancement TODOs
- lambda function
    - add cloudwatch logging on success/failure
    - skip tagged resources
- deployment script
    - cloudwatch log group for cleaner logging
        - remove old cloudwatch log group