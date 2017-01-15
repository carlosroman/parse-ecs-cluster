"""
This script generates a template that deploys the Parse Server as an ECS
service.
"""
from troposphere import Parameter, Ref, Sub, Template
from troposphere.ecs import ContainerDefinition, Environment, LoadBalancer
from troposphere.ecs import LogConfiguration, PortMapping, Service, TaskDefinition
import troposphere.elasticloadbalancingv2 as elb
from troposphere.iam import Policy, Role
from troposphere.logs import LogGroup
import awacs
import awacs.aws
from awacs.aws import Action, Allow, Principal

def main():
    """Generates the CloudFormation template"""
    template = Template()
    template.add_version("2010-09-09")
    template.add_description(
        'This template deploys a Docker image of the parse-server ' +
        'as an ECS serivce')

    # Parameters
    # VPC
    vpc_param = template.add_parameter(Parameter(
        'VPC',
        Type='AWS::EC2::VPC::Id',
        Description='The VPC that the ECS cluster is deployed to',
    ))

    # Cluster
    cluster_param = template.add_parameter(Parameter(
        'Cluster',
        Type='String',
        Description='Please provide the ECS Cluster ID that this service should run on',
    ))

    # DesiredCount
    desired_count_param = template.add_parameter(Parameter(
        'DesiredCount',
        Type='Number',
        Description='How many instances of this task should we run across our cluster?',
        Default='2',
    ))

    # Listener
    listener_param = template.add_parameter(Parameter(
        'Listener',
        Type='String',
        Description='The Application Load Balancer listener to register with',
    ))

    # ParseDockerImage
    parse_docker_image_param = template.add_parameter(Parameter(
        'ParseDockerImage',
        Type='String',
        Description='The Parse Server docker image',
    ))

    # Path
    path_param = template.add_parameter(Parameter(
        'Path',
        Type='String',
        Description='The path to register with the Application Load Balancer',
        Default='/parse',
        AllowedPattern='[\/][a-zA-Z0-9\/]{0,}(?<!\/)',
    ))

    # ApplicationID
    app_name_param = template.add_parameter(Parameter(
        'AppName',
        Type='String',
        Description='Sets the app name',
    ))


    # ApplicationID
    application_id_param = template.add_parameter(Parameter(
        'ApplicationID',
        Type='String',
        Description='Your Parse Application ID',
    ))

    # MasterKey
    master_key_param = template.add_parameter(Parameter(
        'MasterKey',
        Type='String',
        Description='Your Parse Master Key',
        NoEcho=True,
    ))

    # JavascriptKey
    javascript_key_param = template.add_parameter(Parameter(
        'JavascriptKey',
        Type='String',
        Description='The Javascript key for the Javascript SDK',
    ))

    # ClientKey
    client_key_param = template.add_parameter(Parameter(
        'ClientKey',
        Type='String',
        Description='Key for iOS, MacOS, tvOS clients',
    ))

    # RestKey
    rest_key_param = template.add_parameter(Parameter(
        'RestKey',
        Type='String',
        Description='Key for REST calls',
    ))

    # DotNetKey
    dotnet_key_param = template.add_parameter(Parameter(
        'DotNetKey',
        Type='String',
        Description='Key for Unity and .Net SDK',
    ))

    # WebhookKey
    webhook_key_param = template.add_parameter(Parameter(
        'WebhookKey',
        Type='String',
        Description='Key sent with outgoing webhook calls',
    ))

    # Verbose
    verbose_param = template.add_parameter(Parameter(
        'Verbose',
        Type='Number',
        Description='Set the logging to verbose',
        Default='0',
        MinValue='0',
        MaxValue='1',
    ))

    # # Verbose
    # mount_path_param = template.add_parameter(Parameter(
    #     'MountPath',
    #     Type='String',
    #     Description='Mount path for the server, defaults to /parse',
    #     Default='/parse',
    #     AllowedPattern='[\/][a-zA-Z0-9\/]{0,}(?<!\/)'
    # ))

    # MongoDBUsername
    template.add_parameter(Parameter(
        'MongoDBUsername',
        Type='String',
        Description='The Username for MonogDB',
    ))

    # MongoDBUsername
    template.add_parameter(Parameter(
        'MongoDBPassword',
        Type='String',
        Description='The password for MongoDB',
        NoEcho=True,
    ))

    # MongoDBURI
    template.add_parameter(Parameter(
        'MongoDBURI',
        Type='String',
        Description='The MonogoDB driver URI after the @ symbol.',
    ))

    # Resources
    # TaskDefinition
    task_definition = template.add_resource(
        TaskDefinition(
            'TaskDefinition',
            Family='parse-service',
            ContainerDefinitions=[
                ContainerDefinition(
                    Name='parse-service',
                    Essential=True,
                    Environment=[
                        Environment(Name='VERBOSE', Value=Ref(verbose_param)),
                        Environment(Name='PARSE_SERVER_LOGS_FOLDER', Value='null'),
                        Environment(
                            Name='PARSE_SERVER_APP_NAME', Value=Ref(app_name_param)),
                        Environment(
                            Name='PARSE_SERVER_APPLICATION_ID', Value=Ref(application_id_param)),
                        Environment(Name='PARSE_SERVER_MASTER_KEY', Value=Ref(master_key_param)),
                        Environment(
                            Name='PARSE_SERVER_JAVASCRIPT_KEY', Value=Ref(javascript_key_param)),
                        Environment(Name='PARSE_SERVER_CLIENT_KEY', Value=Ref(client_key_param)),
                        Environment(Name='PARSE_SERVER_REST_API_KEY', Value=Ref(rest_key_param)),
                        Environment(Name='PARSE_SERVER_DOT_NET_KEY', Value=Ref(dotnet_key_param)),
                        Environment(Name='PARSE_SERVER_WEBHOOK_KEY', Value=Ref(webhook_key_param)),
                        Environment(Name='PARSE_SERVER_MOUNT_PATH', Value='/parse'),
                        Environment(
                            Name='PARSE_SERVER_DATABASE_URI',
                            Value=
                            Sub('mongodb://${MongoDBUsername}:${MongoDBPassword}@${MongoDBURI}'))
                    ],
                    Image=Ref(parse_docker_image_param),
                    Memory='256',
                    PortMappings=[
                        PortMapping(ContainerPort=1337)
                    ],
                    LogConfiguration=LogConfiguration(
                        LogDriver='awslogs',
                        Options={
                            'awslogs-group': Ref('AWS::StackName'),
                            'awslogs-region': Ref('AWS::Region'),
                            'awslogs-stream-prefix': 'parse-service',
                        }
                    ),
                ),
            ],
        )
    )

    # CloudWatchLogsGroup
    template.add_resource(
        LogGroup(
            'CloudWatchLogsGroup',
            LogGroupName=Ref('AWS::StackName'),
            RetentionInDays=5,
        )
    )

    # ServiceRole
    service_role = template.add_resource(
        Role(
            'ServiceRole',
            RoleName=Sub('ecs-service-${AWS::StackName}'),
            AssumeRolePolicyDocument=awacs.aws.Policy(
                Statement=[
                    awacs.aws.Statement(
                        Effect=Allow,
                        Action=[awacs.aws.Action('sts', 'AssumeRole')],
                        Principal=Principal('Service', ['ecs.amazonaws.com']),
                    ),
                ]
            ),
            Policies=[
                Policy(
                    PolicyName='ecs-service',
                    PolicyDocument=awacs.aws.Policy(
                        Statement=[
                            awacs.aws.Statement(
                                Effect=Allow,
                                Action=[
                                    Action('ec2', 'AuthorizeSecurityGroupIngress'),
                                    Action('ec2', 'Describe*'),
                                    Action('elasticloadbalancing',
                                           'DeregisterInstancesFromLoadBalancer'),
                                    Action('elasticloadbalancing', 'Describe*'),
                                    Action('elasticloadbalancing',
                                           'RegisterInstancesWithLoadBalancer'),
                                    Action('elasticloadbalancing', 'DeregisterTargets'),
                                    Action('elasticloadbalancing', 'DescribeTargetGroups'),
                                    Action('elasticloadbalancing', 'DescribeTargetHealth'),
                                    Action('elasticloadbalancing', 'RegisterTargets'),
                                ],
                                Resource=['*'],
                            ),
                        ],
                    ),
                ),
            ],
        )
    )

    # TargetGroup
    target_group = template.add_resource(
        elb.TargetGroup(
            'TargetGroup',
            VpcId=Ref(vpc_param),
            Port='80',
            Protocol='HTTP',
            Matcher=elb.Matcher(HttpCode='200-299'),
            HealthCheckIntervalSeconds='10',
            HealthCheckPath=Sub('/parse/health'),
            HealthCheckProtocol='HTTP',
            HealthCheckTimeoutSeconds='5',
            HealthyThresholdCount='2',
        )
    )

    # ListenerRule
    template.add_resource(
        elb.ListenerRule(
            'ListenerRule',
            ListenerArn=Ref(listener_param),
            Priority='2',
            Conditions=[
                elb.Condition(Field='path-pattern', Values=[Sub('${Path}/*')])
            ],
            Actions=[
                elb.Action(Type='forward', TargetGroupArn=Ref(target_group))
            ],
        )
    )

    # Service
    template.add_resource(
        Service(
            'Service',
            DependsOn='ListenerRule',
            Cluster=Ref(cluster_param),
            Role=Ref(service_role),
            DesiredCount=Ref(desired_count_param),
            TaskDefinition=Ref(task_definition),
            LoadBalancers=[
                LoadBalancer(
                    ContainerName='parse-service',
                    ContainerPort='1337',
                    TargetGroupArn=Ref(target_group))],
        )
    )

    print(template.to_json())


if __name__ == '__main__':
    main()
