简体中文 | [English](README_EN.md)

# 认识 vkit

## 简介

vkit 是一个面向计算机视觉开发者，特别是文档图像分析与识别方向开发者的工具包，特性如下：

* 丰富的数据增强策略
  * 支持常见的光度畸变策略，如各类色彩空间操作、各类噪音
  * 支持常见的几何畸变策略，如各类仿射变换、各类非线性变换（如 Similarity MLS，基于相机模型的 3D 曲面、翻折效果等）
  * 支持图片与各种标注数据类型的一致变换
* 较为全面的数据类型封装支持
  * 如图片（image）、蒙板（mask）、评分图（score map）、框（box）、多边形（polygon） 等类型
* 面向文档图像分析与识别方向用户的数据方案 🚧
* 工业级代码质量
  * 友好的自动补全与类型检查支持
  * 自动化风格检查（基于 flake8）与静态类型分析（基于 pyright）
  * 完善的自动化测试流程 🚧

注：🚧 表示施工中，未完全支持

笔者希望可以通过 vkit：

* 将开发者从繁琐的数据治理细节中解放出来，将时间放在更有价值的部分，如数据治理策略、算法模型设计与调优等
* 整合常见的数据增强策略，构建工业级场景数据方案（即那些工业算法落地的 "secret sauce"）
* 基于 vkit 构建工业级开源文档图像分析与识别解决方案

## 安装

Python 版本要求：3.8, 3.9

开发版（追踪最新一个的 commit 的版本）：

```bash
pip install python-vkit-nightly
```

稳定版：还未发布，请先使用开发版尝鲜

## 近期计划

* 0.1.0
  - [ ] 使用文档
  - [ ] 使用文档（英文）
  - [x] 支持 Python 3.9
  - [ ] 完整 CI 测试流程
  - [ ] 支持字体渲染
  - [ ] 支持 OCR 文字检测（text detection）训练数据生成
  - [ ] 支持 OCR 文字识别（text recognition）训练数据生成

## 已发布稳定版本

TODO

# vkit 功能

## 几何畸变

### 接口使用

Import:

```python
from vkit.augmentation.geometric_distortion import (
    # 接口类型
    GeometricDistortion,
    # distort(...) 返回类型
    GeometricDistortionResult,
    # camera_cubic_curve 操作
    CameraModelConfig,
    CameraCubicCurveConfig,
    camera_cubic_curve,
)
```

`distort` 接口：

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

* `config_or_config_generator`：传入几何畸变配置，或者一个生成配置的函数。注意每种几何畸变的操作都有独立的配置类型
* `image`：需要进行几何畸变的图片
* `image_mask`, `image_score_map` 等皆为可选项，会对传入对象执行与 `image` 一致的几何畸变
* `get_active_image_mask`：如果设置，会在结果中返回 `active_image_mask` 蒙板，用于表示变换后属于原图的激活区域
* `get_config`：如果设置，会在结果中返回配置实例
* `get_state`：如果设置，会在结果中返回状态实例
* `rnd`：`np.random.RandomState` 实例，用于生成配置或者其他需要随机行为的操作

`distort` 接口返回类型：

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

示例输入与输出：

<div align="center">
    <img alt="Lenna.png" src="https://i.loli.net/2021/11/25/HFaygJjhuI2OxU1.png">
	<img alt="demo_output.png" src="https://i.loli.net/2021/11/25/Ww7yr3a25H4sUgN.png">
</div>

### camera_cubic_curve

描述：基于相机模型的与三次函数的 3D 曲面效果。

配置：

```python
@attr.define
class CameraModelConfig:
    rotation_unit_vec: Sequence[float]
    rotation_theta: float
    principal_point: Optional[Sequence[float]] = None
    focal_length: Optional[float] = None
    camera_distance: Optional[float] = None


@attr.define
class CameraCubicCurveConfig:
    curve_alpha: float
    curve_beta: float
    # Clockwise, [0, 180]
    curve_direction: float
    curve_scale: float
    camera_model_config: CameraModelConfig
    grid_size: int
```

其中：

* todo

效果示例：

<div align="center"><img alt="camera_cubic_curve.gif" src="https://i.loli.net/2021/11/25/B7Rpz46u5axO1sf.gif"></div>



### camera_plane_line_fold

描述：基于相机模型的翻折效果。

配置：

```python
@attr.define
class CameraPlaneLineFoldConfig:
    fold_point: Tuple[float, float]
    # Clockwise, [0, 180]
    fold_direction: float
    fold_perturb_vec: Tuple[float, float, float]
    fold_alpha: float
    camera_model_config: CameraModelConfig
    grid_size: int
```

其中：

* todo

效果示例：

<div align="center"><img alt="camera_plane_line_fold.gif" src="https://i.loli.net/2021/11/25/FLicMRwuA1tynrg.gif"></div>

## 光度畸变

## 图像类型

## 标注类型

# vkit 数据方案

TODO

# vkit 开发者指引

```bash
pyproject-init -r git@github.com:vkit-dev/vkit.git -p 3.8.12
```
