"""
This script generates a template that contains the security groups
required by our entire stack. We create them in a seperate nested
template, so they can be referenced by all of the other nested
templates.
"""
from troposphere import Output, Parameter, Template, Ref, Sub
from troposphere.ec2 import SecurityGroup, SecurityGroupRule


def main():
    """Generates the CloudFormation template"""
    template = Template()

    template.add_version("2010-09-09")

    template.add_description(
        'This template contains the security groups required by our '+
        'entire stack. We create them in a seperate nested template, '+
        'so they can be referenced by all of the other nested templates')

    # Parameters
    # EnvironmentName
    template.add_parameter(Parameter(
        'EnvironmentName',
        Type='String',
        Description='An environment name that will be prefixed to resource names',
    ))

    # VPC
    vpc_param = template.add_parameter(Parameter(
        'VPC',
        Type='AWS::EC2::VPC::Id',
        Description='Choose which VPC this ECS cluster should be deployed to',
    ))

    # Resources
    # LoadBalancerSecurityGroup
    elb_security_group = template.add_resource(SecurityGroup(
        'LoadBalancerSecurityGroup',
        VpcId=Ref(vpc_param),
        GroupDescription='Access to the load balancer that sits in front of ECS',
        SecurityGroupIngress=[SecurityGroupRule(CidrIp='0.0.0.0/0', IpProtocol='-1',)],
        Tags=[{'Key': 'Name', 'Value' : Sub('${EnvironmentName}-LoadBalancers')}]
    ))
    # ECSHostSecurityGroup
    ecs_security_group = template.add_resource(SecurityGroup(
        'ECSHostSecurityGroup',
        VpcId=Ref(vpc_param),
        GroupDescription='Access to the ECS hosts and the tasks/containers that run on them',
        SecurityGroupIngress=[
            SecurityGroupRule(SourceSecurityGroupId=Ref(elb_security_group), IpProtocol='-1',)
        ],
        Tags=[{'Key': 'Name', 'Value' : Sub('${EnvironmentName}-ECS-Hosts')}]
    ))

    # Output
    template.add_output(Output(
        'ECSHostSecurityGroup',
        Description='A reference to the security group for ECS hosts',
        Value=Ref(ecs_security_group),
    ))

    template.add_output(Output(
        'LoadBalancerSecurityGroup',
        Description='A reference to the security group for load balancers',
        Value=Ref(elb_security_group),
    ))
    print(template.to_json())


if __name__ == '__main__':
    main()
