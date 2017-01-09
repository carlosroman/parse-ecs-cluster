from troposphere import Base64, FindInMap, GetAtt, GetAZs, Join, Output
from troposphere import Parameter, Ref, Tags, Template
from troposphere.cloudformation import Init, InitConfig, InitFiles, InitFile
from troposphere.cloudformation import InitServices, InitService
from troposphere.iam import PolicyType
from troposphere.autoscaling import LaunchConfiguration
from troposphere.iam import Policy, Role
from troposphere.ecs import Cluster
from troposphere.autoscaling import AutoScalingGroup, Metadata
from troposphere.autoscaling import Tags as ASTags
from troposphere.policies import AutoScalingRollingUpdate, CreationPolicy, ResourceSignal, UpdatePolicy
from troposphere.iam import InstanceProfile
import awacs
import awacs.aws

t = Template()
t.add_version('2010-09-09')
t.add_description('This template deploys an ECS cluster to the provided VPC and subnets using an Auto Scaling Group')

# Parameters
# EnvironmentName
env_name_param = t.add_parameter(Parameter(
  'EnvironmentName',
  Type='String',
  Description='An environment name that will be prefixed to resource names',
))

# InstanceType
instance_type_param = t.add_parameter(Parameter(
  'InstanceType',
  Type='String',
  Default='t2.nano',
  Description='Which instance type should we use to build the ECS cluster?',
  AllowedValues=[
    't2.nano', 't2.micro', 't2.small', 't2.medium', 't2.large', 't2.xlarge', 't2.2xlarge',
  ],
))

# ClusterSize
cluster_size_param = t.add_parameter(Parameter(
  'ClusterSize',
  Type='Number',
  Description='How many ECS hosts do you want to initially deploy?',
  Default='1',
))

# VPC
vpc_param = t.add_parameter(Parameter(
  'VPC',
  Type='AWS::EC2::VPC::Id',
  Description='Choose which VPC this ECS cluster should be deployed to',
))

# Subnets
subnets_param = t.add_parameter(Parameter(
  'Subnets',
  Type='List<AWS::EC2::Subnet::Id>',
  Description='Choose which subnets this ECS cluster should be deployed to',
))

# SecurityGroup
sg_param = t.add_parameter(Parameter(
  'SecurityGroup',
  Type='AWS::EC2::SecurityGroup::Id',
  Description='Select the Security Group to use for the ECS cluster hosts',
))

# Mappings
# AWSRegionToAMI
t.add_mapping(
  'AWSRegionToAMI',
  {
    'us-east-1' : { 'AMI': 'ami-6df8fe7a'},
    'us-east-2' : { 'AMI': 'ami-c6b5efa3'},
    'us-west-1' : { 'AMI': 'ami-1eda8d7e'},
    'us-west-2' : { 'AMI': 'ami-a2ca61c2'},
    'eu-west-1' : { 'AMI': 'ami-ba346ec9'},
    'eu-west-2' : { 'AMI': 'ami-42c5cf26'},
    'eu-central-1' : { 'AMI': 'ami-e012d48f'},
    'ap-northeast-1' : { 'AMI': 'ami-08f7956f'},
    'ap-southeast-1' : { 'AMI': 'ami-f4832f97'},
    'ap-southeast-2' : { 'AMI': 'ami-774b7314'},
    'ca-central-1' : { 'AMI': 'ami-be45f7da'},
  },
)

# Resources
ECSRole = t.add_resource(Role(
  'ECSRole',
  Path='/',
  AssumeRolePolicyDocument=awacs.aws.Policy(
    Statement=[
      awacs.aws.Statement(
        Effect=awacs.aws.Allow,
        Action=[awacs.aws.Action('sts','AssumeRole')],
        Principal=awacs.aws.Principal('Service', ['ec2.amazonaws.com']),
      ),
    ]
  ),
  Policies=[
    Policy(
      PolicyName='ecs-service',
      PolicyDocument=awacs.aws.Policy(
         Statement=[
           awacs.aws.Statement(
             Effect=awacs.aws.Allow,
             Action=[
               awacs.aws.Action('ecs', 'CreateCluster'),
               awacs.aws.Action('ecs', 'DeregisterContainerInstance'),
               awacs.aws.Action('ecs', 'DiscoverPollEndpoint'),
               awacs.aws.Action('ecs', 'Poll'),
               awacs.aws.Action('ecs', 'RegisterContainerInstance'),
               awacs.aws.Action('ecs', 'StartTelemetrySession'),
               awacs.aws.Action('ecs', 'Submit*'),
               awacs.aws.Action('logs', 'CreateLogStream'),
               awacs.aws.Action('ecr', 'BatchCheckLayerAvailability'),
               awacs.aws.Action('ecr', 'BatchGetImage'),
               awacs.aws.Action('ecr', 'GetDownloadUrlForLayer'),
               awacs.aws.Action('ecr', 'GetAuthorizationToken'),
             ],
             Resource=['*'],
           ),
         ],
      ),
    ),
  ],
))

EC2InstanceProfile = t.add_resource(InstanceProfile(
  'ECSInstanceProfile',
  Path='/',
  Roles=[Ref('ECSRole')],
))

instance_metadata = Metadata(
  Init({
    'config': InitConfig(
      commands={},
      files=InitFiles({
        '/etc/cfn/cfn-hup.conf': InitFile(
          mode='000400',
          owner='root',
          group='root',
          content=Join('', ['[main]\n', 'stack=', Ref('AWS::StackId'), '\n', 'region=', Ref('AWS::Region'), '\n']),
        ),
        '/etc/cfn/hooks.d/cfn-auto-reloader.conf': InitFile(
          mode='000400',
          owner='root',
          group='root',
          content=Join('', [
            '[cfn-auto-reloader-hook]\n', 
            'triggers=post.update\n', 
            'path=Resources.ContainerInstances.Metadata.AWS::CloudFormation::Init\n'
            'action=/opt/aws/bin/cfn-init -v --region ', Ref('AWS::Region'), ' --stack ', Ref('AWS::StackId'), ' --resource ECSLaunchConfiguration\n']),
        )
      }),
      services=InitServices({
        'cfn-hup': InitService(
          enabled='true',
          ensureRunning='true',
          files=['/etc/cfn/cfn-hup.conf', '/etc/cfn/hooks.d/cfn-auto-reloader.conf']
        )
      }),
    )
  })
)

ECSLaunchConfiguration = t.add_resource(LaunchConfiguration(
  'ECSLaunchConfiguration',
  ImageId=FindInMap('AWSRegionToAMI', Ref('AWS::Region'), 'AMI'),
  InstanceType=Ref(instance_type_param),
  SecurityGroups=Ref(sg_param),
  IamInstanceProfile=Ref(EC2InstanceProfile),
  UserData=Base64(Join('',[
    '#!/bin/bash\n',
    'yum install -y aws-cfn-bootstrap\n',
    '/opt/aws/bin/cfn-init -v --region ', Ref('AWS::Region'), ' --stack ', Ref('AWS::StackName'), '--resource ECSLaunchConfiguration\n',
    '/opt/aws/bin/cfn-signal -e $? --region ', Ref('AWS::Region'), ' --stack ', Ref('AWS::StackName'), '--resource ECSAutoScalingGroup\n',
  ])),
  Metadata=instance_metadata,
))
# ECSCluster
ECSCluster = t.add_resource(Cluster(
  'ECSCluster',
  ClusterName=Ref(env_name_param), 
))

# ECSAutoScalingGroup:
ECSAutoScalingGroup = t.add_resource(AutoScalingGroup(
  'ECSAutoScalingGroup',
  VPCZoneIdentifier=Ref(subnets_param),
  LaunchConfigurationName=Ref(ECSLaunchConfiguration),
  MinSize=Ref(cluster_size_param),
  MaxSize=Ref(cluster_size_param),
  DesiredCapacity=Ref(cluster_size_param),
  Tags=[
    ASTags(Name=('test',True))
  ],
  CreationPolicy=CreationPolicy(
    ResourceSignal=ResourceSignal(
      Timeout='PT15M'
    ),
  ),
  UpdatePolicy=UpdatePolicy(
    AutoScalingRollingUpdate=AutoScalingRollingUpdate(
      MinInstancesInService='1',
      MaxBatchSize='1',
      PauseTime='PT15M',
      WaitOnResourceSignals=True,
    )
  ),  
))

print(t.to_json())
