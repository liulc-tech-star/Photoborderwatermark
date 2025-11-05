import cv2
import numpy as np

def apply_vignette_border(image):
    # Assuming this function adds a vignette border to the image
    rows, cols = image.shape[:2]
    X_resultant_kernel = cv2.getGaussianKernel(cols, cols / 3)
    Y_resultant_kernel = cv2.getGaussianKernel(rows, rows / 3)
    Kernel = Y_resultant_kernel * X_resultant_kernel.T
    mask = 255 * Kernel / np.linalg.norm(Kernel)
    vignette_image = np.copy(image)
    for i in range(3):
        vignette_image[:,:,i] = vignette_image[:,:,i] * mask
    return np.uint8(vignette_image)

def apply_white_bottom_border(image):
    # Assuming this function adds a white bottom border to the image
    height, width, _ = image.shape
    border_height = int(height * 0.2)
    border = 255 * np.ones((border_height, width, 3), np.uint8)
    combined = np.vstack((image, border))
    return combined

def main():
    image_path = input('Enter the path to the image: ')
    image = cv2.imread(image_path)
    mode = input('Choose mode: 1 for vignette border, 2 for white bottom border: ')
    if mode == '1':
        result = apply_vignette_border(image)
    elif mode == '2':
        result = apply_white_bottom_border(image)
    else:
        print('Invalid mode chosen!')
        return
    output_path = input('Enter the output path for the modified image: ')
    cv2.imwrite(output_path, result)
    print('Image saved at:', output_path)

if __name__ == '__main__':
    main()