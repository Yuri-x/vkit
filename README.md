简体中文 | [English](README_EN.md)


# Table of Contents
* [vkit 总览](#vkit-总览)
	* [简介](#简介)
	* [安装](#安装)
	* [近期计划](#近期计划)
	* [已发布稳定版本](#已发布稳定版本)
	* [沟通途径](#沟通途径)
	* [赞助](#赞助)
* [vkit 功能](#vkit-功能)
	* [几何畸变](#几何畸变)
		* [接口使用](#接口使用)
		* [camera_cubic_curve](#camera_cubic_curve)
		* [camera_plane_line_fold](#camera_plane_line_fold)
		* [camera_plane_line_curve](#camera_plane_line_curve)
		* [similarity_mls](#similarity_mls)
		* [shear_hori](#shear_hori)
		* [shear_vert](#shear_vert)
		* [rotate](#rotate)
		* [skew_hori](#skew_hori)
		* [skew_vert](#skew_vert)
	* [光度畸变](#光度畸变)
	* [图像类型](#图像类型)
	* [标注类型](#标注类型)
* [vkit 数据方案](#vkit-数据方案)
* [vkit 开发者指引](#vkit-开发者指引)


# vkit 总览

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
  * 友好的代码自动补全与类型检查支持
  * 自动化风格检查（基于 flake8）与静态类型分析（基于 pyright）
  * 完善的自动化测试流程 🚧

注：🚧 表示施工中，未完全支持

笔者希望可以通过 vkit：

* 将开发者从繁琐的数据治理细节中解放出来，将时间放在更有价值的部分，如数据治理策略、算法模型设计与调优等
* 整合常见的数据增强策略，构建工业级场景数据方案（即那些工业算法落地的 "secret sauce"）
* 基于 vkit 构建工业级开源文档图像分析与识别解决方案

## 安装

Python 版本要求：3.8, 3.9 （由于第三方依赖等问题，目前没有兼容 3.8 以下版本的计划）

开发版本（追踪最新一个的 commit 的版本）：

```bash
pip install python-vkit-nightly
```

稳定版本：

```bash
pip install python-vkit
```

## 近期计划

* 0.1.0
  - [ ] 使用文档
  - [x] 支持 Python 3.9
* 0.2.0
  - [ ] 使用文档（英文）
  - [ ] 完整 CI 测试流程
  - [ ] 支持字体渲染
  - [ ] 支持 OCR 文字检测（text detection）训练数据生成
  - [ ] 支持 OCR 文字识别（text recognition）训练数据生成

## 已发布稳定版本

🚧

## 沟通途径

* 使用疑问、需求讨论等请移步 [Discussions](https://github.com/vkit-dev/vkit/discussions)
* 报 Bug 请移步 [Issues](https://github.com/vkit-dev/vkit/issues)

作者平日工作繁忙，只能在业余支持本项目，响应或有不及时等情况，请多多担待

## 赞助

赞助体系正在规划中，会在项目成长到一定阶段推出

如果本项目省了您的时间，可以考虑一下请我喝杯咖啡😄

<div align="center">
    <img alt="爱发电.jpg" width="400" src="https://i.loli.net/2021/11/28/xkQ3DFws9W1fBg4.jpg">
</div>
<div align="center">
    <a href="https://afdian.net/@huntzhan?tab=home">也可以点此传送至爱发电</a>
</div>

# vkit 功能


## 几何畸变


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

### camera_cubic_curve

描述：实现基于相机模型的与三次函数的 3D 曲面效果，参见 [Page dewarping](https://mzucker.github.io/2016/08/15/page-dewarping.html) 文中描述

import:

```python
from vkit.augmentation.geometric_distortion import (
    CameraModelConfig,
    CameraCubicCurveConfig,
    camera_cubic_curve,
)
```

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

* `CameraModelConfig` 是相机模型的配置（下同）
  * `rotation_unit_vec`：旋转单位向量，即旋转指向方向，具体见 [cv.Rodrigues](https://docs.opencv.org/4.5.3/d9/d0c/group__calib3d.html#ga61585db663d9da06b68e70cfbf6a1eac) 里的解释
  * `rotation_theta`：旋转的角度，区间 `[-180, 180]`。角度为正数，表示的方向与右手法则旋转方向一致
  * `principal_point`：可选。相机成像光学轴（optical axis）与图片的相交点，使用原图的坐标表示。如果不提供，默认会设定为图片的中心点
  * `focal_length`：可选。相机成像光学轴的焦距。如果不提供，会采用图像长宽中较大值作为焦距
  * `camera_distance`：可选。指定相机坐标原点到 `principal_point` 的距离。如果不提供，会基于图片与成像屏幕相切的策略决定此距离

* `CameraCubicCurveConfig` 控制如何生成曲面
  * `curve_alpha`：投影左端点的斜率
  * `curve_beta`：投影右端点的斜率
  * `curve_direction`：投影线的方向，区间 `[0, 180]`。图片会按照这个方生成曲面，例如角度为 `0` 时曲面的“起伏”是横向的，`90` 时为纵向。基于投影位置，会生成 Z 轴的偏移量
  * `curve_scale`：控制 Z 轴的偏移量的放大倍数，建议设为 `1.0`
  * `grid_size`：网格的大小，下同。网格越小，几何畸变效果越好，性能越差


效果示例：

<div align="center"><img alt="camera_cubic_curve.gif" src="https://i.loli.net/2021/11/25/B7Rpz46u5axO1sf.gif"></div>

其中（下同）：

* 左上：形变后图片，`VImage`
* 右上：形变后多边形，`VPolygon`
* 左中：形变后图像平面网格，`VImageGrid`
* 右中：图像 `active_image_mask` 蒙板，`VIMageMask`
* 左下：形变后图像蒙版，`VImageMask`
* 右下：形变后评分图，`VImageScoreMap`

### camera_plane_line_fold

描述：实现基于相机模型与基准线的翻折效果，参见 [DocUNet: Document Image Unwarping via A Stacked U-Net](https://www3.cs.stonybrook.edu/~cvl/docunet.html) 文中描述

import:

```python
from vkit.augmentation.geometric_distortion import (
    CameraModelConfig,
    CameraPlaneLineFoldConfig,
    camera_plane_line_fold,
)
```

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

* `fold_point`  与  `fold_direction`  决定基准线。 `fold_point`  设为原图的某个点，`fold_direction` 为从该点出发的基准线角度，顺时针区值区间 `[0, 180]`
* `fold_perturb_vec`：为三维扰动向量。图中的点与基准线越接近，扰动越强，即 `p + w * fold_perturb_vec`
* `fold_alpha`： 控制 `w = fold_alpha / (fold_alpha + d)`，`d` 为点到翻折线的归一化距离。`fold_alpha` 的取值越靠近 `0`，翻折效果越强。推荐取值 `0.5`

效果示例：

<div align="center"><img alt="camera_plane_line_fold.gif" src="https://i.loli.net/2021/11/25/FLicMRwuA1tynrg.gif"></div>

### camera_plane_line_curve

描述：实现基于相机模型的与基准线的曲面效果，参见 [DocUNet: Document Image Unwarping via A Stacked U-Net](https://www3.cs.stonybrook.edu/~cvl/docunet.html) 文中描述

import:

```python
from vkit.augmentation.geometric_distortion import (
    CameraModelConfig,
    CameraPlaneLineCurveConfig,
    camera_plane_line_curve,
)
```

配置：

```python
@attr.define
class CameraPlaneLineCurveConfig:
    curve_point: Tuple[float, float]
    # Clockwise, [0, 180]
    curve_direction: float
    curve_perturb_vec: Tuple[float, float, float]
    curve_alpha: float
    camera_model_config: CameraModelConfig
    grid_size: int

```

其中：

* `curve_point`  与  `curve_direction`  决定基准线，同 `CameraPlaneLineFoldConfig`
* `curve_perturb_vec`：为三维扰动向量。同 `CameraPlaneLineFoldConfig`
* `curve_alpha`： 控制 `w = 1 - d^curve_alpha`，`d` 为点到基准线的归一化距离。`curve_alpha`  越小，越接近翻折的效果。推荐取值 `2.0`

效果示例：

<div align="center"><img alt="camera_plane_line_curve.gif" src="https://i.loli.net/2021/11/26/xcCPAUbZDflO3wj.gif"></div>

### similarity_mls

描述：参见 [Image Deformation Using Moving Least Squares](https://people.engr.tamu.edu/schaefer/research/mls.pdf) 文中的 similarity transformation 描述

import:

```python
from vkit.augmentation.geometric_distortion import (
    SimilarityMlsConfig,
    similarity_mls,
)
```

配置：

```python
@attr.define
class SimilarityMlsConfig:
    src_handle_points: Sequence[VPoint]
    dst_handle_points: Sequence[VPoint]
    grid_size: int
    rescale_as_src: bool = False
```

其中：

* `src_handle_points` 与 `dst_handle_points` 为形变控制点
* `rescale_as_src` 若设为 `True`，则强制输出图片尺寸与原图一致

效果示例：

<div align="center"><img alt="similarity_mls.gif" src="https://i.loli.net/2021/11/28/WjoHstxRJXmLzFT.gif"></div>

### shear_hori

描述：实现横向剪切效果

import：

```python
from vkit.augmentation.geometric_distortion import (
    ShearHoriConfig,
    shear_hori,
)
```

配置：

```python
@attr.define
class ShearHoriConfig:
    # angle: int, [-90, 90], positive value for rightward direction.
    angle: int
```

其中：

* `angle`：取值范围 `(-90, 90)`，正数为向右剪切角度，负数向左

效果示例：

<div align="center"><img alt="shear_hori.gif" src="https://i.loli.net/2021/11/28/N4wL5tZJGlocySb.gif"></div>

### shear_vert

描述：实现纵向剪切效果

import：

```python
from vkit.augmentation.geometric_distortion import (
    ShearVertConfig,
    shear_vert,
)
```

配置：

```python
@attr.define
class ShearVertConfig:
    # angle: int, (-90, 90), positive value for downward direction.
    angle: int
```

其中：

* `angle`：取值范围 `(-90, 90)`，正数为向下剪切角度，负数向上

效果示例：

<div align="center"><img alt="shear_vert.gif" src="https://i.loli.net/2021/11/28/f5niNrvgWbOdRoV.gif"></div>

### rotate

描述：实现旋转效果

import：

```python
from vkit.augmentation.geometric_distortion import (
    RotateConfig,
    rotate,
)
```

配置：

```python
@attr.define
class RotateConfig:
    # angle: int, [0, 360], clockwise angle.
    angle: int
```

其中：

* `angle`：取值范围 `[0, 360]`，为顺时针方向角度

效果示例：

<div align="center"><img alt="rotate.gif" src="https://i.loli.net/2021/11/28/SdbO4xeWZMQPC2U.gif"></div>

### skew_hori

描述：实现水平倾斜效果

import：

```python
from vkit.augmentation.geometric_distortion import (
    SkewHoriConfig,
    skew_hori,
)
```

配置：

```python
@attr.define
class SkewHoriConfig:
    # (-1.0, 0.0], shrink the left side.
    # [0.0, 1.0), shrink the right side.
    # The larger abs(ratio), the more to shrink.
    ratio: float
```

其中：

* `ratio`：表示纵向缩减比例，取值范围 `(-1.0, 1.0)`，正数缩减右边，负数缩减左边，绝对值越大缩减的量越大，倾斜效果越明显

效果示例：

<div align="center"><img alt="skew_hori.gif" src="https://i.loli.net/2021/11/28/C49MQJDF2GixlXP.gif"></div>

### skew_vert

描述：实现垂直倾斜效果

import：

```python
from vkit.augmentation.geometric_distortion import (
    SkewVertConfig,
    skew_vert,
)
```

配置：

```python
@attr.define
class SkewVertConfig:
    # (-1.0, 0.0], shrink the up side.
    # [0.0, 1.0), shrink the down side.
    # The larger abs(ratio), the more to shrink.
    ratio: float
```

其中：

* `ratio`：表示横向缩减比例，取值范围 `(-1.0, 1.0)`，正数缩减下边，负数缩减上边，绝对值越大缩减的量越大，倾斜效果越明显

效果示例：

<div align="center"><img alt="skew_vert.gif" src="https://i.loli.net/2021/11/28/V9cOmJZuRLXlk8r.gif"></div>








## 光度畸变

## 图像类型

## 标注类型

# vkit 数据方案

🚧

# vkit 开发者指引

🚧

```bash
pyproject-init -r git@github.com:vkit-dev/vkit.git -p 3.8.12
```
