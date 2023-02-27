from aws_cdk import (
    aws_ec2 as ec2,
    aws_iam as iam,
    App, Stack
)
from constructs import Construct

class CdkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # VPC
        vpc = ec2.Vpc(self, "VPC",
            nat_gateways=0,
            subnet_configuration=[ec2.SubnetConfiguration(name="public",subnet_type=ec2.SubnetType.PUBLIC)]
            )

        # AMI
        amzn_linux = ec2.MachineImage.latest_amazon_linux(
            generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2,
            edition=ec2.AmazonLinuxEdition.STANDARD,
            virtualization=ec2.AmazonLinuxVirt.HVM,
            storage=ec2.AmazonLinuxStorage.GENERAL_PURPOSE
            )

        # Instance Role and SSM Managed Policy
        role = iam.Role(self, "InstanceSSM", assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"))

        role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore"))


        # Create 4 ec2 instances
        for i in range(4):
            instance = ec2.Instance(
                self, f"streamline-ws{i+1}",
                instance_type=ec2.InstanceType("t2.micro"),
                machine_image=amzn_linux,
                vpc=vpc,
                role=role,
                key_name="streamline.pem",
                vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
                block_devices=[
                    ec2.BlockDevice(
                        device_name="/dev/sda1",
                        volume=ec2.BlockDeviceVolume.ebs(
                            volume_type=ec2.EbsDeviceVolumeType.GP2,
                            volume_size=10
                        )
                    )
                ]
            )

app = App()
CdkStack(app, "streamline-ec2-instaces")

app.synth()