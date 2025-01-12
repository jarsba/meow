#ifndef APP_H
#define APP_H

#include <string>
#include <vector>
#include <opencv2/opencv.hpp>
#include "image_stitcher.h"
#include "sensor_data_interface.h"
#include "stitching_param_generator.h"

class App {
public:
    App(const std::vector<std::string>& video_files, const std::string& output_folder, const std::string& file_name, double fps, bool dry_run, bool use_lir);
    void run_stitching();

private:
    SensorDataInterface sensor_data_interface_;
    ImageStitcher image_stitcher_;
    cv::VideoWriter video_writer_;
    cv::UMat image_concat_umat_;
    std::string output_folder_;
    std::string file_name_;
    double fps_;
    int total_cols_;
    bool dry_run_;
    bool use_lir_;
};

#endif // APP_H