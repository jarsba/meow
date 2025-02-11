# Fast panorama stitching method using UMat.

Code is based on the following work, but it is heavily modified version of it. The modifications include:

- Use always only two input videos
- Use LIR
- Change the logic of video reading to get rid of semaphores
- Add a dry run mode
- Add a mode to output the intermediate images
- Fix issues related to infinite stitching loop in the original code
- And some other minor changes


Paper: 

> Du, Chengyao, et al. (2020). GPU based parallel optimization for real time panoramic video stitching. Pattern Recognition Letters, 133, 62-69.
 

Repository:

> https://github.com/duchengyao/gpu-based-image-stitching


## How to run

```
$ mkdir build && cd build
$ cmake .. && make
$ ./image-stitching <output_folder> <file_name> <fps> <dry_run> <use_lir> <video_file1> <video_file2>
```