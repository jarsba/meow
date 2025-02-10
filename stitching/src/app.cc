#include "app.h"

#include <iostream>
#include <thread>
#include <stack>
#include <opencv2/videoio.hpp>
#include "stitching_param_generator.h"
#include <opencv2/imgproc.hpp>
#include <chrono>

App::App(const std::vector<std::string>& video_files, const std::string& output_folder, const std::string& file_name, double fps, bool dry_run, bool use_lir)
    : sensor_data_interface_(video_files), output_folder_(output_folder), file_name_(file_name), fps_(fps), dry_run_(dry_run), use_lir_(use_lir) {

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

// Helper function to check if a pixel is similar to reference color
bool isSimilarColor(const cv::Vec3b& pixel, const cv::Vec3b& reference, int tolerance = 0) {
    return std::abs(pixel[0] - reference[0]) <= tolerance &&
           std::abs(pixel[1] - reference[1]) <= tolerance &&
           std::abs(pixel[2] - reference[2]) <= tolerance;
}


// Optimized version of findLargestInteriorRectangle
cv::Rect findLargestInteriorRectangle(const cv::Mat& image, bool use_approximate = false, bool debug = false) {
    cv::Mat binary;
    cv::cvtColor(image, binary, cv::COLOR_BGR2GRAY);
    
    cv::GaussianBlur(binary, binary, cv::Size(5, 5), 0);
    cv::threshold(binary, binary, 1, 255, cv::THRESH_BINARY);

    int padding_h = use_approximate ? 50 : 0;   
    int padding_v = use_approximate ? 150 : 0;

    // Find the largest rectangle
    cv::Rect largest_rect(0, 0, 0, 0);
    int max_area = 0;
        
    // Pre-compute horizontal histograms for each row
    std::vector<std::vector<int>> h_lengths(binary.rows, std::vector<int>(binary.cols));
    
    // First row
    for(int x = 0; x < binary.cols; x++) {
        h_lengths[0][x] = binary.at<uchar>(0, x) == 255 ? 1 : 0;
    }
    
    // Remaining rows
    for(int y = 1; y < binary.rows; y++) {
        for(int x = 0; x < binary.cols; x++) {
            if(binary.at<uchar>(y, x) == 255) {
                h_lengths[y][x] = h_lengths[y-1][x] + 1;
            } else {
                h_lengths[y][x] = 0;
            }
        }
    }

    // For each row, find largest rectangle
    for(int y = 0; y < binary.rows; y++) {
        std::vector<int> heights = h_lengths[y];
        std::stack<int> s;
        int i = 0;
        
        while(i < binary.cols) {
            if(s.empty() || heights[s.top()] <= heights[i]) {
                s.push(i++);
            } else {
                int height = heights[s.top()];
                s.pop();
                int width = s.empty() ? i : i - s.top() - 1;
                int area = height * width;
                if(area > max_area) {
                    max_area = area;
                    largest_rect = cv::Rect(
                        s.empty() ? 0 : s.top() + 1,
                        y - height + 1,
                        width,
                        height
                    );
                }
            }
        }
        
        while(!s.empty()) {
            int height = heights[s.top()];
            s.pop();
            int width = s.empty() ? i : i - s.top() - 1;
            int area = height * width;
            if(area > max_area) {
                max_area = area;
                largest_rect = cv::Rect(
                    s.empty() ? 0 : s.top() + 1,
                    y - height + 1,
                    width,
                    height
                );
            }
        }
    }

    // Add padding if in approximate mode
    if (use_approximate && !largest_rect.empty()) {
        int new_x = std::max(0, largest_rect.x - padding_h);
        int new_y = std::max(0, largest_rect.y - padding_v);
        int new_width = std::min(image.cols - new_x, largest_rect.width + 2 * padding_h);
        int new_height = std::min(image.rows - new_y, largest_rect.height + 2 * padding_v);
        largest_rect = cv::Rect(new_x, new_y, new_width, new_height);
    }

    // If in debug mode, create a visualization
    if (debug) {
        cv::Mat debug_vis;
        cv::cvtColor(binary, debug_vis, cv::COLOR_GRAY2BGR);  // Convert to BGR for colored rectangle
        
        // Draw the largest rectangle in red
        if (!largest_rect.empty()) {
            cv::rectangle(debug_vis, largest_rect, cv::Scalar(0, 0, 255), 2);  // Red color, thickness 2
        }
        
        cv::imwrite("binary_mask_with_rect.png", debug_vis);
        cv::imwrite("binary_mask.png", binary);
        
        // Also save the original frame with rectangle for reference
        cv::Mat original_with_rect = image.clone();
        if (!largest_rect.empty()) {
            cv::rectangle(original_with_rect, largest_rect, cv::Scalar(0, 0, 255), 2);
        }
        cv::imwrite("original_with_rect.png", original_with_rect);
    } else {
        cv::imwrite("binary_mask.png", binary);
    }

    return largest_rect;
}

void App::run_stitching() {
    auto start_time = std::chrono::high_resolution_clock::now();
    std::vector<cv::UMat> image_vector(sensor_data_interface_.num_img_);
    std::vector<cv::UMat> images_warped_vector(sensor_data_interface_.num_img_);
    cv::Rect crop_rect;
    cv::Mat cropped_frame;

    // Get first frame for stitching
    sensor_data_interface_.get_image_vector(image_vector);

    // Process single frame for dry run
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

    if (dry_run_) {
        // Save the full panorama before cropping
        std::string full_image_path = output_folder_ + "/dry_run_full_" + file_name_;
        size_t dot_pos = full_image_path.find_last_of(".");
        if (dot_pos != std::string::npos) {
            full_image_path = full_image_path.substr(0, dot_pos) + ".jpg";
        }
        cv::imwrite(full_image_path, image_concat_mat);
    }

    // Apply LIR if requested
    if (use_lir_) {
        crop_rect = findLargestInteriorRectangle(image_concat_mat, true, dry_run_);  // Enable debug output in dry run
        cropped_frame = image_concat_mat(crop_rect);
        
        if (dry_run_) {
            // Save additional debug information
            std::cout << "LIR Debug Info:" << std::endl;
            std::cout << "Crop rectangle: x=" << crop_rect.x << ", y=" << crop_rect.y 
                      << ", width=" << crop_rect.width << ", height=" << crop_rect.height << std::endl;
            std::cout << "Original image size: " << image_concat_mat.cols << "x" << image_concat_mat.rows << std::endl;
            
            // Calculate and output the crop percentage
            double crop_area = crop_rect.width * crop_rect.height;
            double total_area = image_concat_mat.cols * image_concat_mat.rows;
            double crop_percentage = (crop_area / total_area) * 100.0;
            std::cout << "Crop percentage: " << crop_percentage << "% of original area" << std::endl;
        }
    } else {
        cropped_frame = image_concat_mat;  // Use full image without cropping
    }

    if (dry_run_) {
        // Save the final panorama (cropped or full)
        std::string image_path = output_folder_ + "/dry_run_" + file_name_;
        size_t dot_pos = image_path.find_last_of(".");
        if (dot_pos != std::string::npos) {
            image_path = image_path.substr(0, dot_pos) + ".jpg";
        }
        cv::imwrite(image_path, cropped_frame);
        return;
    }

    // Initialize video writer with appropriate dimensions
    cv::Size frame_size = use_lir_ ? cv::Size(crop_rect.width, crop_rect.height) 
                                 : cv::Size(image_concat_mat.cols, image_concat_mat.rows);

    video_writer_.open(output_folder_ + "/" + file_name_,
                      cv::VideoWriter::fourcc('M', 'J', 'P', 'G'),
                      fps_,
                      frame_size);

    if (!video_writer_.isOpened()) {
        throw std::runtime_error("Could not open the output video file for write");
    }

    // Write first frame
    video_writer_.write(cropped_frame);

    // Continue with remaining frames for normal run
    size_t frame_count = 1;
    double total_frames = sensor_data_interface_.getTotalFrames();

    while (!dry_run_) {
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

        image_concat_umat_.copyTo(image_concat_mat);
        cropped_frame = use_lir_ ? image_concat_mat(crop_rect) : image_concat_mat;
        video_writer_.write(cropped_frame);

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
    if (argc != 8) {  // Exactly 7 arguments + program name
        std::cerr << "Usage: " << argv[0] 
                  << " <output_folder> <file_name> <fps> <dry_run> <use_lir> <video_file1> <video_file2>" 
                  << std::endl;
        std::cerr << "  dry_run: true/false" << std::endl;
        std::cerr << "  use_lir: true/false" << std::endl;
        return 1;
    }

    std::string output_folder = argv[1];
    std::string file_name = argv[2];
    double fps = std::stod(argv[3]);
    bool dry_run = (std::string(argv[4]) == "true");
    bool use_lir = (std::string(argv[5]) == "true");
    
    // Always exactly two video files
    std::vector<std::string> video_files = {argv[6], argv[7]};

    try {
        App app(video_files, output_folder, file_name, fps, dry_run, use_lir);
        app.run_stitching();
    } catch (const std::exception& e) {
        std::cerr << "Exception: " << e.what() << std::endl;
        return 1;
    }

    return 0;
}