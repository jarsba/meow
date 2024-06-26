#include "app.h"

#include <iostream>
#include <thread>
#include <opencv2/videoio.hpp>
#include "stitching_param_generator.h"

App::App(const std::vector<std::string>& video_files, const std::string& output_folder, const std::string& file_name, double fps)
    : sensor_data_interface_(video_files), output_folder_(output_folder), file_name_(file_name), fps_(fps) {

    sensor_data_interface_.InitVideoCapture();

    std::vector<cv::UMat> first_image_vector(sensor_data_interface_.num_img_);
    std::vector<cv::Mat> first_mat_vector(sensor_data_interface_.num_img_);
    std::vector<cv::UMat> reproj_xmap_vector;
    std::vector<cv::UMat> reproj_ymap_vector;
    std::vector<cv::UMat> undist_xmap_vector;
    std::vector<cv::UMat> undist_ymap_vector;
    std::vector<cv::Rect> image_roi_vect;

    sensor_data_interface_.get_initial_images(first_image_vector);

    for (size_t i = 0; i < sensor_data_interface_.num_img_; ++i) {
        first_image_vector[i].copyTo(first_mat_vector[i]);
    }

    StitchingParamGenerator stitching_param_generator(first_mat_vector);

    stitching_param_generator.GetReprojParams(
        undist_xmap_vector,
        undist_ymap_vector,
        reproj_xmap_vector,
        reproj_ymap_vector,
        image_roi_vect
    );

    image_stitcher_.SetParams(
        100,
        undist_xmap_vector,
        undist_ymap_vector,
        reproj_xmap_vector,
        reproj_ymap_vector,
        image_roi_vect
    );

    total_cols_ = 0;
    for (size_t i = 0; i < sensor_data_interface_.num_img_; ++i) {
        total_cols_ += image_roi_vect[i].width;
    }

    // Initialize the video writer
    std::string output_file = output_folder_ + "/" + file_name_;
    int frame_width = total_cols_;
    int frame_height = image_roi_vect[0].height;
    video_writer_.open(output_file, cv::VideoWriter::fourcc('M', 'J', 'P', 'G'), fps_, cv::Size(frame_width, frame_height));
    if (!video_writer_.isOpened()) {
        throw std::runtime_error("Could not open the output video file for write: " + output_file);
    }

    image_concat_umat_.create(frame_height, frame_width, CV_8UC3);
}

void App::run_stitching() {
    auto start_time = std::chrono::high_resolution_clock::now();
    std::vector<cv::UMat> image_vector(sensor_data_interface_.num_img_);
    std::vector<cv::UMat> images_warped_vector(sensor_data_interface_.num_img_);
    size_t frame_count = 0;
    double total_frames = sensor_data_interface_.getTotalFrames();

    while (true) {
        sensor_data_interface_.get_image_vector(image_vector);

        if (sensor_data_interface_.all_videos_finished()) {
            break;
        }

        for (size_t img_idx = 0; img_idx < sensor_data_interface_.num_img_; ++img_idx) {
            image_stitcher_.WarpImages(
                img_idx,
                20,
                image_vector,
                images_warped_vector,
                image_concat_umat_
            );
        }

        cv::Mat image_concat_mat;
        image_concat_umat_.copyTo(image_concat_mat);
        video_writer_.write(image_concat_mat);

        frame_count++;
        if (frame_count % static_cast<size_t>(fps_) == 0) {
            auto current_time = std::chrono::high_resolution_clock::now();
            std::chrono::duration<double> elapsed_seconds = current_time - start_time;
            double fps = frame_count / elapsed_seconds.count();

            double progress_percentage = (frame_count / total_frames) * 100;
            double estimated_total_time = total_frames / fps;
            double time_remaining = estimated_total_time - elapsed_seconds.count();

            // Print the progress and time estimate
            std::cout << "FPS: " << fps << ", Progress: " << progress_percentage << "%"
                      << ", Time Remaining: " << time_remaining << " seconds" << std::endl;
        }
    }

    if (video_writer_.isOpened()) {
        video_writer_.release();
    }
}

int main(int argc, char* argv[]) {
  if (argc < 6) {
    std::cerr << "Usage: " << argv[0] << " <output_folder> <file_name> <fps> <video_file1> <video_file2> [video_file3 ...]" << std::endl;
    return 1;
  }

  std::string output_folder = argv[1];
  std::string file_name = argv[2];
  double fps = std::stod(argv[3]);
  std::vector<std::string> video_files;
  for (int i = 4; i < argc; ++i) {
    video_files.push_back(argv[i]);
  }

  try {
    App app(video_files, output_folder, file_name, fps);
    app.run_stitching();
  } catch (const std::exception& e) {
    std::cerr << "Exception: " << e.what() << std::endl;
    return 1;
  }

  return 0;
}