# R 分布图与 Origin 实验曲线

## R 分组分布

使用 `scripts/plot_distribution.R` 绘制原始样本点叠加箱线图。CSV 采用 UTF-8，每行一条观测，组别列与数值列由参数指定。分组按首次出现排序，水平抖动有固定随机种子。箱体为四分位距，横线为中位数，须延伸至距箱体不超过 1.5 倍四分位距的最远观测。每个原始观测仅显示一个点。

```powershell
Rscript --vanilla scripts/plot_distribution.R data.csv group strength out/distribution "强度 Strength (MPa)" 80 65
```

参数依次为 CSV、组别列、数值列、输出前缀，之后可选纵轴标题、宽和高（毫米）。依赖 ggplot2、gtable、systemfonts、ragg 及支持 Cairo 的 R。中文字符与全角标点用宋体（SimSun），英文、数字与单位用 Times New Roman。Cairo 生成保留文字的矢量 PDF，ragg 生成白底 600 DPI PNG。缺少字体、字段不全或数值缺失时，先修订输入或处理计划。保留首次导出的文件，重试用新的前缀。

内置六个类别色。要使用主题库或参考图的颜色，可在运行前设置 `$env:PLOT_COLORS="#427694,#B76F52"`，按分组首次出现顺序提供足量色值。适配多组和长组名时增加图宽，交付前按实际印刷尺寸核对。

## R 加权弦图

使用 `scripts/plot_chord.R` 绘制来源、去向和非负权重构成的边表。用 `directed` 表示有向流，用 `undirected` 表示无向联系。宽和高可省略，默认为 140 × 95 mm。两个 R 入口共享与脚本同目录的 `r_plot_common.R`，此入口另需 circlize。

```powershell
Rscript --vanilla scripts/plot_chord.R links.csv from to mass_kg out/material-flow directed
Rscript --vanilla scripts/plot_chord.R links.csv node_a node_b count out/interactions undirected 160 100
```

每个正权重对应一条带状连线，带宽与权重成比例。有向图使用来源节点颜色，箭头指向去向。无向图使用中性色连线。相同名称在两端表示同一节点，可同时接收与发出。若同名节点在不同阶段代表不同实体，请在输入中赋予可辨识的阶段名。平行边和自环保留。零权重行写入 `.links.csv`，标记 `drawn=FALSE`。台账保留源记录号（表头计为第 1 行）、来源、去向、原始权重文本、权重字段与方向模式，便于对照输入和图注中的单位。

节点配色顺序为正权重行中首次出现的来源节点，然后补上首次出现的去向节点，支持 `PLOT_COLORS`。所有节点标签支持同一行中英混排，中文用宋体，拉丁字符用 Times New Roman。引线将节点标签放在弧的两侧。增加图宽容纳更长的名称，增加图高容纳密集节点。输入不能含缺失或负权重。导出前逐条核对 circlize 返回的实际两端与带宽，再生成 PDF、600 DPI PNG 和权重台账。[circlize 弦图接口](https://jokergoo.github.io/circlize/reference/chordDiagramFromDataFrame.html)

## Origin 原生工程

在 Windows 上，若存在专用于此 Skill 的解释器 `$env:LOCALAPPDATA\scientific-schematic-to-ppt\origin-venv\Scripts\python.exe`，用它执行下列 Python 命令。也可使用自己的外部 Python 环境并安装 `originpro`。Rscript 不在 PATH 时，可从 Windows 注册表 `HKLM:\SOFTWARE\R-core\R` 的 InstallPath 定位 `bin/Rscript.exe`。

```powershell
python scripts/origin_curve.py data.csv out/curve.opju --x time --y load --xlabel "时间 Time (s)" --ylabel "载荷 Load (N)"
python scripts/origin_curve.py data.csv out/processed.opju --x time --y load --sg 7 2 --fit-linear
```

使用安装了 originpro 的外部 Windows Python 与可用的 Origin 许可证。脚本通过 originpro 创建独立实例。原始 X、Y 两列按源行序写入工作簿，曲线保持与工作表链接。附加输入列由原 CSV 保留。默认只绘制原始测量，`--sg WINDOW ORDER` 才调用 Origin 的 Savitzky–Golay 平滑，窗口是奇数个采样点，端点采用镜像延拓，输入 X 须等间隔递增。`--fit-linear` 在原始 XY 上执行带自由截距的等权最小二乘回归，并以各原始 X 处的预测值建立拟合曲线。SG 和拟合均写入独立派生列。

打开工程的 `Processing` 备注查看源文件名、SHA-256、源字段、行数、引擎版本、平滑窗口与阶数、回归系数及决定系数。常量响应的决定系数记为空。派生列是本次处理的数值快照；更换输入后，可用相同参数重新运行或使用 Origin 的分析对话框。图形、原始/派生数据及图例均可在 Origin 继续编辑。

Origin MCP 可用于新建独立会话时按同一顺序写工作簿、调用 `smooth` / `LinearFit`、绘制曲线、另存 OPJU，并重新打开检查。若连接器只能控制用户当前项目，请从独立外部 Python 运行上述入口。交付前核对原始数据行数和端点、每条派生曲线的列绑定、中文与拉丁字形以及图例位置。

官方参数及接口见 [Origin smooth](https://docs.originlab.com/x-function/ref/smooth/)、[Origin LinearFit](https://docs.originlab.com/originpro/classoriginpro_1_1analysis_1_1LinearFit.html) 和 [Origin 外部 Python 接口](https://docs.originlab.com/externalpython/)。
