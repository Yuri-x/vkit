### 接口使用

Import 示例:

```python
from vkit.augmentation.geometric_distortion import (
    # 接口类型
    GeometricDistortion,
    # distort(...) 返回类型
    GeometricDistortionResult,
    # 具体的几何畸变实现
    ...
)
```

`GeometricDistortion.distort` 接口：

```python
def distort(
    self,
    config_or_config_generator: Union[T_CONFIG,
                                      Callable[[Tuple[int, int], np.random.RandomState],
                                               T_CONFIG]],
    image: VImage,
    image_mask: Optional[VImageMask] = None,
    image_score_map: Optional[VImageScoreMap] = None,
    point: Optional[VPoint] = None,
    points: Optional[VPointList] = None,
    polygon: Optional[VPolygon] = None,
    polygons: Optional[Iterable[VPolygon]] = None,
    get_active_image_mask: bool = False,
    get_config: bool = False,
    get_state: bool = False,
    rnd: Optional[np.random.RandomState] = None,
) -> GeometricDistortionResult:
    ...
```

其中：

* `config_or_config_generator`：几何畸变配置，或者一个生成配置的函数。每种几何畸变的操作，都有对应的独立配置类型，如 `camera_cubic_curve` 对应 `CameraCubicCurveConfig`
* `image`：需要进行几何畸变的图片
* `image_mask`, `image_score_map` 等皆为可选项，会对传入对象执行与 `image` 一致的几何畸变
* `get_active_image_mask`：如果设置，会在结果中返回 `active_image_mask` 蒙板，用于表示变换后属于原图的激活区域
* `get_config`：如果设置，会在结果中返回配置实例
* `get_state`：如果设置，会在结果中返回状态实例
* `rnd`：`np.random.RandomState` 实例，用于生成配置或者其他需要随机行为的操作

`GeometricDistortion.distort` 接口返回类型：

```python
@attr.define
class GeometricDistortionResult:
    image: VImage
    image_mask: Optional[VImageMask] = None
    image_score_map: Optional[VImageScoreMap] = None
    active_image_mask: Optional[VImageMask] = None
    point: Optional[VPoint] = None
    points: Optional[VPointList] = None
    polygon: Optional[VPolygon] = None
    polygons: Optional[Sequence[VPolygon]] = None
    config: Optional[Any] = None
    state: Optional[Any] = None
```

其中，返回的字段对应传入参数。

简单的可执行调用示例：

```python
from vkit.image.type import VImage
from vkit.augmentation.geometric_distortion import (
    CameraModelConfig,
    CameraCubicCurveConfig,
    camera_cubic_curve,
)


def run(image_file, output_file):
    image = VImage.from_file(image_file)

    config = CameraCubicCurveConfig(
        curve_alpha=60,
        curve_beta=-60,
        curve_direction=0,
        curve_scale=1.0,
        camera_model_config=CameraModelConfig(
            rotation_unit_vec=[1.0, 0.0, 0.0],
            rotation_theta=30,
        ),
        grid_size=10,
    )
    result = camera_cubic_curve.distort(config, image)

    result.image.to_file(output_file)

```

可以通过 `fireball` (`pip install fireball`) 直接调用以上示例：

```bash
fib vkit_case.vkit_doc_helper.demo:run \
    --image_file="REQUIRED" \
    --output_file="REQUIRED"
```

以下是示例输入与输出：

<div align="center">
    <img alt="Lenna.png" src="https://i.loli.net/2021/11/25/HFaygJjhuI2OxU1.png">
	<img alt="demo_output.png" src="https://i.loli.net/2021/11/25/Ww7yr3a25H4sUgN.png">
</div>
下面是几何畸变的具体实现
