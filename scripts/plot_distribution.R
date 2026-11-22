# Grouped distributions from a UTF-8 CSV. Usage is in references/engine-r-origin.md.
if (.Platform$OS.type == "windows" && !l10n_info()[["UTF-8"]]) invisible(Sys.setlocale("LC_CTYPE", ".UTF-8"))
script_arg <- sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[1])
script_dir <- dirname(normalizePath(gsub("~+~", " ", script_arg, fixed = TRUE)))
source(file.path(script_dir, "r_plot_common.R"), encoding = "UTF-8")
suppressPackageStartupMessages(library(ggplot2))
args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 4 || length(args) > 7) {
  stop("Usage: Rscript plot_distribution.R data.csv group value output_prefix [ylabel] [width_mm] [height_mm]")
}
source_file <- args[1]
prefix <- args[4]
ylabel <- if (length(args) >= 5) args[5] else args[3]
width_mm <- if (length(args) >= 6) as.numeric(args[6]) else 80
height_mm <- if (length(args) >= 7) as.numeric(args[7]) else 65
tbl <- read.csv(source_file, check.names = FALSE, stringsAsFactors = FALSE, colClasses = "character",
                fileEncoding = "UTF-8-BOM", na.strings = character(), fill = FALSE)
if (anyDuplicated(names(tbl)) || !all(args[2:3] %in% names(tbl))) stop("Check column names against the CSV header")
groups <- trimws(tbl[[args[2]]])
values <- suppressWarnings(as.numeric(tbl[[args[3]]]))
if (!length(groups) || any(!nzchar(groups)) || any(!is.finite(values))) {
  stop("Each row requires a group and a finite value; resolve missing or nonnumeric records explicitly")
}
categories <- unique(groups)
dat <- data.frame(group = factor(groups, levels = categories), value = values)
colors <- figure_colors(categories)

plot <- ggplot(dat, aes(x = group, y = value, fill = group)) +
  geom_boxplot(width = .49, outlier.shape = NA, linewidth = .4, colour = "#303030") +
  geom_point(shape = 21, size = 1.35, stroke = .27, colour = "#252525",
             position = position_jitter(width = .11, height = 0, seed = 113)) +
  scale_fill_manual(values = colors) +
  scale_x_discrete(expand = expansion(add = .60)) +
  labs(x = NULL, y = "Y") +
  theme_classic(base_size = 9, base_family = fonts[1]) +
  theme(legend.position = "none", axis.text.x = element_blank(),
        axis.text.y = element_text(color = "#252525"), plot.margin = margin(4, 5, 4, 4))
draw <- function() {
  grid.newpage()
  tab <- ggplotGrob(plot)
  tab$grobs[[match("ylab-l", tab$layout$name)]] <- mixed_label(ylabel, angle = 90)
  panel <- tab$layout[tab$layout$name == "panel", ]
  axis <- tab$layout[tab$layout$name == "axis-b", ]
  pos <- (seq_along(categories) - .4) / (length(categories) + .2)
  labels <- Map(function(txt, x) mixed_label(txt, x = x, pts = 8), categories, pos)
  tab <- gtable::gtable_add_rows(tab, unit(4.8, "mm"), pos = axis$b)
  tab <- gtable::gtable_add_grob(tab, grobTree(children = do.call(gList, labels)),
                                 t = axis$b + 1, l = panel$l, clip = "off")
  grid.draw(tab)
}
render_figure(prefix, width_mm, height_mm, draw)
