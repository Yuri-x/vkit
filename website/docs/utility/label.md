# label data type

## VPoint

import:

```python
from vkit.label.type import VPoint
```

`VPoint` represents a point on 2D plane：

```python
@attr.define
class VPoint:
    y: int
    x: int
```

Methods available in `VPoint`:

* `self.clone()`: returns a copy of the object
* `self.to_xy_pair()`: returns a tuple as `(x, y)`
* `self.to_clipped_point(image: VImage)`: generates a new `VPoint`, ensure no positional overflow/underflow would take place via clip operation
* `self.to_rescaled_point(image: VImage, rescaled_height: int, rescaled_width: int)`: Generates new `VPoint` based on rescaled target image's height and width. `image` represents the original image, `rescaled_height` and `rescaled_width` is the desired rescaled image's height and width respectively

## VPointList

import:

```python
from vkit.label.type import VPointList
```

`VPointList` is used to represent a list of `VPoint`：

```python
class VPointList(List[VPoint]):
    ...
```

Methods available in `VPointList`：

* `VPointList.from_np_array(np_points: npt.NDArray)`: converts a numpy array with shape `(*, 2)` (`[(x, y), ...]`) into a `VPointList` object
* `VPointList.from_xy_pairs(xy_pairs: Iterable[Tuple[int, int]])`: converts an `Iterable[Tuple[int, int]]` into a `VPointList` object
* `VPointList.from_flatten_xy_pairs(flatten_xy_pairs: Sequence[int])`: similar to `VPointList.from_xy_pairs`, however accepts the input in the format of `[x0, y0, x1, y1, ...]`
* `VPointList.from_point(point: VPoint)`: Returns a `VPointList` which contains the specified `point` object alone
* `self.clone()`: returns a copy of the object
* `self.to_xy_pairs()`: converts the `VPointList` into `List[Tuple[int, int]]`, aka the reverse operation of `VPointList.from_xy_pairs`
* `self.to_np_array()`: converts the `VPointList` into a numpy array, aka the reverse operation of `VPointList.from_np_array`
* `self.to_clipped_points(image: VImage)`: generates a new `VPointList` object, ensures no positional overflow/underflow via clip operation
* `self.to_rescaled_points(image: VImage, rescaled_height: int, rescaled_width: int)`: Generates a new `VPointList` based on rescaled target image's height and width. `image` represents the original image, `rescaled_height` and `rescaled_width` is the desired rescaled image's height and width respectively

## VBox

import:

```python
from vkit.label.type import VBox
```

`VBox` is used to represent rectangular labeled area which is horizontal and vertical

```python
@attr.define
class VBox:
    up: int
    down: int
    left: int
    right: int
```

Explanation:

* `up` and `left` represents the coordinate of the top left corner
* `up` and `right` represents the coordinate of the top right corner
* `down` and `left` represents the coordinate of the bottom left corner
* `down` and `right` represents the coordinate of the bottom right corner
* VBox is therefore a rectangular enclosed by the 4 points mentioned above

attributes of `VBox`:

* `height`: type `int`
* `width`: type `int`
* `shape`: (height, width), type `Tuple[int, int]`

Methods available for `VBox`:

* `self.clone()`: Creates a copy of the `VBox`
* `self.to_clipped_box(image: VImage)`: generates a new `VBox` object, ensures no positional overflow/underflow via clip operation
* `self.extract_image(image: VImage)`: extracts part of a `image` surrounded by a `VBox` object, returns a `VImage` object. Note that this method will not generate a new numpy array, therefore explicit `clone` is required

## VPolygon

import:

```python
from vkit.label.type import VPolygon
```

`VPolygon` represents a polygon shaped area

```python
@attr.define
class VPolygon:
    points: VPointList
```

Methods available for `VPolygon`:

* `VPolygon.from_np_array(np_points: npt.NDArray)`: calls `VPointList.from_np_array` to generate `self.points`
* `VPolygon.from_xy_pairs(xy_pairs)`: calls `VPointList.from_xy_pairs` to generate `self.points`
* `VPolygon.from_flatten_xy_pairs(xy_pairs: Sequence[int])`: calls `VPointList.from_flatten_xy_pairs` to generate`self.points`
* `self.to_xy_pairs()`, `self.to_np_array()` and `self.to_clipped_points` will all call methods defined in `VPointList` with the same name and output in the same type
* `self.to_clipped_polygon()` returns `VPolygon` while `self.to_clipped_points()` returns `VPointList`
* `self.to_bounding_box_with_np_points(shift_np_points: bool = False)`: returns `Tuple[VBox, npt.NDArray]`, which is the bounding `VBox` object and `self.points` converted to a numpy array. If `shift_np_points` was set to `True`, the point that was closest to origin will be the new origin (aka. shift to `(0, 0)`)
* `self.to_bounding_box()`: returns the `VBox` explained in `self.to_bounding_box_with_np_points`
* `self.to_rescaled_polygon(image: VImage, rescaled_height: int, rescaled_width: int)`: Generates a new `VPolygon` based on rescaled target image's height and width. `image` represents the original image, `rescaled_height` and `rescaled_width` is the desired rescaled image's height and width respectively
* `self.clone()`: returns a copy of the object

## VTextPolygon

import:

```python
from vkit.label.type import VTextPolygon
```

`VTextPolygon` represents a polygon area tagged with text label:

```python
@attr.define
class VTextPolygon:
    text: str
    polygon: VPolygon
    meta: Optional[Dict[str, Any]] = None
```

Explanation:

* `text`: must not be empty or `None`
* `meta`: Optional, can be used to keep other metadata

Methods available for `VTextPolygon`:

* `self.to_rescaled_text_polygon(image: VImage, rescaled_height: int, rescaled_width: int)`Generates a new `VTextPolygon` based on rescaled target image's height and width. `image` represents the original image, `rescaled_height` and `rescaled_width` is the desired rescaled image's height and width respectively

## VImageMask

import:

```python
from vkit.label.type import VImageMask
```

`VImageMask` represents a mask label:

```python
@attr.define
class VImageMask:
    mat: npt.NDArray
```

Explanation:

* `mat` fulfills `ndim = 2` and `dtype = np.uint8`

Attributes of `VImageMask`:

* `height`: type `int`
* `width`: type `int`
* `shape`: (height, width), type `Tuple[int, int]`

Methods available for `VImageMask`:

* `VImageMask.from_shape(height: int, width: int)`: initialise `VImageMask` from `shape`, while all elements in `mat` will be initialised to `0`
* `VImageMask.from_shape_and_polygons(height: int, width: int, polygons: Iterable[VPolygon], mode: VImageMaskPolygonsMergeMode = VImageMaskPolygonsMergeMode.UNION)`: initialise `VImageMask` from `shape` and one or more `VPolygon`. The default `mode == VImageMaskPolygonsMergeMode.UNION` sets the areas covered by any of the `VPolygon` to `1`; If `mode == VImageMaskPolygonsMergeMode.DISTINCT`, only sets non-overlapping areas to `1`; similarly, if `mode == VImageMaskPolygonsMergeMode.INTERSECTION`, only sets areas where overlap exist to `1`
* `VImageMask.from_image_and_polygons(image: VImage, polygons: Iterable[VPolygon], mode: VImageMaskPolygonsMergeMode = VImageMaskPolygonsMergeMode.UNION)`: similar to `VImageMask.from_shape_and_polygons`, however `image.shape` will be used instead
* `self.to_rescaled_image_mask(height: int, width: int, cv_resize_interpolation: int = cv.INTER_NEAREST_EXACT)`: rescale the height and width of the mask
* `self.clone()`: returns a copy of the object

## VImageScoreMap

import:

```python
from vkit.label.type import VImageScoreMap
```

`VImageScoreMap` represents a score map：

```python
@attr.define
class VImageScoreMap:
    mat: npt.NDArray
```

Explanation:

* `mat` fulfills `ndim = 2` and `dtype = np.float32`

Attributes of `VImageScoreMap`:

* `height`: type `int`
* `width`: type `int`
* `shape`: (height, width), type `Tuple[int, int]`

Methods available in `VImageScoreMap`：

* `VImageScoreMap.from_image_mask(image_mask: VImageMask)`: converts from a `VImageMask` to a `VImageScoreMap`
* `VImageScoreMap.from_shape_and_polygon_value_pairs(height: int, width: int, polygon_value_pairs: Iterable[Tuple[VPolygon, float]])`: initialise a `VImageScoreMap` with the provided height and width, the float value in the `Tuple[VPolygon, float]` will be used as the score
* `VImageScoreMap.from_image_and_polygon_value_pairs(image: VImage, polygon_value_pairs: Iterable[Tuple[VPolygon, float]])`: similar to `VImageScoreMap.from_shape_and_polygon_value_pairs`, however `image.shape` will be used instead for the height and width
