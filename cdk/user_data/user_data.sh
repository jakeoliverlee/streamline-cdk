#!/bin/bash
# Version 1.0.0
# Owned by @jaklee

# This script can be used to setup the environment on an EC2 instance with AMI image.
# It will install git, clone the repo, install the dependencies start the tmux session to run the app.


# Update the system and install dependencies
sudo yum update -y
sudo yum install -y git tmux
sudo pip3 install streamlit

# Clone the Streamline repo
git clone https://github.com/jakeoliverlee/Streamline.git

# Change directory to the app folder
cd Streamline/app

# Redirect port 80 to port 8080
sudo iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 8080

# Start a new TMUX session
tmux new-session -d -s streamline_session

# Run the Streamlit app in the TMUX session
tmux send-keys "streamlit run --server.port 8080 Home.py" C-m

# Attach to the TMUX session to view the app
tmux attach -t streamline_session