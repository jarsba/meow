#include "app.h"

#include <iostream>
#include <thread>
#include <opencv2/videoio.hpp>
#include "stitching_param_generator.h"
#include <opencv2/imgproc.hpp>

App::App(const std::vector<std::string>& video_files, const std::string& output_folder, const std::string& file_name, double fps, bool dry_run)
    : sensor_data_interface_(video_files), output_folder_(output_folder), file_name_(file_name), fps_(fps), dry_run_(dry_run)  {

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

// Add this helper function to find the largest interior rectangle
cv::Rect findLargestInteriorRectangle(const cv::Mat& image) {
    cv::Mat gray, binary;
    cv::cvtColor(image, gray, cv::COLOR_BGR2GRAY);
    cv::threshold(gray, binary, 1, 255, cv::THRESH_BINARY); // Threshold to separate black borders

    cv::Rect largest_rect(0, 0, 0, 0);
    int max_area = 0;
    
    // Scan through possible top-left points
    for(int y = 0; y < binary.rows; y++) {
        for(int x = 0; x < binary.cols; x++) {
            if(binary.at<uchar>(y,x) == 0) continue; // Skip black pixels
            
            // For each point, find largest possible rectangle
            int max_width = binary.cols - x;
            int max_height = binary.rows - y;
            
            // Find maximum width
            for(int w = max_width; w > largest_rect.width; w--) {
                // Find maximum height for this width
                for(int h = max_height; h > 0; h--) {
                    cv::Rect rect(x, y, w, h);
                    cv::Mat roi = binary(rect);
                    if(cv::countNonZero(roi) == roi.total()) { // If no black pixels
                        int area = w * h;
                        if(area > max_area) {
                            max_area = area;
                            largest_rect = rect;
                        }
                        break;
                    }
                }
            }
        }
    }
    return largest_rect;
}

void App::run_stitching() {
    auto start_time = std::chrono::high_resolution_clock::now();
    std::vector<cv::UMat> image_vector(sensor_data_interface_.num_img_);
    std::vector<cv::UMat> images_warped_vector(sensor_data_interface_.num_img_);
    size_t frame_count = 0;
    double total_frames = dry_run_ ? 1 : sensor_data_interface_.getTotalFrames();
    cv::Rect crop_rect;
    bool crop_rect_initialized = false;

    while (true) {
        sensor_data_interface_.get_image_vector(image_vector);

        if (sensor_data_interface_.all_videos_finished() || (dry_run_ && frame_count > 0)) {
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

        // Find the crop rectangle on the first frame
        if (!crop_rect_initialized) {
            crop_rect = findLargestInteriorRectangle(image_concat_mat);
            crop_rect_initialized = true;

            // Reinitialize video writer with new dimensions
            if (video_writer_.isOpened()) {
                video_writer_.release();
            }
            std::string output_file = output_folder_ + "/" + file_name_;
            video_writer_.open(output_file, 
                             cv::VideoWriter::fourcc('M', 'J', 'P', 'G'), 
                             fps_, 
                             cv::Size(crop_rect.width, crop_rect.height));
        }

        // Crop the frame
        cv::Mat cropped_frame = image_concat_mat(crop_rect);
        video_writer_.write(cropped_frame);

        if (dry_run_) {
            // Save single frame as image
            cv::Mat output_frame;
            image_concat_mat.copyTo(output_frame);
            std::string image_path = output_folder_ + "/test_frame.jpg";
            cv::imwrite(image_path, output_frame, {cv::IMWRITE_JPEG_QUALITY, 95});
            break;
        }

        frame_count++;
        if (frame_count % static_cast<size_t>(fps_ * 5) == 0) {
            auto current_time = std::chrono::high_resolution_clock::now();
            std::chrono::duration<double> elapsed_seconds = current_time - start_time;
            double fps = frame_count / elapsed_seconds.count();
            double progress_percentage = (frame_count / total_frames) * 100;
            double estimated_total_time = total_frames / fps;
            double time_remaining = estimated_total_time - elapsed_seconds.count();

            
            std::cout << "PROGRESS:" << static_cast<int>(progress_percentage) << std::endl;
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
        std::cerr << "Usage: " << argv[0] 
                  << " <output_folder> <file_name> <fps> <dry_run> <video_file1> <video_file2> [video_file3 ...]" 
                  << std::endl;
        return 1;
    }

    std::string output_folder = argv[1];
    std::string file_name = argv[2];
    double fps = std::stod(argv[3]);
    bool dry_run = std::string(argv[4]) == "true";
    
    std::vector<std::string> video_files;
    for (int i = 5; i < argc; ++i) {
        video_files.push_back(argv[i]);
    }

    try {
        App app(video_files, output_folder, file_name, fps, dry_run);
        app.run_stitching();
    } catch (const std::exception& e) {
        std::cerr << "Exception: " << e.what() << std::endl;
        return 1;
    }

    return 0;
}