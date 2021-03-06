import os
import os.path
import random
import argparse

from torchvision import datasets

import webdataset as wds


parser = argparse.ArgumentParser("ImageNet training on shards")
parser.add_argument(
    "--imagenet",
    default="/imagenet",
    help="directory containing ImageNet data distribution suitable for torchvision.datasets",
)
parser.add_argument(
    "--shards", default="./data", help="directory where shards are written"
)
parser.add_argument("--splits", default="train,val", help="which splits to write")
args = parser.parse_args()

splits = args.splits.split(",")

# The desired shard size in bytes.
shardsize = 1e9


def readfile(fname):
    "Read a binary file from disk."
    with open(fname, "rb") as stream:
        return stream.read()


all_keys = set()


def write_dataset(imagenet, base="./imagenet", split="train"):

    # We're using the torchvision ImageNet dataset
    # to parse the metadata; however, we will read
    # the compressed images directly from disk (to
    # avoid having to reencode them)
    ds = datasets.ImageNet(imagenet, split=split)
    nimages = len(ds.imgs)

    # We shuffle the indexes to make sure that we
    # don't get any large sequences of a single class
    # in the dataset.
    indexes = list(range(nimages))
    random.shuffle(indexes)

    # This is the output pattern under which we write shards.
    pattern = base + "-" + split + "-%06d.tar"

    with wds.ShardWriter(pattern, maxsize=shardsize) as sink:
        for i in indexes:

            # Internal information from the ImageNet dataset
            # instance: the file name and the numerical class.
            fname, cls = ds.imgs[i]
            assert cls == ds.targets[i]

            # Read the JPEG-compressed image file contents.
            image = readfile(fname)

            # Construct a uniqu keye from the filename.
            key = os.path.splitext(os.path.basename(fname))[0]

            # Useful check.
            assert key not in all_keys
            all_keys.add(key)

            # Construct a sample.
            sample = {"__key__": key, "jpg": image, "cls": cls}

            # Write the sample to the sharded tar archives.
            sink.write(sample)


os.makedirs(args.shards, exist_ok=True)

for split in splits:
    write_dataset(args.imagenet, base=args.shards, split=split)
