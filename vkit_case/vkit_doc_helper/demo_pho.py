from vkit.image.type import VImage
from vkit.augmentation.photometric_distortion import (
    MeanShiftConfig,
    mean_shift,
)


def run(image_file, output_file):
    image = VImage.from_file(image_file)

    config = MeanShiftConfig(delta=100)
    new_image = mean_shift.distort_image(config, image)

    new_image.to_file(output_file)
