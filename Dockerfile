FROM ubuntu:24.04

ARG UBUNTU_MIRROR=http://archive.ubuntu.com/ubuntu
RUN sed -i "s|http://archive.ubuntu.com/ubuntu|$UBUNTU_MIRROR|g" /etc/apt/sources.list 
RUN find /etc/apt/sources.list.d/ -type f -exec sed -i 's|http://archive.ubuntu.com/ubuntu|http://il.archive.ubuntu.com/ubuntu|g' {} \; 

RUN apt-get update 
RUN apt-get upgrade -y 
RUN apt-get install -y software-properties-common ffmpeg procps

ENV DEBIAN_FRONTEND=noninteractive

RUN apt install -y curl

#RUN apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 8771ADB0816950D8 \
#    || apt-key adv --keyserver hkp://pgp.mit.edu:80 --recv-keys 8771ADB0816950D8


#RUN echo "deb https://ppa.launchpadcontent.net/stebbins/handbrake-releases/ubuntu $(lsb_release -cs) main" \
#    > /etc/apt/sources.list.d/handbrake-releases.list


#RUN add-apt-repository -y ppa:stebbins/handbrake-releases

#RUN apt-get update 

RUN apt-get install -y handbrake-cli

COPY convert_videos.sh /usr/local/bin/convert_videos.sh
COPY entrypoint.sh /usr/local/bin/entrypoint.sh

RUN chmod +x /usr/local/bin/convert_videos.sh /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

