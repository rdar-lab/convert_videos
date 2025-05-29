# convert_videos

automatically convert any videos in a specific folder to H.256.
This container will keep monitoring for new files in the folder (or any sub-folder within it), and if it is more than 1GB of space and not already H.256 it will automatically convert it

Benefits:
1. Play with HW acceleration
2. Save storage

## Build docker

docker build -t rdxmaster/convert_videos:latest .

## Run it

docker run \
	-d \
	--name convert_videos \
	-v [FOLDER]:/data \
	--restart unless-stopped \
	--cap-add=SYS_NICE \
	rdxmaster/convert_videos
