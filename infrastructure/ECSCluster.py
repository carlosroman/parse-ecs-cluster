"""
This script generates a template that deploys an ECS cluster
to the provided VPC and subnets using an Auto Scaling Group
"""
from troposphere import Base64, FindInMap, Join, Output
from troposphere import Parameter, Ref, Sub, Template
from troposphere.cloudformation import Init, InitConfig, InitFiles, InitFile
from troposphere.cloudformation import InitServices, InitService
from troposphere.autoscaling import LaunchConfiguration
from troposphere.iam import Policy, Role
from troposphere.ecs import Cluster
from troposphere.autoscaling import AutoScalingGroup, Metadata
from troposphere.autoscaling import Tags as ASTags
from troposphere.policies import AutoScalingRollingUpdate, CreationPolicy
from troposphere.policies import ResourceSignal, UpdatePolicy
from troposphere.iam import InstanceProfile
import awacs
import awacs.aws

def main():
    """Generates the CloudFormation template"""
    template = Template()
    template.add_version('2010-09-09')
    template.add_description(
        'This template deploys an ECS cluster to the ' +
        'provided VPC and subnets using an Auto Scaling Group')

    # Parameters
    # EnvironmentName
    env_name_param = template.add_parameter(Parameter(
        'EnvironmentName',
        Type='String',
        Description='An environment name that will be prefixed to resource names',
    ))

    # InstanceType
    instance_type_param = template.add_parameter(Parameter(
        'InstanceType',
        Type='String',
        Default='t2.nano',
        Description='Which instance type should we use to build the ECS cluster?',
        AllowedValues=[
            't2.nano', 't2.micro', 't2.small', 't2.medium', 't2.large', 't2.xlarge', 't2.2xlarge',
        ],
    ))

    # ClusterSize
    cluster_size_param = template.add_parameter(Parameter(
        'ClusterSize',
        Type='Number',
        Description='How many ECS hosts do you want to initially deploy?',
        Default='1',
    ))

    # VPC
    template.add_parameter(Parameter(
        'VPC',
        Type='AWS::EC2::VPC::Id',
        Description='Choose which VPC this ECS cluster should be deployed to',
    ))

    # Subnets
    subnets_param = template.add_parameter(Parameter(
        'Subnets',
        Type='List<AWS::EC2::Subnet::Id>',
        Description='Choose which subnets this ECS cluster should be deployed to',
    ))

    # SecurityGroup
    sg_param = template.add_parameter(Parameter(
        'SecurityGroup',
        Type='AWS::EC2::SecurityGroup::Id',
        Description='Select the Security Group to use for the ECS cluster hosts',
    ))

    # Mappings
    # AWSRegionToAMI
    template.add_mapping(
        'AWSRegionToAMI',
        {
            'us-east-1' : {'AMI': 'ami-a58760b3'},
            'us-east-2' : {'AMI': 'ami-a6e4bec3'},
            'us-west-1' : {'AMI': 'ami-74cb9b14'},
            'us-west-2' : {'AMI': 'ami-5b6dde3b'},
            'eu-west-1' : {'AMI': 'ami-e3fbd290'},
            'eu-west-2' : {'AMI': 'ami-77f6fc13'},
            'eu-central-1' : {'AMI': 'ami-38dc1157'},
            'ap-northeast-1' : {'AMI': 'ami-30bdce57'},
            'ap-southeast-1' : {'AMI': 'ami-9f75ddfc'},
            'ap-southeast-2' : {'AMI': 'ami-cf393cac'},
            'ca-central-1' : {'AMI': 'ami-1b01b37f'},
        },
    )

    # Resources
    ecs_role = template.add_resource(Role(
        'ECSRole',
        Path='/',
        RoleName=Sub('${EnvironmentName}-ECSRole-${AWS::Region}'),
        AssumeRolePolicyDocument=awacs.aws.Policy(
            Statement=[
                awacs.aws.Statement(
                    Effect=awacs.aws.Allow,
                    Action=[awacs.aws.Action('sts', 'AssumeRole')],
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

    ecs_instance_profile = template.add_resource(InstanceProfile(
        'ECSInstanceProfile',
        Path='/',
        Roles=[Ref(ecs_role)],
    ))

    # ECSCluster
    ecs_cluster = template.add_resource(Cluster(
        'ECSCluster',
        ClusterName=Ref(env_name_param),
    ))

    instance_metadata = Metadata(
        Init({
            'config': InitConfig(
                commands={
                    '01_add_instance_to_cluster': {
                        'command': Join(
                            '',
                            ['#!/bin/bash\n',
                             'echo ECS_CLUSTER=', Ref(ecs_cluster),
                             ' >> /etc/ecs/ecs.config'])
                    },
                },
                files=InitFiles({
                    '/etc/cfn/cfn-hup.conf': InitFile(
                        mode='000400',
                        owner='root',
                        group='root',
                        content=Join(
                            '',
                            ['[main]\n',
                             'stack=',
                             Ref('AWS::StackId'), '\n',
                             'region=', Ref('AWS::Region'), '\n']),
                    ),
                    '/etc/cfn/hooks.d/cfn-auto-reloader.conf': InitFile(
                        mode='000400',
                        owner='root',
                        group='root',
                        content=Join('', [
                            '[cfn-auto-reloader-hook]\n',
                            'triggers=post.update\n',
                            'path=Resources.ContainerInstances.Metadata.AWS::CloudFormation::Init\n'
                            'action=/opt/aws/bin/cfn-init -v --region ', Ref('AWS::Region'),
                            ' --stack ', Ref('AWS::StackId'),
                            ' --resource ECSLaunchConfiguration\n']),
                    )
                }),
                services=InitServices({
                    'cfn-hup': InitService(
                        enabled='true',
                        ensureRunning='true',
                        files=[
                            '/etc/cfn/cfn-hup.conf',
                            '/etc/cfn/hooks.d/cfn-auto-reloader.conf']
                    )
                }),
            )
        })
    )

    ecs_launch_config = template.add_resource(LaunchConfiguration(
        'ECSLaunchConfiguration',
        ImageId=FindInMap('AWSRegionToAMI', Ref('AWS::Region'), 'AMI'),
        InstanceType=Ref(instance_type_param),
        SecurityGroups=[Ref(sg_param)],
        IamInstanceProfile=Ref(ecs_instance_profile),
        UserData=Base64(Join('', [
            '#!/bin/bash\n',
            'yum install -y aws-cfn-bootstrap\n',
            '/opt/aws/bin/cfn-init -v --region ', Ref('AWS::Region'),
            ' --stack ', Ref('AWS::StackName'), ' --resource ECSLaunchConfiguration\n',
            '/opt/aws/bin/cfn-signal -e $? --region ', Ref('AWS::Region'),
            ' --stack ', Ref('AWS::StackName'), ' --resource ECSAutoScalingGroup\n',
        ])),
        Metadata=instance_metadata,
    ))

    # ECSAutoScalingGroup:
    template.add_resource(AutoScalingGroup(
        'ECSAutoScalingGroup',
        VPCZoneIdentifier=Ref(subnets_param),
        LaunchConfigurationName=Ref(ecs_launch_config),
        MinSize=Ref(cluster_size_param),
        MaxSize=Ref(cluster_size_param),
        DesiredCapacity=Ref(cluster_size_param),
        Tags=ASTags(Name=(Sub('${EnvironmentName} ECS host'), True)),
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

    # Output
    template.add_output(Output(
        'Cluster',
        Description='A reference to the ECS cluster',
        Value=Ref(ecs_cluster),
    ))
    print(template.to_json())

if __name__ == '__main__':
    main()
