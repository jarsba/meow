#include "sensor_data_interface.h"

#include <string>
#include <thread>

SensorDataInterface::SensorDataInterface(const std::vector<std::string>& video_files)
    : max_queue_length_(2), video_files_(video_files) {
  num_img_ = video_files_.size();
  image_queue_vector_ = std::vector<std::queue<cv::UMat>>(num_img_);
  image_queue_mutex_vector_ = std::vector<std::mutex>(num_img_);
  video_finished_ = std::vector<bool>(num_img_, false);
}

void SensorDataInterface::InitVideoCapture() {
  std::cout << "Initializing video capture..." << std::endl;
  num_img_ = video_files_.size();
  image_queue_vector_ = std::vector<std::queue<cv::UMat>>(num_img_);
  image_queue_mutex_vector_ = std::vector<std::mutex>(num_img_);
  video_finished_ = std::vector<bool>(num_img_, false);

  for (int i = 0; i < num_img_; ++i) {
    cv::VideoCapture capture(video_files_[i]);
    if (!capture.isOpened())
      std::cout << "Failed to open capture " << i << std::endl;
    video_capture_vector_.push_back(capture);

    cv::UMat frame;
    capture.read(frame);
    image_queue_vector_[i].push(frame);
  }
  std::cout << "Done. " << num_img_ << " captures initialized." << std::endl;
}

void SensorDataInterface::RecordVideos() {
  size_t frame_idx = 0;
  while (true) {
    std::cout << "[DEBUG] Recording frame " << frame_idx << "." << std::endl;

    for (int i = 0; i < num_img_; ++i) {
      cv::UMat frame;
      video_capture_vector_[i].read(frame);

      if (frame.empty()) {
        video_finished_[i] = true;
        std::cout << "[DEBUG] DEBUGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG." << std::endl;
        std::cout << "[DEBUG] Finished video with index " << i << "." << std::endl;
      } else {
        std::cout << "[DEBUG] Video finished debug " << "i: " << i << ", value: " << video_finished_[i] << "." << std::endl;

        if (frame.rows > 0) {
          image_queue_mutex_vector_[i].lock();
          image_queue_vector_[i].push(frame);
          if (image_queue_vector_[i].size() > max_queue_length_) {
            image_queue_vector_[i].pop();
          }
          image_queue_mutex_vector_[i].unlock();
        } else {
          video_finished_[i] = true;
          std::cout << "[DEBUG] DEBUGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG." << std::endl;
          std::cout << "[DEBUG] Finished video with index " << i << "." << std::endl;
        }
      }
    }
    
    std::cout << "[RecordVideos] recorded frame " << frame_idx << "." << std::endl;
    frame_idx++;
    std::this_thread::sleep_for(std::chrono::milliseconds(1000));

    if (all_videos_finished()) {
        break;
    }
  }
}

bool SensorDataInterface::all_videos_finished() {
  return std::all_of(video_finished_.begin(), video_finished_.end(),  [](bool finished) { return finished; });
}

void SensorDataInterface::get_image_vector(
    std::vector<cv::UMat>& image_vector,
    std::vector<std::mutex>& image_mutex_vector) {

  std::cout << "[SensorDataInterface] Getting new images...";
  for (size_t i = 0; i < num_img_; ++i) {
    cv::Mat img_undistort;
    cv::Mat img_cylindrical;

    image_queue_mutex_vector_[i].lock();
    image_mutex_vector[i].lock();
    image_vector[i] = image_queue_vector_[i].front();
    image_mutex_vector[i].unlock();
    image_queue_mutex_vector_[i].unlock();
  }
  std::cout << " Done." << std::endl;

}
