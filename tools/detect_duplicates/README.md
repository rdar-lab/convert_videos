1. Install OS Dependencies:

sudo apt install ffmpeg imagemagick

2. Create a virtual env with python

python -m venv venv

3. Activate virtual env

source venv/bin/activate

4. Install python dependencies

pip install imagehash pillow

5. Get all movie hashes

./hash_videos.sh [DEST_FOLDER]

6. Compare hashes

python compare_videos.py
