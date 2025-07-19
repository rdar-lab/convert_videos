#!/usr/bin/env python3

from imagehash import phash
from PIL import Image
from collections import defaultdict
import itertools

def hamming_dist(hash1, hash2):
    return bin(int(str(hash1), 16) ^ int(str(hash2), 16)).count("1")

# Load hashes
videos = []
with open("video_hashes.txt") as f:
    for line in f:
        hash_str, path = line.strip().split("|", 1)
        videos.append((hash_str.strip(), path.strip()))

# Compare all pairs
for (h1, f1), (h2, f2) in itertools.combinations(videos, 2):
    dist = hamming_dist(h1, h2)
    if dist <= 5:
        print(f"Possible duplicate (distance={dist}):\n  {f1}\n  {f2}\n")
