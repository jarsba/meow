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

    // Initialize all maps with black borders
    for (size_t img_idx = 0; img_idx < num_img_; ++img_idx) {
        tmp_umat_vect_[img_idx].create(undist_ymap_vector[0].size(), CV_8UC3);
        tmp_umat_vect_[img_idx].setTo(cv::Scalar(0, 0, 0));  // Set to black
    }

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

// Helper function to check if a pixel is similar to reference color
bool isSimilarColor(const cv::Vec3b& pixel, const cv::Vec3b& reference) {
    return std::abs(pixel[0] - reference[0]) <= 0 &&
           std::abs(pixel[1] - reference[1]) <= 0 &&
           std::abs(pixel[2] - reference[2]) <= 0;
}


void ImageStitcher::WarpImages(
    const int& img_idx,
    const int& fusion_pixel,
    const std::vector<cv::UMat>& image_vector,
    std::vector<cv::UMat>& images_warped_with_roi_vector,
    cv::UMat& image_concat_umat) {

    // Initialize or clear the concat image with black
    if (img_idx == 0) {
        image_concat_umat.setTo(cv::Scalar(0, 0, 0));
    }

    // First do the remap with black borders
    remap(image_vector[img_idx],
          tmp_umat_vect_[img_idx],
          final_xmap_vector_[img_idx],
          final_ymap_vector_[img_idx],
          cv::INTER_LINEAR,
          cv::BORDER_CONSTANT,  // Use constant border
          cv::Scalar(0, 0, 0)   // Black color for borders
    );

    // Now get the warped image and its corner colors
    cv::Mat warped_mat;
    tmp_umat_vect_[img_idx].copyTo(warped_mat);
    
    cv::Vec3b topLeft = warped_mat.at<cv::Vec3b>(0, 0);
    cv::Vec3b topRight = warped_mat.at<cv::Vec3b>(0, warped_mat.cols-1);
    cv::Vec3b bottomLeft = warped_mat.at<cv::Vec3b>(warped_mat.rows-1, 0);
    cv::Vec3b bottomRight = warped_mat.at<cv::Vec3b>(warped_mat.rows-1, warped_mat.cols-1);

    // Convert any remaining border colors to black
    cv::parallel_for_(cv::Range(0, warped_mat.rows), [&](const cv::Range& range) {
        for(int y = range.start; y < range.end; y++) {
            for(int x = 0; x < warped_mat.cols; x++) {
                cv::Vec3b& pixel = warped_mat.at<cv::Vec3b>(y, x);
                if (isSimilarColor(pixel, topLeft) || 
                    isSimilarColor(pixel, topRight) || 
                    isSimilarColor(pixel, bottomLeft) || 
                    isSimilarColor(pixel, bottomRight)) {
                    pixel = cv::Vec3b(0, 0, 0);
                }
            }
        }
    });
    
    warped_mat.copyTo(tmp_umat_vect_[img_idx]);

    if (img_idx > 0) {
        cv::UMat _r = tmp_umat_vect_[img_idx](cv::Rect(
            roi_vect_[img_idx].x,
            roi_vect_[img_idx].y,
            weightMap_[0].cols,
            weightMap_[0].rows));

        cv::UMat _l = tmp_umat_vect_[img_idx - 1](cv::Rect(
            roi_vect_[img_idx - 1].x + roi_vect_[img_idx - 1].width,
            roi_vect_[img_idx - 1].y,
            weightMap_[0].cols,
            weightMap_[0].rows));
        cv::multiply(_r, weightMap_[0], _r, 1. / 255.);
        cv::multiply(_l, weightMap_[1], _l, 1. / 255.);
        cv::add(_r, _l, _r);
    }

    // Apply ROI
    int cols = 0;
    for (size_t i = 0; i < img_idx; i++) {
        cols += roi_vect_[i].width;
    }

    tmp_umat_vect_[img_idx](roi_vect_[img_idx]).copyTo(
        image_concat_umat(cv::Rect(cols, 0, roi_vect_[img_idx].width, roi_vect_[img_idx].height))
    );
}