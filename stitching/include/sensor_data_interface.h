#ifndef IMAGE_STITCHING_SENSOR_DATA_INTERFACE_H
#define IMAGE_STITCHING_SENSOR_DATA_INTERFACE_H

#include <vector>
#include <queue>
#include <opencv2/opencv.hpp>

class SensorDataInterface {
public:
  SensorDataInterface(const std::vector<std::string>& video_files);

  void InitVideoCapture();
  void get_image_vector(std::vector<cv::UMat>& image_vector);
  void get_initial_images(std::vector<cv::UMat>& image_vector);
  bool all_videos_finished();
  double getTotalFrames();
  size_t num_img_;

private:
  std::vector<std::queue<cv::UMat>> image_queue_vector_;
  std::vector<cv::VideoCapture> video_capture_vector_;
  std::vector<bool> video_finished_;
  std::vector<std::string> video_files_;
  double total_frames_;
};

#endif //IMAGE_STITCHING_SENSOR_DATA_INTERFACE_H