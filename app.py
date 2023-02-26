from aws_cdk import (
    aws_ec2 as ec2,
    aws_autoscaling as autoscaling,
    aws_elasticloadbalancingv2 as elbv2,
    core,
)

app = core.App()

# create a VPC for the instances to run in
vpc = ec2.Vpc(
    app, "streamline-vpc",
    cidr="10.0.0.0/16",
    max_azs=2,
    subnet_configuration=[
        ec2.SubnetConfiguration(
            name="Public", cidr_mask=24, subnet_type=ec2.SubnetType.PUBLIC
        )
    ],
)

# create a security group for the instances
instance_sg = ec2.SecurityGroup(
    app, "streamline-sg",
    vpc=vpc,
    allow_all_outbound=True,
)
instance_sg.add_ingress_rule(
    elbv2.SecurityGroup(
        app, "streamline-alb-sg",
        vpc=vpc,
    ),
    ec2.Port.tcp_range(80, 443),
    "allow HTTP/HTTPS traffic from ALB",
)

# create an Application Load Balancer
alb = elbv2.ApplicationLoadBalancer(
    app, "streamline-alb",
    vpc=vpc,
    internet_facing=True,
)
alb.connections.allow_default_port_from_any_ipv4("allow public access to ALB")

# create an Auto Scaling Group
asg = autoscaling.AutoScalingGroup(
    app, "streamline-ws-asg",
    vpc=vpc,
    instance_type=ec2.InstanceType("t2.micro"),
    machine_image=ec2.AmazonLinuxImage(),
    min_capacity=2,
    max_capacity=4,
    desired_capacity=2,
    security_group=instance_sg,
    user_data=core.Fn.base64(
            "#!/bin/bash\n"
            "# Version 1.0.0\n"
            "# Owned by @jaklee\n"
            "\n"
            "# This script can be used to setup the environment on an EC2 instance with AMI image.\n"
            "# It will install git, clone the repo, install the dependencies start the tmux session to run the app.\n"
            "\n"
            "# Update the system and install dependencies\n"
            "sudo yum update -y\n"
            "sudo yum install -y git tmux\n"
            "sudo pip3 install streamlit\n"
            "\n"
            "# Clone the Streamline repo\n"
            "git clone https://github.com/jakeoliverlee/Streamline.git\n"
            "\n"
            "# Change directory to the app folder\n"
            "cd Streamline/app\n"
            "\n"
            "# Redirect port 80 to port 8080\n"
            "sudo iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 8080\n"
            "\n"
            "# Start a new TMUX session\n"
            "tmux new-session -d -s streamline_session\n"
            "\n"
            "# Run the Streamlit app in the TMUX session\n"
            "tmux send-keys \"streamlit run --server.port 8080 Home.py\" C-m\n"
            "\n"
            "# Attach to the TMUX session to view the app\n"
            "tmux attach -t streamline_session\n"
    ),
    desired_capacity=3,
)
asg.connections.allow_from(alb, ec2.Port.tcp_range(80, 443), "allow HTTP/HTTPS traffic from ALB")

# add the instances to the target group of the Application Load Balancer
tg = elbv2.ApplicationTargetGroup(
    app, "MyTargetGroup",
    vpc=vpc,
    port=80,
    targets=[asg],
)

listener = alb.add_listener(
    "MyListener",
    port=80,
    default_target_groups=[tg],
)

app.synth()
