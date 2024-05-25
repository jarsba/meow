// Created by s1nh.org.

#ifndef IMAGE_STITCHING_APP_H
#define IMAGE_STITCHING_APP_H

#include "opencv2/opencv.hpp"
#include "opencv2/videoio.hpp"
#include "sensor_data_interface.h"
#include "image_stitcher.h"

class App {
public:
  App(const std::vector<std::string>& video_files, const std::string& output_folder, const std::string& file_name, double fps);

  void run_stitching();

private:
  SensorDataInterface sensor_data_interface_;
  ImageStitcher image_stitcher_;
  std::vector<cv::Mat> image_vector_;
  int total_cols_;
  cv::UMat image_concat_umat_;
  cv::VideoWriter video_writer_;
  std::string output_folder_;
  std::string file_name_;
  double fps_;
};

#endif //IMAGE_STITCHING_APP_H
