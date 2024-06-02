#ifndef IMAGE_STITCHER_H
#define IMAGE_STITCHER_H

#include <vector>
#include <opencv2/opencv.hpp>

class ImageStitcher {
public:
    void SetParams(
        const int& blend_width,
        std::vector<cv::UMat>& undist_xmap_vector,
        std::vector<cv::UMat>& undist_ymap_vector,
        std::vector<cv::UMat>& reproj_xmap_vector,
        std::vector<cv::UMat>& reproj_ymap_vector,
        std::vector<cv::Rect>& projected_image_roi_vect_refined
    );

    void WarpImages(
        const int& img_idx,
        const int& fusion_pixel,
        const std::vector<cv::UMat>& image_vector,
        std::vector<cv::UMat>& images_warped_with_roi_vector,
        cv::UMat& image_concat_umat
    );

private:
    int num_img_;
    std::vector<cv::UMat> undist_xmap_vector_;
    std::vector<cv::UMat> undist_ymap_vector_;
    std::vector<cv::UMat> reproj_xmap_vector_;
    std::vector<cv::UMat> reproj_ymap_vector_;
    std::vector<cv::Rect> roi_vect_;
    std::vector<cv::UMat> final_xmap_vector_;
    std::vector<cv::UMat> final_ymap_vector_;
    std::vector<cv::UMat> tmp_umat_vect_;
    std::vector<cv::UMat> weightMap_;
    
    void CreateWeightMap(const int& height, const int& width);
};

#endif // IMAGE_STITCHER_H