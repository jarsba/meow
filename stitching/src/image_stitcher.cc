#include "image_stitcher.h"

#include <iostream>

void ImageStitcher::SetParams(
    const int& blend_width,
    std::vector<cv::UMat>& undist_xmap_vector,
    std::vector<cv::UMat>& undist_ymap_vector,
    std::vector<cv::UMat>& reproj_xmap_vector,
    std::vector<cv::UMat>& reproj_ymap_vector,
    std::vector<cv::Rect>& projected_image_roi_vect_refined) {

    std::cout << "[SetParams] Setting params..." << std::endl;
    num_img_ = undist_xmap_vector.size();

    undist_xmap_vector_ = undist_xmap_vector;
    undist_ymap_vector_ = undist_ymap_vector;
    reproj_xmap_vector_ = reproj_xmap_vector;
    reproj_ymap_vector_ = reproj_ymap_vector;
    roi_vect_ = projected_image_roi_vect_refined;

    // Combine two remap operator (For speed up a little)
    final_xmap_vector_ = std::vector<cv::UMat>(undist_ymap_vector.size());
    final_ymap_vector_ = std::vector<cv::UMat>(undist_ymap_vector.size());
    tmp_umat_vect_ = std::vector<cv::UMat>(undist_ymap_vector.size());
    for (size_t img_idx = 0; img_idx < num_img_; ++img_idx) {
        remap(undist_xmap_vector_[img_idx],
              final_xmap_vector_[img_idx],
              reproj_xmap_vector_[img_idx],
              reproj_ymap_vector_[img_idx],
              cv::INTER_LINEAR);
        remap(undist_ymap_vector_[img_idx],
              final_ymap_vector_[img_idx],
              reproj_xmap_vector_[img_idx],
              reproj_ymap_vector_[img_idx],
              cv::INTER_LINEAR);
    }

    auto blend_height = undist_ymap_vector[0].rows;
    for (int i = 0; i < num_img_; i++) {
        if (undist_ymap_vector[i].rows < blend_height)
            blend_height = undist_ymap_vector[i].rows;
        if (roi_vect_[i].height < blend_height)
            blend_height = roi_vect_[i].height;
    }

    CreateWeightMap(blend_height, blend_width);
    std::cout << "[SetParams] Setting params... Done." << std::endl;
}

void ImageStitcher::CreateWeightMap(const int& height, const int& width) {
    std::cout << "[CreateWeightMap] Creating weight map..." << std::endl;

    // TODO: Try CV_16F.
    cv::Mat _l = cv::Mat(height, width, CV_8UC3);
    cv::Mat _r = cv::Mat(height, width, CV_8UC3);
    for (int i = 0; i < height; ++i) {
        for (int j = 0; j < width; ++j) {
            _l.at<cv::Vec3b>(i, j)[0] =
            _l.at<cv::Vec3b>(i, j)[1] =
            _l.at<cv::Vec3b>(i, j)[2] =
                cv::saturate_cast<uchar>((float) j / (float) width * 255);

            _r.at<cv::Vec3b>(i, j)[0] =
            _r.at<cv::Vec3b>(i, j)[1] =
            _r.at<cv::Vec3b>(i, j)[2] =
                cv::saturate_cast<uchar>((float) (width - j) / (float) width * 255);

        }
    }
    weightMap_.emplace_back(_l.getUMat(cv::ACCESS_READ));
    weightMap_.emplace_back(_r.getUMat(cv::ACCESS_READ));

    cv::imwrite("../results/_weight_map_l.png", weightMap_[0]);
    cv::imwrite("../results/_weight_map_r.png", weightMap_[1]);

    std::cout << "[CreateWeightMap] Creating weight map... Done." << std::endl;
}

void ImageStitcher::WarpImages(
    const int& img_idx,
    const int& fusion_pixel,
    const std::vector<cv::UMat>& image_vector,
    std::vector<cv::UMat>& images_warped_vector,
    cv::UMat& image_concat_umat) {

    // Initialize with black background
    if (img_idx == 0) {
        image_concat_umat.setTo(cv::Scalar(0, 0, 0));
    }

    // Remap with black border
    remap(image_vector[img_idx],
          tmp_umat_vect_[img_idx],
          final_xmap_vector_[img_idx],
          final_ymap_vector_[img_idx],
          cv::INTER_LINEAR,
          cv::BORDER_CONSTANT,
          cv::Scalar(0, 0, 0));

    // Calculate destination position
    int cols = 0;
    for (size_t i = 0; i < img_idx; i++) {
        cols += roi_vect_[i].width;
    }

    // Ensure ROI is valid
    cv::Rect safe_roi = roi_vect_[img_idx];
    safe_roi.x = std::max(0, safe_roi.x);
    safe_roi.y = std::max(0, safe_roi.y);
    safe_roi.width = std::min(safe_roi.width, tmp_umat_vect_[img_idx].cols - safe_roi.x);
    safe_roi.height = std::min(safe_roi.height, tmp_umat_vect_[img_idx].rows - safe_roi.y);

    // Create ROI in destination with bounds checking
    cv::Rect dst_roi(cols, 0, 
                     std::min(safe_roi.width, image_concat_umat.cols - cols),
                     std::min(safe_roi.height, image_concat_umat.rows));

    // Additional safety checks
    if (dst_roi.width <= 0 || dst_roi.height <= 0 || 
        dst_roi.x < 0 || dst_roi.y < 0 ||
        dst_roi.x + dst_roi.width > image_concat_umat.cols ||
        dst_roi.y + dst_roi.height > image_concat_umat.rows) {
        std::cout << "Warning: Invalid destination ROI for image " << img_idx << std::endl;
        return;
    }

    // Debug output
    std::cout << "Image " << img_idx << " dimensions:" << std::endl;
    std::cout << "Source size: " << tmp_umat_vect_[img_idx].size() << std::endl;
    std::cout << "Safe ROI: " << safe_roi << std::endl;
    std::cout << "Dst ROI: " << dst_roi << std::endl;
    std::cout << "Concat image size: " << image_concat_umat.size() << std::endl;

    try {
        // Create valid UMat ROIs
        cv::UMat src_roi = tmp_umat_vect_[img_idx](safe_roi);
        cv::UMat dst_roi_mat = image_concat_umat(dst_roi);

        // Just copy for first image or when no blending needed
        if (img_idx == 0 || weightMap_.empty()) {
            src_roi.copyTo(dst_roi_mat);
        } else {
            // Blend with previous image
            int blend_width = std::min(weightMap_[0].cols, dst_roi.width);
            
            // Get overlapping regions
            cv::UMat curr_blend = src_roi(cv::Rect(0, 0, blend_width, dst_roi.height));
            cv::UMat prev_blend = dst_roi_mat(cv::Rect(0, 0, blend_width, dst_roi.height));

            // Apply weight maps
            cv::multiply(curr_blend, weightMap_[0](cv::Rect(0, 0, blend_width, dst_roi.height)), 
                        curr_blend, 1.0/255);
            cv::multiply(prev_blend, weightMap_[1](cv::Rect(0, 0, blend_width, dst_roi.height)), 
                        prev_blend, 1.0/255);
            
            // Combine
            cv::add(curr_blend, prev_blend, curr_blend);
            curr_blend.copyTo(dst_roi_mat(cv::Rect(0, 0, blend_width, dst_roi.height)));

            // Copy remaining region
            if (blend_width < dst_roi.width) {
                src_roi(cv::Rect(blend_width, 0, dst_roi.width - blend_width, dst_roi.height))
                    .copyTo(dst_roi_mat(cv::Rect(blend_width, 0, dst_roi.width - blend_width, dst_roi.height)));
            }
        }
    } catch (const cv::Exception& e) {
        std::cout << "OpenCV error: " << e.what() << std::endl;
    }
}