# Python 数据图和精准标注

可直接运行此命令，在新目录中生成 PDF、600 DPI PNG、measurements.json。示例是合成数据。通常把 JSON 和项目 CSV 放在一起，更新列名、标签和目标尺寸，再运行相同入口。

```text
python scripts/plot_data.py assets/data-example.json --out work/example-01
```

## 数据与样式

- `data` 是相对规格的 UTF-8 CSV 路径。工作簿输入先审阅表头、合并单元格、公式缓存、单位和分组，再把所用工作表/列导出成可追溯 CSV；源表保留在项目。空值、NA、NaN 保留为断点，数字零是有效数据。
- `width_mm`、`height_mm` 是最终物理尺寸。`columns` 指定面板列数。按原图锁定布局时，对所有面板给出 `axes_box: [left,bottom,width,height]`，单位是整页归一化坐标，原点位于左下。可指定 `xticks/yticks`、`xlim/ylim`、`xscale/yscale`、`legend`（布尔或 Matplotlib 图例参数）。固定图层尺寸后，优先调整边距和锚点以消除裁切。
- 每个系列填 `id, x, y`，可设置 `kind: line/scatter`、`label, color, marker, linestyle, line_pt, marker_pt`。将已选角色色写入每个系列的 `color`。同一颜色类别在组合图中使用相同图例关键词。用线型、点型补充对比。模板保留采样顺序。往/返加载段须按实验记录说明。
- `yerr` 指向已知误差幅度列，`error_definition` 描述来源和统计量，误差幅度须非负。对重复试验先按真正独立的样本计算 SD/SEM/CI，保留分组、n、公式与置信水平。非对称误差改用 Matplotlib 的 (2,N) 误差数组。显著性、多重比较仅使用对应检验结果。
- Matplotlib 3.6+ 支持单段文本的多字体回退。模板查找两种字体，使用 TrueType PDF 字体类型 42；有中文的结果需再次核实 PDF 的字体清单和实际可选择文字。指定期刊字体可用 `font_latin/font_cjk`。拉丁数学可写 `$F$`，轴题示例为“载荷 $F$ (N)”。中文留在数学环境外。

## 独立标注层

本机已在 Matplotlib 3.9.4、3.10.9 和 3.11.2 验证中文、拉丁字母与行内公式的 PDF 输出。升级绘图库后，可用 `python -m unittest discover -s tests`（完整源码包）复查字形、数值和放大图。

在各面板的 `annotations` 列表中放入条目；`scripts/precision_annotations.py` 独立计算落点、生成图元并尝试避让。调用示例如下。

| kind | 核心字段/计算 |
| --- | --- |
| `peak` / `minimum` | `series`。在有限观测上取全局极值；并列峰需给采集顺序下的 `occurrence`（从 1 开始）。局部峰应先声明分析区间并提取该段。 |
| `threshold` | `series, value`。在相邻有效样本间按原始单位线性插值。平台取首次命中；多次穿越需给 `occurrence`。散点要求明确 `interpolate: true`。对数坐标仍按原始单位插值；模板在显示时细分线段，使该物理模型的阈值落到曲线上。采用其他模型时另行实现并记录。 |
| `inflection` | `series`。仅用于连续、严格递增 x 的序列，至少五点。用相邻割线估计二阶导数，对变号位置插值；连续零段取中点。噪声会造成伪拐点，先选定有物理依据的平滑或分析区间。 |
| `interval` / `span` | `bounds: [start,end]`。前者加阴影；后者还需数据坐标 `y` 和 `label`，画双箭头。阶段名称与边界来自实验记录。 |
| `reference` | `axis: x/y, value`。画同单位参考虚线。 |
| `inset` | `box: [left,bottom,width,height]`（面板内比例）、`xlim, ylim`、可选 `series: ["id"]`。重复绘制同一原始曲线及点型，并将放大框与父图连接。局部坐标继承母图的线性或对数轴，配套误差棒复用母图同一误差列。 |
| `linear_fit` | `series`，可选 `bounds`。对所选有限观测做带截距的非加权最小二乘，打印方程和同样本的 R²，记录 n 和区间。权重、非线性或分段模型要在专用脚本或 Origin 中声明并验证。 |
| `significance` | `bounds, y, p, test, source`。标注已计算的组间检验及其来源；需要星号时把阈值写进图注。 |

点标注自定义文字接受 `{x:.3g}` 与 `{y:.3g}`。生成后核对 measurements.json 的源文件哈希、缺失数、区间及每个标签的 xy。`review_overlap` 和 `review_clipping` 标识自动检查发现的冲突；调整后重新导出。自动避让检查文字与折线、标签及放大框，最后在实际输出中逐项查看箭头、连接线、误差棒端帽、图例和点型。使用显式坐标和不同工具时，一律保留标注的原始数据坐标，并以一次独立重算验证科学数值。
