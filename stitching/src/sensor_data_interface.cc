#include "sensor_data_interface.h"
#include <string>

SensorDataInterface::SensorDataInterface(const std::vector<std::string>& video_files)
    : video_files_(video_files) {
  num_img_ = video_files_.size();
  image_queue_vector_ = std::vector<std::queue<cv::UMat>>(num_img_);
  video_finished_ = std::vector<bool>(num_img_, false);
  total_frames_ = 0;
}

void SensorDataInterface::InitVideoCapture() {
  std::cout << "Initializing video capture..." << std::endl;

  for (const auto& file : video_files_) {
    cv::VideoCapture capture(file);
    if (!capture.isOpened()) {
      std::cerr << "Failed to open video file: " << file << std::endl;
      video_finished_[&file - &video_files_[0]] = true;
      continue;
    }
    video_capture_vector_.push_back(capture);
    total_frames_ = capture.get(cv::CAP_PROP_FRAME_COUNT);
  }
  std::cout << "Done. " << video_files_.size() << " captures initialized." << std::endl;
}

double SensorDataInterface::getTotalFrames() {
  return total_frames_;
}


void SensorDataInterface::get_initial_images(std::vector<cv::UMat>& image_vector) {
  for (size_t i = 0; i < num_img_; ++i) {
    cv::UMat frame;
    video_capture_vector_[i].read(frame);
    if (!frame.empty()) {
      image_queue_vector_[i].push(frame);
    } else {
      video_finished_[i] = true;
    }
    image_vector[i] = frame;
  }
}

void SensorDataInterface::get_image_vector(std::vector<cv::UMat>& image_vector) {
  for (size_t i = 0; i < num_img_; ++i) {
    if (video_finished_[i]) {
      continue;
    }
    cv::UMat frame;
    video_capture_vector_[i].read(frame);
    if (frame.empty()) {
      video_finished_[i] = true;
    } else {
      image_vector[i] = frame;
    }
  }
}

bool SensorDataInterface::all_videos_finished() {
  return std::all_of(video_finished_.begin(), video_finished_.end(), [](bool finished) { return finished; });
}