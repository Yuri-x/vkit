import json
import logging
import multiprocessing
import traceback
import random
from typing import Sequence

import iolite as io
import requests
import numpy as np
import cv2 as cv
from shapely.geometry import Polygon
import attr
from tqdm import tqdm

from vkit.label.vatti_clipping import dilate_polygon
from vkit.image.type import VImage

from vkit.label.type import (
    VImageMask,
    VImageMaskPolygonsMergeMode,
    VImageScoreMap,
    VPolygon,
    VTextPolygon,
)
from vkit.label.polygon_union import (
    unionize_polygons,
    get_line_lengths,
    estimate_shapely_polygon_height,
)
from vkit.label.visualization import (
    visualize_scale_image_score_map,
    visualize_image_mask,
    visualize_polygons,
    blend_image_with_image_mask,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def download_images(csv_file, output_folder, is_test=False):
    out_fd = io.folder(output_folder, touch=True)
    for line in io.read_csv_lines(csv_file, skip_header=True):
        raw_label = None
        if not is_test:
            id, image_url, raw_label = line
        else:
            id, image_url = line
        logger.info(f'Processing {id}')
        image_url = json.loads(image_url)['tfspath']

        image_ext = image_url.split('.')[-1]
        image_file = out_fd / f'{id}.{image_ext}'
        json_file = out_fd / f'{id}.json'

        if not image_file.exists():
            try:
                with requests.get(image_url, stream=True) as rsp:
                    rsp.raise_for_status()
                    with image_file.open('wb') as fout:
                        for chunk in rsp.iter_content(chunk_size=8192):
                            fout.write(chunk)

            except Exception:
                logger.info('Failed to download.')
                image_file.unlink(missing_ok=True)
                json_file.unlink(missing_ok=True)
                continue

        if not is_test:
            assert raw_label
            raw_labels = json.loads(raw_label)
            assert len(raw_labels) == 2

            text_lines = []
            for raw_label in raw_labels[0]:
                raw_label_text = json.loads(raw_label['text'])
                text = raw_label_text['text']
                text = text.strip()
                if not text:
                    logger.warning('text is empty.')
                    continue
                direction = raw_label_text.get('direction')
                raw_label['text'] = text
                raw_label['direction'] = direction
                text_lines.append(raw_label)

            assert list(raw_labels[1]) == ['option']
            option = raw_labels[1]['option']

            if not text_lines:
                logger.warning('text_lines is empty.')
                image_file.unlink(missing_ok=True)
                json_file.unlink(missing_ok=True)
                continue

            label = {
                'text_lines': text_lines,
                'option': option,
            }
            io.write_json(json_file, label, ensure_ascii=False, indent=2)


def read_text_polygons(json_file):
    text_polygons = []

    for item in io.read_json(json_file)['text_lines']:
        assert item['text']
        coord = item['coord']
        assert len(coord) == 8

        text_polygons.append(
            VTextPolygon(
                text=item['text'],
                polygon=VPolygon.from_flatten_xy_pairs(coord),
                meta={'direction': item['direction']},
            )
        )

    return text_polygons


def read_image_and_text_polygons(image_file, json_file):
    image = VImage.from_file(image_file)

    text_polygons = read_text_polygons(json_file)
    for text_polygon in text_polygons:
        text_polygon.polygon = text_polygon.polygon.to_clipped_polygon(image)

    return image, text_polygons


def estimate_polygon_height(polygon: VPolygon, text):
    xy_pairs = polygon.to_xy_pairs()
    shapely_polygon = Polygon(xy_pairs)
    if len(text) == 1:
        return max(get_line_lengths(shapely_polygon))
    else:
        return estimate_shapely_polygon_height(shapely_polygon)


def generate_scores_from_text_polygons(text_polygons):
    polygon_heights = np.asarray(
        [
            estimate_polygon_height(text_polygon.polygon, text_polygon.text)
            for text_polygon in text_polygons
        ],
        dtype=np.float32,
    )
    if len(polygon_heights) == 1:
        return [1.0]
    else:
        # Use median height as reference.
        return polygon_heights / np.median(polygon_heights)


@attr.define
class ScaleSample:
    image: VImage
    text_polygons: Sequence[VTextPolygon]
    text_scale_map: VImageScoreMap
    text_mask: VImageMask


def convert_to_scale_sample(
    image: VImage,
    text_polygons: Sequence[VTextPolygon],
    dilate_ratio: float,
    long_side: int,
):
    polygons = [text_polygon.polygon for text_polygon in text_polygons]

    scores = generate_scores_from_text_polygons(text_polygons)
    score_map = VImageScoreMap.from_image_and_polygon_value_pairs(
        image,
        zip(polygons, scores),
    )

    dilated_polygons = []
    for polygon in polygons:
        dilated_polygon, _ = dilate_polygon(polygon, dilate_ratio)
        dilated_polygon = dilated_polygon.to_clipped_polygon(image)
        dilated_polygons.append(dilated_polygon)

    unionized_polygons, _ = unionize_polygons(dilated_polygons)

    polygons_mask = VImageMask.from_image_and_polygons(
        image,
        polygons,
        VImageMaskPolygonsMergeMode.DISTINCT,
    )
    unionized_mask = VImageMask.from_image_and_polygons(
        image,
        unionized_polygons,
        VImageMaskPolygonsMergeMode.DISTINCT,
    )

    # Add delta to score map.
    score_map.mat += 100.0  # type: ignore
    # Reset unmasked region to zero.
    score_map.mat[polygons_mask.mat == 0] = 0.0

    # Inpaint.
    inpaint_mask_mat = ((unionized_mask.mat > 0) & (polygons_mask.mat == 0))  # type: ignore
    inpaint_mask_mat = inpaint_mask_mat.astype(np.uint8)
    score_map.mat = cv.inpaint(score_map.mat, inpaint_mask_mat, 1, cv.INPAINT_NS)

    # Set zero-value region as invalid.
    unionized_mask.mat[score_map.mat < 90.0] = 0
    # Minus delta.
    score_map.mat -= 100.0

    if long_side:
        long_side = round(long_side)
        if image.height > image.width:
            rescaled_height = long_side
            rescaled_width = round(image.width * rescaled_height / image.height)
        else:
            rescaled_width = long_side
            rescaled_height = round(image.height * rescaled_width / image.width)

        text_polygons = [
            text_polygon.to_rescaled_text_polygon(image, rescaled_height, rescaled_width)
            for text_polygon in text_polygons
        ]
        image = image.to_rescaled_image(rescaled_height, rescaled_width)
        score_map = score_map.to_rescaled_image_score_map(rescaled_height, rescaled_width)
        unionized_mask = unionized_mask.to_rescaled_image_mask(rescaled_height, rescaled_width)

    return ScaleSample(
        image=image,
        text_polygons=text_polygons,
        text_scale_map=score_map,
        text_mask=unionized_mask,
    )


def generate_scale_sample(
    image_file,
    json_file,
    output_scale_sample_pkl,
    dilate_ratio,
    long_side,
):
    logger.info(f'Generating {output_scale_sample_pkl}')
    try:
        image, text_polygons = read_image_and_text_polygons(image_file, json_file)
        scale_sample = convert_to_scale_sample(
            image,
            text_polygons,
            dilate_ratio,
            long_side,
        )
        io.write_joblib(output_scale_sample_pkl, scale_sample)
    except Exception:
        logger.error(f'Failed {output_scale_sample_pkl}, ex={traceback.format_exc()}')


def generate_scale_samples_from_folder(
    input_folder,
    output_folder,
    dilate_ratio=0.7,
    long_side=720,
):
    in_fd = io.folder(input_folder, exists=True)
    out_fd = io.folder(output_folder, reset=True)

    args_group = []
    for image_file in in_fd.glob('*.jpg'):
        json_file = image_file.with_suffix('.json')
        output_scale_sample_pkl = out_fd / f'{image_file.stem}.pkl'
        args_group.append((
            image_file,
            json_file,
            output_scale_sample_pkl,
            dilate_ratio,
            long_side,
        ))

    with multiprocessing.Pool() as pool:
        for _ in tqdm(pool.starmap(generate_scale_sample, args_group)):
            pass


def vis_scale_samples(input_folder, output_folder, num_samples=10):
    in_fd = io.folder(input_folder, exists=True)
    out_fd = io.folder(output_folder, reset=True)

    pkl_files = list(in_fd.glob('*.pkl'))
    random.shuffle(pkl_files)

    for pkl_file in pkl_files[:num_samples]:
        scale_sample: ScaleSample = io.read_joblib(pkl_file)
        id = pkl_file.stem

        scale_sample.image.to_file(out_fd / f'{id}.png')

        polygons = [text_polygon.polygon for text_polygon in scale_sample.text_polygons]
        visualize_polygons(
            scale_sample.image,
            polygons,
        ).to_file(out_fd / f'{id}-polygon.png')

        image_text_scale_map = visualize_scale_image_score_map(
            scale_sample.text_scale_map,
            scale_sample.text_mask,
        )
        image_text_scale_map.to_file(out_fd / f'{id}-text-scale.png')

        visualize_image_mask(scale_sample.text_mask).to_file(out_fd / f'{id}-text-mask.png')

        blend_image_with_image_mask(
            image_text_scale_map,
            scale_sample.text_mask,
            scale_sample.image,
        ).to_file(out_fd / f'{id}-combined.png')
