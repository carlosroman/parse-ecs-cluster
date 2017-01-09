from troposphere import Base64, Join
from troposphere import Parameter, Ref, Template
from troposphere.cloudformation import Init, InitConfig, InitFiles, InitFile
from troposphere.cloudformation import InitServices, InitService
from troposphere.iam import PolicyType
from troposphere.autoscaling import LaunchConfiguration
from troposphere.iam import Role
from troposphere.ecs import Cluster
from troposphere.autoscaling import AutoScalingGroup, Metadata
from troposphere.iam import InstanceProfile

t = Template()
t.add_version('2010-09-09')
t.add_description('This template deploys an ECS cluster to the provided VPC and subnets using an Auto Scaling Group')

# EnvironmentName
t.add_parameter(Parameter(
  'EnvironmentName',
  Type='String',
  Description='An environment name that will be prefixed to resource names',
))

# InstanceType
t.add_parameter(Parameter(
  'InstanceType',
  Type='String',
  Default='t2.nano',
  Description='Which instance type should we use to build the ECS cluster?',
  AllowedValues=[
    't2.nano', 't2.micro', 't2.small', 't2.medium', 't2.large', 't2.xlarge', 't2.2xlarge',
  ],
))

# ClusterSize
t.add_parameter(Parameter(
  'ClusterSize',
  Type='Number',
  Description='How many ECS hosts do you want to initially deploy?',
  Default='1',
))

# VPC
t.add_parameter(Parameter(
  'VPC',
  Type='AWS::EC2::VPC::Id',
  Description='Choose which VPC this ECS cluster should be deployed to',
))

# Subnets
t.add_parameter(Parameter(
  'Subnets',
  Type='List<AWS::EC2::Subnet::Id>',
  Description='Choose which subnets this ECS cluster should be deployed to',
))

# SecurityGroup
t.add_parameter(Parameter(
  'SecurityGroup',
  Type='AWS::EC2::SecurityGroup::Id',
  Description='Select the Security Group to use for the ECS cluster hosts',
))



print(t.to_json())
