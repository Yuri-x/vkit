# 标注类型

## VPoint

import：

```python
from vkit.label.type import VPoint
```

`VPoint` 用于表示二维平面上的点：

```python
@attr.define
class VPoint:
    y: int
    x: int
```

`VPoint` 的方法：

* `self.clone()` ：返回拷贝
* `self.to_xy_pair()`：返回 `(x, y)`
* `self.to_clipped_point(image: VImage)`：生成新的 `VPoint` ，通过 clip 操作保证不会出现位置的 overflow/underflow
* `self.to_rescaled_point(image: VImage, rescaled_height: int, rescaled_width: int)`：基于目标缩放图片的高度与宽度，生成新的 `VPoint`。`image` 是缩放前图片，`rescaled_height` 与 `rescaled_width` 是缩放后的图片高度与宽度

## VPointList

import：

```python
from vkit.label.type import VPointList
```

`VPointList` 用于表示 `VPoint` 数组：

```python
class VPointList(List[VPoint]):
    ...
```

`VPointList` 的方法：

* `VPointList.from_np_array(np_points: npt.NDArray)`：将 numpy array `(*, 2)` （`[(x, y), ...]`）转换为 `VPointList`
* `VPointList.from_xy_pairs(xy_pairs: Iterable[Tuple[int, int]])`： 将 `Iterable[Tuple[int, int]]` 转换为  `VPointList`
* `VPointList.from_flatten_xy_pairs(flatten_xy_pairs: Sequence[int])`：类似 `VPointList.from_xy_pairs`，但输入形式为 `[x0, y0, x1, y1, ...]`
* `VPointList.from_point(point: VPoint)`：返回包含 `point` 为唯一元素的 `VPointList`
* `self.clone()`：返回拷贝
* `self.to_xy_pairs()`：转换为 `List[Tuple[int, int]]` 格式，即 `VPointList.from_xy_pairs` 的逆过程
* `self.to_np_array()`：转换为 numpy array，即 `VPointList.from_np_array` 的逆过程
* `self.to_clipped_points(image: VImage)`：生成新的 `VPointList` ，通过 clip 操作保证不会出现位置的 overflow/underflow
* `self.to_rescaled_points(image: VImage, rescaled_height: int, rescaled_width: int)`：基于目标缩放图片的高度与宽度，生成新的 `VPointList`。`image` 是缩放前图片，`rescaled_height` 与 `rescaled_width` 是缩放后的图片高度与宽度

## VBox

import：

```python
from vkit.label.type import VBox
```

`VBox` 用于表示横平竖直的矩形标注区域：

```python
@attr.define
class VBox:
    up: int
    down: int
    left: int
    right: int
```

其中：

* `down` 与 `right` 的表示是闭区间端点

`VBox` 的属性：

* `height`：高度，类型 `int`
* `width`：宽度，类型 `int`
* `shape`：（高度，宽度），类型 `Tuple[int, int]`

`VBox`  的方法：

* `self.clone()`：返回拷贝
* `self.to_clipped_box(image: VImage)`：生成新的 `VBox` ，通过 clip 操作保证不会出现位置的 overflow/underflow
* `self.extract_image(image: VImage)`：从 `image` 中抽取 `VBox`  划定的区域，返回一个新的 `VImage`。需要注意，这个操作不会产生一个新的 numpy array，如有需要得显式地调用 `clone`

## VPolygon

import：

```python
from vkit.label.type import VPolygon
```

`VPolygon` 用于表示多边形标注区域：

```python
@attr.define
class VPolygon:
    points: VPointList
```

`VPolygon` 的方法：

* `VPolygon.from_np_array(np_points: npt.NDArray)`：调用 `VPointList.from_np_array` 生成 `self.points`
* `VPolygon.from_xy_pairs(xy_pairs)`：调用 `VPointList.from_xy_pairs` 生成 `self.points`
* `VPolygon.from_flatten_xy_pairs(xy_pairs: Sequence[int])`：调用 `VPointList.from_flatten_xy_pairs` 生成 `self.points`
* `self.to_xy_pairs()`、`self.to_np_array()`、`self.to_clipped_points` 皆在内部调用 `VPointList` 同名方法，生成同样类型的输出
* `self.to_clipped_polygon()` 与 `self.to_clipped_points()`，区别在于返回 `VPolygon`
* `self.to_bounding_box_with_np_points(shift_np_points: bool = False)`：返回 `Tuple[VBox, npt.NDArray]` ，即外接矩形 `VBox` 与转为 numpy array 格式的  `self.points`。如果将 `shift_np_points` 设为 `True`，则会将 numpy array 中离原点最近的点设为原点（shift 至 `(0, 0)`）
* `self.to_bounding_box()`：返回 `self.to_bounding_box_with_np_points` 中的 `VBox`
* `self.to_rescaled_polygon(image: VImage, rescaled_height: int, rescaled_width: int)`：基于目标缩放图片的高度与宽度，生成新的 `VPolygon`。`image` 是缩放前图片，`rescaled_height` 与 `rescaled_width` 是缩放后的图片高度与宽度
* `self.clone()`：返回拷贝

## VTextPolygon

import：

```python
from vkit.label.type import VTextPolygon
```

`VTextPolygon` 用于表示带文本标注的多边形标注区域：

```python
@attr.define
class VTextPolygon:
    text: str
    polygon: VPolygon
    meta: Optional[Dict[str, Any]] = None
```

其中：

* `text`：必须不为空
* `meta`：可选。用于存储额外字段

`VTextPolygon` 的方法：

* `self.to_rescaled_text_polygon(image: VImage, rescaled_height: int, rescaled_width: int)`：基于目标缩放图片的高度与宽度，生成新的 `VTextPolygon`。`image` 是缩放前图片，`rescaled_height` 与 `rescaled_width` 是缩放后的图片高度与宽度

## VImageMask

import：

```python
from vkit.label.type import VImageMask
```

`VImageMask` 用于表示蒙板（mask）标注：

```python
@attr.define
class VImageMask:
    mat: npt.NDArray
```

其中：

* `mat`：`ndim = 2` 且 `dtype = np.uint8`

`VImageMask` 的属性：

* `height`：高，类型 `int`
* `width`：宽，类型 `int`
* `shape`：（高，宽），类型 `Tuple[int, int]`

`VImageMask` 的方法：

* `VImageMask.from_shape(height: int, width: int)`：从形状初始化 `VImageMask`，`mat` 初始化为 `0`
* `VImageMask.from_shape_and_polygons(height: int, width: int, polygons: Iterable[VPolygon], mode: VImageMaskPolygonsMergeMode = VImageMaskPolygonsMergeMode.UNION)`：从形状与多边形初始化 `VImageMask`。默认 `mode == VImageMaskPolygonsMergeMode.UNION` 时，将所有多边形区域设为 `1`；如果  `mode == VImageMaskPolygonsMergeMode.DISTINCT`，只将非相交区域设为 `1`；如果  `mode == VImageMaskPolygonsMergeMode.INTERSECTION`，只将重合区域设为 `1`
* `VImageMask.from_image_and_polygons(image: VImage, polygons: Iterable[VPolygon], mode: VImageMaskPolygonsMergeMode = VImageMaskPolygonsMergeMode.UNION)`：与 `VImageMask.from_shape_and_polygons` 类似，只不过会采用 `image.shape`
* `self.to_rescaled_image_mask(height: int, width: int, cv_resize_interpolation: int = cv.INTER_NEAREST_EXACT)`：缩放蒙板的高度与宽度
* `self.clone()`：返回拷贝

## VImageScoreMap

import：

```python
from vkit.label.type import VImageScoreMap
```

`VImageScoreMap` 用于表示评分图：

```python
@attr.define
class VImageScoreMap:
    mat: npt.NDArray
```

其中：

* `mat`：`ndim = 2` 且 `dtype = np.float32`

`VImageScoreMap` 的属性：

* `height`：高，类型 `int`
* `width`：宽，类型 `int`
* `shape`：（高，宽），类型 `Tuple[int, int]`

`VImageScoreMap` 的方法：

* `VImageScoreMap.from_image_mask(image_mask: VImageMask)`：从 `VImageMask` 转换生成
* `VImageScoreMap.from_shape_and_polygon_value_pairs(height: int, width: int, polygon_value_pairs: Iterable[Tuple[VPolygon, float]])`：初始化（高，宽）的评分图，图中的多边形使用对应的评分赋值
* `VImageScoreMap.from_image_and_polygon_value_pairs(image: VImage, polygon_value_pairs: Iterable[Tuple[VPolygon, float]])`：与 `VImageScoreMap.from_shape_and_polygon_value_pairs` 类似，只不过会采用 `image.shape`
