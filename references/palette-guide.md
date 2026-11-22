# 科研示意图配色

打开[主题配色色卡 PDF](../docs/palette-atlas.pdf)可按主题查看每个对象的颜色和 HEX，再用下方 ID 生成项目配色。

配色先跟着图中对象走。先找读者需要辨认的两三种东西，例如岩样、注入的水和滑移面，再给它们分配固定的角色色。同一个对象在剖面、装置图和放大窗中沿用同一色。具体的中文字体、英文数字字体和绘图引擎由本 Skill 的主流程确定。

## 原图、配方与证据

当用户要求复绘时，优先采用其明确给出的 HEX，或在图片原尺寸下选择每个对象内部的平坦色块。避免箭头边缘、抗锯齿轮廓、半透明叠合处和照片反光。优先级从高到低为用户按角色指定的颜色、参考图中按角色采到的像素、用户点名的配方、按主题匹配的配方。仅有参考图片、没有对象采样点时，选择器输出实测可见色和待核对状态；整图色频无法给出对象身份。

在原创图中，先确定分类、顺序和连续量的差别。下表配方提供分类用色。表示温度、浓度、应力大小等连续量时，采用与数据范围一致的连续色标，写明单位和端点。数据图有既定图例时，示意图中的同名组分与之对齐。有物理含义的约定（如实际光波长、晶体学配色或地层标准色）由该图的约定决定。

| 配方 ID | 图中主要对象 |
|---|---|
| rock-fracture | 岩体、裂隙面、孔隙水、注水方向 |
| mass-transport | 流动方向、溶质、渗流与扩散边界 |
| acid-corrosion | 基体、溶液、反应前沿、产物或保护层 |
| mechanical-loading | 试样、支座、力与位移 |
| microfluidics | 芯片基底、微通道、样品、缓冲液与检测位点 |
| layered-device | 传感器或晶体管中的衬底、活性层、电极与介电层 |
| optical-path | 光学元件、主光束、次级光路、衬底 |
| energy-interface | 光伏或电池的功能层及界面 |
| polymer-network | 水相、聚合物链、交联点 |
| cell-populations | 组织中的细胞类型与基质 |
| molecular-complex | 蛋白亚基、复合体与结合位点 |
| geological-section | 地层、板片、沉积与深部背景 |
| research-workflow | 研究或计算流程中的输入、处理、输出和判断 |

## 使用选择器

在 Skill 目录运行以下命令。默认输出 UTF-8 JSON，指定 `--out palette.json` 可直接保存到项目。

```text
python scripts/choose_palette.py --list
python scripts/choose_palette.py --theme "岩石裂隙中的孔隙水"
python scripts/choose_palette.py --theme "mass transfer in porous media"
python scripts/choose_palette.py --palette acid-corrosion --reference-colors "solution=#A0CFDA" "front=#AB513C"
python scripts/choose_palette.py --palette rock-fracture --reference-image reference.png --sample rock=0.28,0.42 fluid=0.63,0.31
python scripts/choose_palette.py --reference-image reference.png
```

坐标以图片左上角为原点，取值为 0–1。透明像素在白色画布上合成，带 EXIF 方向的照片按其显示方向采样。返回的 `roles` 是绘图使用的 HEX，`role_origin` 标明每个角色的来源。图上的文字可读取 `label_colors`，它按不透明纯色底返回相对亮度对比更高的黑色或白色。透明、渐变、叠色、细线和外置图例须在最终尺寸渲染后复查。相邻对象另用形状、符号、线型或纹理区分，特别是颜色接近或黑白打印时。

灰度核对结果见 `grayscale_check`。选择器对除正文和画布外的每一对角色，用线性 sRGB 相对亮度 Y 计算对比度 (Y亮 + 0.05) / (Y暗 + 0.05)，在未舍入数值低于 1.5 时列入 `close_pairs`。1.5 是本库用于提醒复查的经验阈值。重点核对相邻、叠放或在同一图例中比较的角色，并按 `suggestion` 增加线型、边界或纹理。算法保留每个角色的原 HEX。该项只检测亮度接近，彩色视觉缺陷模拟和实物灰阶打样需要另外进行。

关键词按独立匹配数排序，子串同义词只计一次。一个词句同时命中几个相同分数的主题时，`candidates` 给出匹配词，`status` 为 `needs_review`。例如，机械加载和酸蚀同时出现且分属两个子图，分别指定 `mechanical-loading` 与 `acid-corrosion`，并让跨图重复出现的同一岩样沿用其颜色。全无关键词命中时，只提供中性文字和底色。明确的角色色可独立使用；只锁定其中一部分时，核对其余角色是否仍需补全。

## 取样范围

本版含 66 篇原始研究、15 种期刊、69 个取色区域。按主题关键词和可公开读取的学术图例进行有目的抽样。清单另列 1 篇方法综述和 1 篇研究综述。每篇入选论文附有出版方或 Europe PMC 的文献类型核验来源。主题色卡是面向对象角色、浅色画布和标签可读性调整过的设计方案。期刊没有为这些主题指定统一配色。

每篇记录给出 DOI、期刊、原图页、原图地址、图号、尺寸、取样矩形与测得的 HEX。矩形均从原图左上角归一化到 0–1。不同取样方法的频率分母分别记录，跨方法不能直接相加。两篇岩石研究按对象核对平坦色块，记录色块原始像素众数与所占比例；其他面板在目视定位后去除中性色、对取样像素分箱，记录填色近似值。颜色出处可在 [取色证据清单](palette-evidence.json) 核对，角色组合和用色依据见 [主题配方](palettes.json)。

需要补充新主题时，在线查看原始研究中的具体图号与图注，辨认示意区域，再记录取样框、方法和链接。只保存结构化颜色及溯源元数据；论文及图像留在线上。判断新配方是否合用时，按角色连续性、最终尺寸下的可读性与黑白下的可区分性检查实际图稿。
