---
slug: /
---

# 总览

## 项目简介

[vkit](https://github.com/vkit-dev/vkit) 是一个面向计算机视觉（特别是文档图像分析与识别方向）开发者的工具包，特性如下：

* 丰富的数据增强策略支持
  * 支持常见的光度畸变策略，如各类色彩空间操作、各类噪音操作
  * ⭐ 支持常见的几何畸变策略，如各类仿射变换、各类非线性变换（如 Similarity MLS，基于相机模型的 3D 曲面、翻折效果等）
  * ⭐ 支持在几何畸变过程中，图片与各种标注数据类型的一致变换。例如，在旋转图片的同时，vkit 也可以同时旋转关联标注的位置信息
* 较为全面的数据类型封装与可视化支持
  * 图片类型（基于 PIL 的封装，支持各类图片的读写）
  * 标注类型：蒙板（mask）、评分图（score map）、框（box）、多边形（polygon） 等
* 工业级代码质量
  * 友好的代码自动补全与类型检查支持，为开发体验保驾护航
  * 成熟的包管理与依赖管理机制
  * 自动化风格检查（基于 flake8）与静态类型分析（基于 pyright）

注：

* 🚧 表示施工中，未完全支持
* ⭐ 表示本项目的亮点（其他项目没有，或是做得不够好的地方）

## 项目愿景

作者作为一名 CV/NLP 算法工程师，希望可以通过 vkit 这个项目，从以下几个方面给大家提供便利：

* 将开发者从繁琐的数据治理的细节中解放出来，将宝贵的时间放在更有价值的工作上，如数据治理策略、算法模型设计与调优等
* 整合常见的数据增强策略，助力文档图像分析与识别方向的科研工作、构建工业级场景数据方案（即工业界算法落地所需的那点 "secret sauce"）
* 构建工业级开源文档图像分析与识别解决方案（如扭曲复原、超分辨率、OCR、版面分析等）

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

* 0.2.0
  - [ ] 使用文档（英文）
  - [ ] 完整 CI 测试流程
  - [ ] 支持字体渲染
  - [ ] 支持 OCR 文字检测（text detection）训练数据生成
  - [ ] 支持 OCR 文字识别（text recognition）训练数据生成

## 已发布稳定版本

* 0.1.0
  - 支持 Python 3.9
  - 支持 Python 3.8
  - 图片类型封装
  - 标注类型封装
  - 常见的光度畸变
  - 常见的几何畸变
  - 使用文档


## 沟通途径

* 使用疑问、需求讨论等请移步 [Discussions](https://github.com/vkit-dev/vkit/discussions)
* 报 Bug 请移步 [Issues](https://github.com/vkit-dev/vkit/issues)

作者平日工作繁忙，只能在业余支持本项目，或有响应不及时的情况，请多多担待

## 赞助

赞助体系正在规划中，会在项目成长到一定阶段后推出

就目前而言，如果您觉得本项目对您产生了实质性的帮助，可以考虑请我喝杯咖啡，交个朋友😄

<div align="center">
    <img alt="爱发电.jpg" width="400" src="https://i.loli.net/2021/11/28/xkQ3DFws9W1fBg4.jpg" />
</div>
<div align="center">
    <a href="https://afdian.net/@huntzhan?tab=home">也可以点此传送至爱发电</a>
</div>
