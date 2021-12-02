# Image Type

## VImageKind

Import statement:

```python
from vkit.image.type import VImageKind
```

`VImageKind` can be used to tag the image type for an `VImage` object：

```python
class VImageKind(Enum):
    RGB = auto()
    RGB_GCN = auto()
    RGBA = auto()
    HSV = auto()
    HSV_GCN = auto()
    GRAYSCALE = auto()
    GRAYSCALE_GCN = auto()
    NONE = auto()
```

Explanations:

* `*_GCN`: represents the GCN (Global Contrast Normalization) resultant type from the corresponding image type
* `RGB`: associates `mat.ndim = 3`, `mat.dtype = np.uint8`
* `RGB_GCN`: associates `mat.ndim = 3`, `mat.dtype = np.float32`
* `RGBA`: associates `mat.ndim = 4`, `mat.dtype = np.uint8`
* `HSV`: associates `mat.ndim = 3`, `mat.dtype = np.uint8`
* `HSV_GCN`: associates `mat.ndim = 3`, `mat.dtype = np.float32`
* `GRAYSCALE`: associates `mat.ndim = 2`, `mat.dtype = np.uint8`
* `GRAYSCALE_GCN`: associates `mat.ndim = 2`, `mat.dtype = np.float32`
* `NONE`: Only used while initialising `VImage` . If `kind` was not explicitly passed into `VImage` constructor, vkit will infer the `kind` from `ndim` and `dtype` of `mat`

## VImage

Import statement:

```python
from vkit.image.type import VImage
```

`VImage` is the image data encapsulation provided by vkit. It supports I/O, normalisation, scaling and other common image manipulations. `VImage` has the following fields:

```python
@attr.define
class VImage:
    mat: npt.NDArray
    kind: VImageKind = VImageKind.NONE
```

Explanations:

* `mat`: a numpy array, its `ndim` and `dtype` will be associated to `kind`. Refer to the above `VImageKind` section for detail
* `kind`: tags the corresponding `mat`

Attributes of `VImage`:

* `height`: type `int`
* `width`: type `int`
* `shape`: (height, width), type `Tuple[int, int]`
* `num_channels`: number of channels, type `int`. If the `kind` field is either `GRAYSCALE` or `GRAYSCALE_GCN`, returns `0`

I/O methods available in `VImage`：

### `VImageKind.from_file`

Parameters: `path: PathType, disable_exif_orientation: bool = False`

Initialize a `VImage` object from an image file path. By default `disable_exif_orientation = False`, which instructs vkit to parse the EXIF metadata from the image file and perform image rotation accordingly

### `self.to_file`

Parameters: `path: PathType, disable_to_rgb_image: bool = False`

Export the `VImage` to a file. By default `disable_to_rgb_image: bool = False`, which saves the image using RGB image format

### `VImageKind.from_pil_image`

Parameters: `pil_image: Image.Image`

Initialize a `VImage` object from an `PIL.Image` object

### `self.to_pil_image`

Parameters: None

converts a `VImage` object to a `PIL.Image` object

Conversion methods available in `VImage`:

### `self.clone`

Parameters: None

Creates a copy of the `VImage`

### `self.to_grayscale_image`

Parameters: None

Converts the `VImage` into a `GRAYSCALE` image. If the `self` object is already of the `GRAYSCALE` type, returns a `clone` instance

### `self.to_rgb_image`

Parameters: None

Converts the `VImage` into a `RGB` image. If the `self` object is already of the `RGB` type, returns a `clone` instance

### `self.to_rgba_image`

Parameters: None

Converts the `VImage` into a `RGBA` image. If the `self` object is already of the `RGBA` type, returns a `clone` instance

### `self.to_hsv_image`

Parameters: None

Converts the `VImage` into a `HSV` image. If the `self` object is already of the `HSV` type, returns a `clone` instance

### `self.to_gcn_image`

Parameters: `lamb=0, eps=1E-8, scale=1.0`

perform GCN on the image, please refer to [this article](https://cedar.buffalo.edu/~srihari/CSE676/12.2%20Computer%20Vision.pdf) for detail

### `self.to_non_gcn_image`

Parameters: None

Converts the image to non GCN type, for example converting `RGB_GCN -> RGB`

### `self.to_rescaled_image`

Parameters: `self, height: int, width: int, cv_resize_interpolation: int = cv.INTER_CUBIC`

Scales the height and/or width of the image
