from aws_cdk import (
    aws_ec2 as ec2,
    aws_iam as iam,
    App, Stack, CfnOutput,
    aws_autoscaling as autoscaling,
    aws_elasticloadbalancingv2 as elb,
)
from constructs import Construct


with open("cdk/cdk_vpc_ec2/user_data.sh", "r", encoding="utf-8") as file:
    user_data = file.read()

keyname = "streamline.pem"
ec2_type = "t2.micro"
linux_ami = ec2.AmazonLinuxImage(generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX,
                                 edition=ec2.AmazonLinuxEdition.STANDARD,
                                 virtualization=ec2.AmazonLinuxVirt.HVM,
                                 storage=ec2.AmazonLinuxStorage.GENERAL_PURPOSE
                                 )


class CdkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # VPC
        vpc = ec2.Vpc(self, "streamline-vpc",
            nat_gateways=0,
            subnet_configuration=[ec2.SubnetConfiguration(name="public",subnet_type=ec2.SubnetType.PUBLIC)]
            )

        # Security Group for ec2 instances for asg
        sg_ec2 = ec2.SecurityGroup(self, id="streamline-sg-ec2-instances",
                               vpc=vpc,
                               allow_all_outbound=True,
                           )

        sg_ec2.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(22),
            description="Allow ssh from anywhere"
        )

         # Security group for load balancer
        sg_alb = ec2.SecurityGroup(
            self,
            id = "streamline-sg-alb",
            vpc = vpc,
        )

        sg_alb.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(443),
            description="Allow HTTPS traffic from internet"
        )

        sg_alb.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(80),
            description="Allow HTTP traffic from internet"
        )

        sg_alb.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(22),
            description="Allow SSH traffic from internet"
        )

        # Instance Role and SSM Managed Policy
        role = iam.Role(self, "InstanceSSM", assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"))

        role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore"))

        # Create ALB
        alb = elb.ApplicationLoadBalancer(self, "streamline-alb",
                                          vpc=vpc,
                                          internet_facing=True,
                                          load_balancer_name="streamline-alb"
                                          )

        alb.connections.allow_from_any_ipv4(
        ec2.Port.tcp(80),
            "Internet access ALB 80"
            )

        alb.connections.allow_from_any_ipv4(
        ec2.Port.tcp(443),
            "Internet access ALB 443"
            )

        listener_80 = alb.add_listener("my80",
                                    port=80,
                                    open=True)

        self.asg = autoscaling.AutoScalingGroup(self, "myASG",
                                                vpc=vpc,
                                                vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
                                                instance_type=ec2.InstanceType(instance_type_identifier=ec2_type),
                                                machine_image=linux_ami,
                                                key_name=keyname,
                                                user_data=ec2.UserData.custom(user_data),
                                                desired_capacity=2,
                                                min_capacity=2,
                                                max_capacity=4,
                                                )

        self.asg.connections.allow_from(alb, ec2.Port.tcp(80), "ALB access 80 port of EC2 in Autoscaling Group")

        listener_80.add_targets("addTargetGroup",
                             port=80,
                             targets=[self.asg])

        CfnOutput(self, "Output",
                       value=alb.load_balancer_dns_name)


app = App()
CdkStack(app, "streamline-ec2-stack")

app.synth()