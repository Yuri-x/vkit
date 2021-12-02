# Labeled Data Type

## VPoint

Import statement:

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

### `self.clone`

Parameters: None


Returns a copy of the object

### `self.to_xy_pair`

Parameters: None

Returns a tuple as `(x, y)`

### `self.to_clipped_point`

Parameters: `image: VImage`

Generates a new `VPoint`, ensure no positional overflow/underflow would take place via clip operation

### `self.to_rescaled_point`

Parameters: `image: VImage, rescaled_height: int, rescaled_width: int`

Generates new `VPoint` based on rescaled target image's height and width. `image` represents the original image, `rescaled_height` and `rescaled_width` is the desired rescaled image's height and width respectively

## VPointList

Import statement:

```python
from vkit.label.type import VPointList
```

`VPointList` is used to represent a list of `VPoint`：

```python
class VPointList(List[VPoint]):
    ...
```

Methods available in `VPointList`：

### `VPointList.from_np_array`

Parameters: `np_points: npt.NDArray`

Converts a numpy array with shape `(*, 2)` (`[(x, y), ...]`) into a `VPointList` object

### `VPointList.from_xy_pairs`

Parameters: `xy_pairs: Iterable[Tuple[int, int]]`

Converts an `Iterable[Tuple[int, int]]` into a `VPointList` object

### `VPointList.from_flatten_xy_pairs`

Parameters: `flatten_xy_pairs: Sequence[int]`

Similar to `VPointList.from_xy_pairs`, however accepts the input in the format of `[x0, y0, x1, y1, ...]`

### `VPointList.from_point`

Parameters: `point: VPoint`

Returns a `VPointList` which contains the specified `point` object alone

### `self.clone`

Parameters: None

Returns a copy of the object

### `self.to_xy_pairs`

Parameters: None

Converts the `VPointList` into `List[Tuple[int, int]]`, aka the reverse operation of `VPointList.from_xy_pairs`

### `self.to_np_array`

Parameters: None

Converts the `VPointList` into a numpy array, aka the reverse operation of `VPointList.from_np_array`

### `self.to_clipped_points`

Parameters: `image: VImage`

Generates a new `VPointList` object, ensures no positional overflow/underflow via clip operation

### `self.to_rescaled_points`

Parameters: `image: VImage, rescaled_height: int, rescaled_width: int`

Generates a new `VPointList` based on rescaled target image's height and width. `image` represents the original image, `rescaled_height` and `rescaled_width` is the desired rescaled image's height and width respectively

## VBox

Import statement:

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

Attributes of `VBox`:

* `height`: type `int`
* `width`: type `int`
* `shape`: (height, width), type `Tuple[int, int]`

Methods available for `VBox`:

### `self.clone`

Parameters: None

Creates a copy of the `VBox`

### `self.to_clipped_box`

Parameters: `image: VImage`

Generates a new `VBox` object, ensures no positional overflow/underflow via clip operation

### `self.extract_image`

Parameters: `image: VImage`

Extracts part of a `image` surrounded by a `VBox` object, returns a `VImage` object. Note that this method will not generate a new numpy array, therefore explicit `clone` is required

## VPolygon

Import statement:

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

### `VPolygon.from_np_array`

Parameters: `np_points: npt.NDArray`

Calls `VPointList.from_np_array` to generate `self.points`

### `VPolygon.from_xy_pairs`

Parameters: `xy_pairs`

Calls `VPointList.from_xy_pairs` to generate `self.points`

### `VPolygon.from_flatten_xy_pairs`

Parameters: `xy_pairs: Sequence[int]`

Calls `VPointList.from_flatten_xy_pairs` to generate`self.points`

### `self.to_xy_pairs`, `self.to_np_array` and `self.to_clipped_points`

Will all call methods defined in `VPointList` with the same name and output in the same type

### `self.to_clipped_polygon`

Parameters: None

Returns `VPolygon` while `self.to_clipped_points()` returns `VPointList`

### `self.to_bounding_box_with_np_points`

Parameters: `shift_np_points: bool = False`

Returns `Tuple[VBox, npt.NDArray]`, which is the bounding `VBox` object and `self.points` converted to a numpy array. If `shift_np_points` was set to `True`, the point that was closest to origin will be the new origin (aka. shift to `(0, 0)`)

### `self.to_bounding_box`

Parameters: None

Returns the `VBox` explained in `self.to_bounding_box_with_np_points`

### `self.to_rescaled_polygon`

Parameters: `image: VImage, rescaled_height: int, rescaled_width: int`

Generates a new `VPolygon` based on rescaled target image's height and width. `image` represents the original image, `rescaled_height` and `rescaled_width` is the desired rescaled image's height and width respectively

### `self.clone`

Parameters: None

Returns a copy of the object

## VTextPolygon

Import statement:

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

### `self.to_rescaled_text_polygon`

Parameters: `image: VImage, rescaled_height: int, rescaled_width: int`

Generates a new `VTextPolygon` based on rescaled target image's height and width. `image` represents the original image, `rescaled_height` and `rescaled_width` is the desired rescaled image's height and width respectively

## VImageMask

Import statement:

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

### `VImageMask.from_shape`

Parameters: `height: int, width: int`

Initialize `VImageMask` from `shape`, while all elements in `mat` will be initialized to `0`

### `VImageMask.from_shape_and_polygons`

Parameters: `height: int, width: int, polygons: Iterable[VPolygon], mode: VImageMaskPolygonsMergeMode = VImageMaskPolygonsMergeMode.UNION`

Initialize `VImageMask` from `shape` and one or more `VPolygon`.

The default `mode == VImageMaskPolygonsMergeMode.UNION` sets the areas covered by any of the `VPolygon` to `1`; If `mode == VImageMaskPolygonsMergeMode.DISTINCT`, only sets non-overlapping areas to `1`; Similarly, if `mode == VImageMaskPolygonsMergeMode.INTERSECTION`, only sets areas where overlap exist to `1`

### `VImageMask.from_image_and_polygons`

Parameters: `image: VImage, polygons: Iterable[VPolygon], mode: VImageMaskPolygonsMergeMode = VImageMaskPolygonsMergeMode.UNION`

Similar to `VImageMask.from_shape_and_polygons`, however `image.shape` will be used instead

### `self.to_rescaled_image_mask`

Parameters: `height: int, width: int, cv_resize_interpolation: int = cv.INTER_NEAREST_EXACT`

Rescale the height and width of the mask

### `self.clone`

Parameters: None

Returns a copy of the object

## VImageScoreMap

Import statement:

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

### `VImageScoreMap.from_image_mask`

Parameters: `image_mask: VImageMask`

Converts from a `VImageMask` to a `VImageScoreMap`

### `VImageScoreMap.from_shape_and_polygon_value_pairs`

Parameters: `height: int, width: int, polygon_value_pairs: Iterable[Tuple[VPolygon, float]]`

Initialize a `VImageScoreMap` with the provided height and width, the float value in the `Tuple[VPolygon, float]` will be used as the score

### `VImageScoreMap.from_image_and_polygon_value_pairs`

Parameters: `image: VImage, polygon_value_pairs: Iterable[Tuple[VPolygon, float]]`

Similar to `VImageScoreMap.from_shape_and_polygon_value_pairs`, however `image.shape` will be used instead for the height and width
