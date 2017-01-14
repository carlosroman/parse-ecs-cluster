"""
This scipt creates the template that deploys an Application Load Balancer
that exposes our various ECS services.
We create them it a seperate nested template, so it can be referenced by
all of the other nested templates.
"""
from troposphere import GetAtt, Join, Output, Parameter, Template, Ref, Sub
import troposphere.elasticloadbalancingv2 as elb

def main():
    """Generates the CloudFormation template"""
    template = Template()

    template.add_version("2010-09-09")

    # Parameters
    # EnvironmentName
    env_name_param = template.add_parameter(Parameter(
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

    # Subnets
    subnets_param = template.add_parameter(Parameter(
        'Subnets',
        Type='List<AWS::EC2::Subnet::Id>',
        Description='Choose which subnets the Applicaion Load Balancer should be deployed to',
    ))

    # SecurityGroup
    sg_param = template.add_parameter(Parameter(
        'SecurityGroup',
        Type='AWS::EC2::SecurityGroup::Id',
        Description='Select the Security Group to apply to the Applicaion Load Balancer',
    ))

    # Resources
    # LoadBalancer
    load_balancer = template.add_resource(elb.LoadBalancer(
        'LoadBalancer',
        Name=Ref(env_name_param),
        Subnets=Ref(subnets_param),
        SecurityGroups=[Ref(sg_param)],
        Tags=[{'Key': 'Name', 'Value' : Sub('${EnvironmentName}')}]
    ))

    # DefaultTargetGroup
    dflt_trg_grp = template.add_resource(elb.TargetGroup(
        'DefaultTargetGroup',
        Name='default',
        VpcId=Ref(vpc_param),
        Port='80',
        Protocol='HTTP'
    ))

    # LoadBalancerListener
    load_balancer_listner = template.add_resource(elb.Listener(
        'LoadBalancerListener',
        LoadBalancerArn=Ref(load_balancer),
        Port='80',
        Protocol='HTTP',
        DefaultActions=[elb.Action(
            Type='forward',
            TargetGroupArn=Ref(dflt_trg_grp)
        )]
    ))
    # Output
    # LoadBalancer
    template.add_output(Output(
        'LoadBalancer',
        Description='A reference to the Application Load Balancer',
        Value=Ref(load_balancer),
    ))

    template.add_output(Output(
        'LoadBalancerUrl',
        Description='The URL of the ALB',
        Value=Join("", ["http://", GetAtt(load_balancer, "DNSName")]),
    ))

    template.add_output(Output(
        'Listener',
        Description='A reference to a port 80 listener',
        Value=Ref(load_balancer_listner),
    ))

    print(template.to_json())

if __name__ == '__main__':
    main()
