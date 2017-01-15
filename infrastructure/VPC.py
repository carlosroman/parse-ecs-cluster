"""
This script generates a template deploys a VPC, with a pair of public and
private subnets spread across two Availabilty Zones. It deploys an Internet
Gateway, with a default route on the public subnets. It deploys a pair of
NAT Gateways (one in each AZ), and default routes for them in the private subnets.
"""
from troposphere import GetAtt, GetAZs, Join, Output, Parameter
from troposphere import Ref, Select, Sub, Tags, Template
from troposphere.ec2 import EIP, InternetGateway, NatGateway
from troposphere.ec2 import Subnet, SubnetRouteTableAssociation
from troposphere.ec2 import Route, RouteTable, VPC, VPCGatewayAttachment

def main():
    """Generates the CloudFormation template"""
    template = Template()

    template.add_version("2010-09-09")

    template.add_description(
        'This template deploys a VPC, with a pair of public and private subnets spread ' +
        'across two Availabilty Zones. It deploys an Internet Gateway, with a default ' +
        'route on the public subnets. It deploys a pair of NAT Gateways (one in each AZ), ' +
        'and default routes for them in the private subnets.'
    )
    # Parameters
    # EnvironmentName
    env_param = template.add_parameter(Parameter(
        'EnvironmentName',
        Type='String',
        Description='An environment name that will be prefixed to resource names',
    ))

    # VPC CIDR
    vpc_cidr_param = template.add_parameter(Parameter(
        'VpcCIDR',
        Type='String',
        Description='Please enter the IP range (CIDR notation) for this VPC',
        Default='10.192.0.0/16',
    ))

    # PublicSubnet1CIDR
    pub_subnet_1_param = template.add_parameter(Parameter(
        'PublicSubnet1CIDR',
        Type='String',
        Description='Please enter the IP range (CIDR notation) for the public subnet ' +
        'in the first Availability Zone',
        Default='10.192.10.0/24',
    ))

    # PublicSubnet2CIDR
    pub_subnet_2_param = template.add_parameter(Parameter(
        'PublicSubnet2CIDR',
        Type='String',
        Description='Please enter the IP range (CIDR notation) for the public subnet ' +
        'in the second Availability Zone',
        Default='10.192.11.0/24',
    ))

    # PrivateSubnet1CIDR
    prvt_subnet_1_param = template.add_parameter(Parameter(
        'PrivateSubnet1CIDR',
        Type='String',
        Description='Please enter the IP range (CIDR notation) for the private subnet ' +
        'in the first Availability Zone',
        Default='10.192.20.0/24',
    ))

    # PrivateSubnet2CIDR
    prvt_subnet_2_param = template.add_parameter(Parameter(
        'PrivateSubnet2CIDR',
        Type='String',
        Description='Please enter the IP range (CIDR notation) for the private subnet ' +
        'in the second Availability Zone',
        Default='10.192.21.0/24',
    ))

    # Resources
    # VPC
    vpc = template.add_resource(
        VPC(
            'VPC',
            CidrBlock=Ref(vpc_cidr_param),
            Tags=Tags(Name=Ref(env_param)),
        )
    )

    # InternetGateway
    internet_gateway = template.add_resource(
        InternetGateway(
            'InternetGateway',
            Tags=Tags(Name=Ref(env_param)),
        )
    )

    # InternetGatewayAttachment
    template.add_resource(
        VPCGatewayAttachment(
            'InternetGatewayAttachment',
            InternetGatewayId=Ref(internet_gateway),
            VpcId=Ref(vpc),
        )
    )

    # PublicSubnet1
    pub_subnet1 = template.add_resource(
        Subnet(
            'PublicSubnet1',
            VpcId=Ref(vpc),
            AvailabilityZone=Select('0', GetAZs("")),
            CidrBlock=Ref(pub_subnet_1_param),
            MapPublicIpOnLaunch=False,
            Tags=Tags(Name=Sub('${EnvironmentName} Public Subnet (AZ1)')),
        )
    )

    # PublicSubnet2
    pub_subnet2 = template.add_resource(
        Subnet(
            'PublicSubnet2',
            VpcId=Ref(vpc),
            AvailabilityZone=Select('1', GetAZs("")),
            CidrBlock=Ref(pub_subnet_2_param),
            MapPublicIpOnLaunch=False,
            Tags=Tags(Name=Sub('${EnvironmentName} Public Subnet (AZ2)')),
        )
    )

    # PrivateSubnet1
    prvt_subnet1 = template.add_resource(
        Subnet(
            'PrivateSubnet1',
            VpcId=Ref(vpc),
            AvailabilityZone=Select('0', GetAZs("")),
            CidrBlock=Ref(prvt_subnet_1_param),
            MapPublicIpOnLaunch=False,
            Tags=Tags(Name=Sub('${EnvironmentName} Private Subnet (AZ1)')),
        )
    )

    # PrivateSubnet2
    prvt_subnet2 = template.add_resource(
        Subnet(
            'PrivateSubnet2',
            VpcId=Ref(vpc),
            AvailabilityZone=Select('1', GetAZs("")),
            CidrBlock=Ref(prvt_subnet_2_param),
            MapPublicIpOnLaunch=False,
            Tags=Tags(Name=Sub('${EnvironmentName} Private Subnet (AZ2)')),
        )
    )

    # NatGateway1EIP
    nat_gateway1_eip = template.add_resource(
        EIP(
            'NatGateway1EIP',
            DependsOn='InternetGatewayAttachment',
            Domain='vpc',
        )
    )

    # NatGateway2EIP
    nat_gateway2_eip = template.add_resource(
        EIP(
            'NatGateway2EIP',
            DependsOn='InternetGatewayAttachment',
            Domain='vpc',
        )
    )

    # NatGateway1
    nat_gateway1 = template.add_resource(
        NatGateway(
            'NatGateway1',
            AllocationId=GetAtt(nat_gateway1_eip, 'AllocationId'),
            SubnetId=Ref(pub_subnet1),
        )
    )

    # NatGateway2
    nat_gateway2 = template.add_resource(
        NatGateway(
            'NatGateway2',
            AllocationId=GetAtt(nat_gateway2_eip, 'AllocationId'),
            SubnetId=Ref(pub_subnet2),
        )
    )

    # PublicRouteTable
    pub_route_table = template.add_resource(
        RouteTable(
            'PublicRouteTable',
            VpcId=Ref(vpc),
            Tags=Tags(Name=Sub('${EnvironmentName} Public Routes')),
        )
    )

    # DefaultPublicRoute
    template.add_resource(
        Route(
            'DefaultPublicRoute',
            RouteTableId=Ref(pub_route_table),
            DestinationCidrBlock='0.0.0.0/0',
            GatewayId=Ref(internet_gateway),
        )
    )

    # PublicSubnet1RouteTableAssociation
    template.add_resource(
        SubnetRouteTableAssociation(
            'PublicSubnet1RouteTableAssociation',
            RouteTableId=Ref(pub_route_table),
            SubnetId=Ref(pub_subnet1),
        )
    )

    # PublicSubnet2RouteTableAssociation
    template.add_resource(
        SubnetRouteTableAssociation(
            'PublicSubnet2RouteTableAssociation',
            RouteTableId=Ref(pub_route_table),
            SubnetId=Ref(pub_subnet2),
        )
    )

    # PrivateRouteTable1
    prvt_route_table1 = template.add_resource(
        RouteTable(
            'PrivateRouteTable1',
            VpcId=Ref(vpc),
            Tags=Tags(Name=Sub('${EnvironmentName} Private Routes (AZ1)')),
        )
    )

    # DefaultPrivateRoute1
    template.add_resource(
        Route(
            'DefaultPrivateRoute1',
            RouteTableId=Ref(prvt_route_table1),
            DestinationCidrBlock='0.0.0.0/0',
            NatGatewayId=Ref(nat_gateway1),
        )
    )

    # PrivateSubnet1RouteTableAssociation
    template.add_resource(
        SubnetRouteTableAssociation(
            'PrivateSubnet1RouteTableAssociation',
            RouteTableId=Ref(prvt_route_table1),
            SubnetId=Ref(prvt_subnet1),
        )
    )

    # PrivateRouteTable2
    prvt_route_table2 = template.add_resource(
        RouteTable(
            'PrivateRouteTable2',
            VpcId=Ref(vpc),
            Tags=Tags(Name=Sub('${EnvironmentName} Private Routes (AZ2)')),
        )
    )

    # DefaultPrivateRoute2
    template.add_resource(
        Route(
            'DefaultPrivateRoute2',
            RouteTableId=Ref(prvt_route_table2),
            DestinationCidrBlock='0.0.0.0/0',
            NatGatewayId=Ref(nat_gateway2),
        )
    )

    # PrivateSubnet1RouteTableAssociation
    template.add_resource(
        SubnetRouteTableAssociation(
            'PrivateSubnet2RouteTableAssociation',
            RouteTableId=Ref(prvt_route_table2),
            SubnetId=Ref(prvt_subnet2),
        )
    )

    # Outputs
    template.add_output(Output(
        'VPC',
        Description='A reference to the created VPC',
        Value=Ref(vpc),
    ))

    template.add_output(Output(
        'PublicSubnets',
        Description='A list of the public subnets',
        Value=Join(',', [Ref(pub_subnet1), Ref(pub_subnet2)]),
    ))

    template.add_output(Output(
        'PrivateSubnets',
        Description='A list of the private subnets',
        Value=Join(',', [Ref(prvt_subnet1), Ref(prvt_subnet2)]),
    ))

    template.add_output(Output(
        'PublicSubnet1',
        Description='A reference to the public subnet in the 1st Availability Zone',
        Value=Ref(pub_subnet1),
    ))

    template.add_output(Output(
        'PublicSubnet2',
        Description='A reference to the public subnet in the 2nd Availability Zone',
        Value=Ref(pub_subnet2),
    ))

    template.add_output(Output(
        'PrivateSubnet1',
        Description='A reference to the private  subnet in the 1st Availability Zone',
        Value=Ref(prvt_subnet1),
    ))

    template.add_output(Output(
        'PrivateSubnet2',
        Description='A reference to the private  subnet in the 2nd Availability Zone',
        Value=Ref(prvt_subnet2),
    ))

    print(template.to_json())


if __name__ == '__main__':
    main()
