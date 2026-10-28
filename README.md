# Scientific Schematic to PPT

**从研究材料到逐元素可编辑的学术示意图 PPT。**

[English](README.en.md) · [Skill](SKILL.md) · [案例展示](docs/gallery.md) · [社区案例](docs/community-gallery.md) · [下载安装](https://github.com/dxlian/Scientific-Schematic-to-PPT/releases/latest) · [风格规范](references/style-guide.md)

我把阅读材料、设计示意图和制作原生 PowerPoint 整理成了这个 skill：先理解科学内容，完成整图设计并审阅图片预览，再将确认的图逐元素重建为 `.pptx`。拿到文件后，可以直接在 PPT 中修改标注、调整结构、移动部件和统一配色，不必为每次局部修改重新生成整张图片。

我的目标是让图既讲清楚科学内容，也便于后续修改。**简洁的是视觉语言，不是把必要的结构和细节删掉。**

## 原生可编辑 PPT

我把可编辑性作为交付的一部分：文字、几何图形、曲线和箭头各自成为 PowerPoint 对象，相关部件按结构分组，保留预览中的布局和必要细节。

| 图中元素 | 在 PPT 中可以继续修改 |
| --- | --- |
| 文字与标注 | 内容、字体、字号、颜色、对齐和位置 |
| 箭头与连线 | 端点位置、方向、线宽、颜色和虚实线 |
| 曲线与不规则边界 | 形状顶点、轮廓、填充和层叠顺序 |
| 装置部件与材料区域 | 单独选择、移动、缩放、复制和重新配色 |
| 结构分组 | 整体移动，或取消组合后修改局部并重新组合 |
| 场景文件 | 保留元素坐标、样式和层级，供后续程序化修改与重新构建 |

**交付包括原生 `.pptx`、PPT 实际渲染的预览图，以及用于构建的场景 JSON。** 十二个展示案例都提供独立 PPT，也可一次下载合集。

[下载十二图 PPT 合集](examples/engineering-gallery.pptx) · [查看单张可编辑案例](docs/gallery.md)

这套流程是审阅后的逐元素重建，不是无条件的一键图片矢量化。真实照片和实测图保持原始图像，并明确其可编辑范围；移动部件后，定位式连线可能需要手动调整。原生重建完成后仍需检查实际渲染中的文字、连接关系和布局。

## 图例

### 十二个工科方向

![十二个工科论文图例](docs/images/engineering-gallery.png)

我选取了 Nature、Nature Energy、Nature Biomedical Engineering、Nature Communications 和 Science Advances 的研究，覆盖热管理、机器人、化工、光学、储能、生物工程、声学和建筑材料。每个案例围绕一个清楚的问题展开，避免把所有内容都画成相同的流程图。

[下载十二图可编辑 PPT 合集](examples/engineering-gallery.pptx) · [查看单张 PPT、场景文件与论文来源](docs/gallery.md)

这十二个案例均已逐元素重建。展示图来自 PPT 的实际渲染，文字、箭头、曲线、材料区域和装置部件均可编辑；每个案例也保留独立的 PPT 文件，便于直接修改和复用。

### 算法与信息流

![多头自注意力示意图预览](docs/images/attention-preview.png)

依据 *Attention Is All You Need* 的方法独立设计，展开投影、单头计算与多头合并。矩阵网格仅表示结构，不表示实测数值。这一图例展示的是设计预览，尚不是可编辑 PPT。

方法来源：[Vaswani et al., 2017](https://arxiv.org/abs/1706.03762)。图例采用独立布局，未使用论文原图。

## 分享你的案例

也欢迎把你用这个 skill 绘制的学术示意图分享出来。提交预览图、可编辑 PPT 的公开链接，以及简短的用途和绘制说明；我会在核对来源、授权和文件后，将合适的作品收录到社区展示页，并保留作者署名。

[提交我的案例](https://github.com/dxlian/Scientific-Schematic-to-PPT/issues/new?template=share-your-figure.yml) · [社区展示与提交说明](docs/community-gallery.md)

请只上传可以公开分享的内容。社区作品保留作者声明的许可，不自动改为本仓库的 MIT 许可。

## 我希望保留的风格

- 白底、细线、克制配色，信息层级清楚。
- 完整表达对象、结构、连接关系和必要的局部细节。
- 根据内容选择剖面、装置、并列状态、分层架构或机制示意，不固定套用一种布局。
- 默认英文标注和 Times New Roman，按实际使用尺寸安排字号。
- 在 PPT 中保留曲线、部件和文字的可编辑性，不把整图当作背景图片。
- 颜色和箭头都有明确含义，不用装饰代替科学解释。

## 使用流程

**输入材料 → 解读内容 → 整体设计 → 预览审阅 → 确认版本 → 可编辑 PPT**

可以输入文字指令、论文、实验方案或参考图片。先确定图要回答的问题，以及哪些关系需要画出来，再生成图片预览。调整到满意后，明确确认当前版本，才开始制作 PPT。

重建时，以确认过的图为准，保留其布局、结构、连接和细节。最后核对实际渲染结果，避免转换后出现错位、漏画或过度简化。

## 适用场景

研究背景、实验装置、方法流程、作用机制、材料结构、生物过程、算法架构，以及其他需要以示意图表达学术内容的场景。

对于实测曲线、显微照片或数据图，应使用真实来源，不用生成图替代实验结果。

## 安装

从 [Releases](https://github.com/dxlian/Scientific-Schematic-to-PPT/releases/latest) 下载名称含 `-skill-` 的轻量安装包；完整包还包含案例 PPT、场景文件和展示图。

解压后，将 `scientific-schematic-to-ppt` 文件夹放入本地 skills 目录：

```text
Windows: %USERPROFILE%\.codex\skills\scientific-schematic-to-ppt
macOS/Linux: ~/.codex/skills/scientific-schematic-to-ppt
```

设置过 `CODEX_HOME` 时，使用该目录下的 `skills`。确认路径为 `skills/scientific-schematic-to-ppt/SKILL.md`，然后重新打开会话。

也可以先克隆完整仓库，再将文件夹放入上述目录：

```bash
git clone https://github.com/dxlian/Scientific-Schematic-to-PPT.git scientific-schematic-to-ppt
```

## 开始绘图

```text
使用 $scientific-schematic-to-ppt 阅读我上传的论文，
围绕研究对象、关键结构和作用过程设计一张学术示意图。
风格简洁，但内容要完整，保留必要的局部细节。
英文标注，Times New Roman。
先给我图片审阅，确认后再制作原生可编辑 PPT。
```

已有参考图时：

```text
使用 $scientific-schematic-to-ppt，参考这张图的视觉风格，
根据我的研究内容重新设计，不复制它的布局。
先确认图中的对象和连接关系，再给我预览。
```

可同时指定图宽、单栏或双栏、配色、语言和期刊要求。

## 运行环境

需要支持读取文件和生成图片的助手，以及 Python 3.10+。原生 PPT 构建工具使用 Python 标准库；PDF 提取和图像对照使用可选依赖：

```bash
python -m pip install -r requirements-optional.txt
```

PPT 最终显示效果需通过 PowerPoint、WPS 或其他可用演示软件核对。真实照片和数据图仍按图片保留，其可编辑范围与原生示意图不同。

## 许可证

代码、原创文档和原创图例采用 [MIT License](LICENSE)。外部论文、图片、字体及软件遵循各自许可；可选依赖 PyMuPDF、Pillow 和演示软件不随本项目打包。案例用于解释论文中的科学内容，不代表论文作者或期刊的官方配图或背书。
