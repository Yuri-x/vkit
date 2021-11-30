### 光度畸变接口说明

Import 示例:

```python
from vkit.augmentation.photometric_distortion import (
    PhotometricDistortion,
)
```

`PhotometricDistortion.distort_image` 接口：

```python
def distort_image(
    self,
    config_or_config_generator: Union[T_CONFIG,
                                      Callable[[Tuple[int, int], np.random.RandomState],
                                               T_CONFIG]],
    image: VImage,
    rnd: Optional[np.random.RandomState] = None,
) -> VImage:
    ...
```

其中：

* `config_or_config_generator`：传入光度畸变配置，或者传入一个生成配置的函数。每种光度畸变的操作，都有对应的独立配置类型，如 `mean_shift` 对应 `MeanShiftConfig`

* `image`：需要进行光度畸变的图片
* `rnd`：`numpy.random.RandomState` 实例，用于生成配置或者其他需要随机行为的操作

与几何畸变不同的是，光度畸变并不会改变图片中元素的位置，所以并没有对标注类型（如 `VImageMask`）的处理接口。`distort_image` 的函数名也比较明确，即光度畸变的处理对象是图片，返回被处理过的新图片

简单的可执行调用示例：

```python
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
```

可以通过 `fireball` (`pip install fireball`) 直接调用以上示例：

```bash
fib vkit_case.vkit_doc_helper.demo_pho:run \
    --image_file="REQUIRED" \
    --output_file="REQUIRED"
```

以下是示例输入与输出：

<div align="center">
    <img alt="Lenna.png" src="https://i.loli.net/2021/11/25/HFaygJjhuI2OxU1.png">
	<img alt="demo_output.png" src="https://i.loli.net/2021/11/28/LAvGD7lrkqpa2co.png">
</div>

下面是光度畸变的具体实现