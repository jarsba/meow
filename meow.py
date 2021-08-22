import argparse
from stitcher import Stitcher


def parse_arguments():
    parser = argparse.ArgumentParser(prog='meow', description='Stitch videos to panorama')
    parser.add_argument("-i", "--input", nargs=2, dest='input', help="path to the input files")
    parser.add_argument("-o", "--output", dest='output', help="path of the output file (default output.mp4)")
    parser.add_argument("-v", "--verbose", help="verbose output", action='store_true')

    args = parser.parse_args()
    return args


def run():
    args = parse_arguments()
    stitcher = Stitcher(input_path_1=args.input[0], input_path_2=args.input[1], output=args.output)
    stitcher.stitch()


if __name__ == "__main__":
    run()
