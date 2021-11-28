简体中文 | [English](README_EN.md)

[TOC]

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

```vkit-doc
[[ref]]
path = "../vkit/augmentation/README/README.md"
```

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
