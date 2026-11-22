# Weighted flows with original row provenance. See references/engine-r-origin.md.
if (.Platform$OS.type == "windows" && !l10n_info()[["UTF-8"]]) invisible(Sys.setlocale("LC_CTYPE", ".UTF-8"))
script_arg <- sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[1])
script_dir <- dirname(normalizePath(gsub("~+~", " ", script_arg, fixed = TRUE)))
source(file.path(script_dir, "r_plot_common.R"), encoding = "UTF-8")
suppressPackageStartupMessages(library(circlize))
args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 6 || length(args) > 8) {
  stop("Usage: Rscript plot_chord.R links.csv source target weight output_prefix directed|undirected [width_mm] [height_mm]")
}
width_mm <- if (length(args) >= 7) as.numeric(args[7]) else 140
height_mm <- if (length(args) >= 8) as.numeric(args[8]) else 95
direction <- match.arg(args[6], c("directed", "undirected"))
input <- read.csv(args[1], check.names = FALSE, stringsAsFactors = FALSE, colClasses = "character",
                  fileEncoding = "UTF-8-BOM", na.strings = character(), fill = FALSE)
if (anyDuplicated(names(input)) || anyDuplicated(args[2:4]) || !all(args[2:4] %in% names(input))) {
  stop("Select distinct source, target and weight fields from the CSV header")
}
edges <- data.frame(from = input[[args[2]]], to = input[[args[3]]],
                    value = suppressWarnings(as.numeric(input[[args[4]]])))
if (!nrow(edges) || any(!nzchar(trimws(edges$from))) || any(!nzchar(trimws(edges$to))) ||
    any(!is.finite(edges$value)) || any(edges$value < 0) || !any(edges$value > 0)) {
  stop("Supply named endpoints and finite nonnegative weights, including at least one positive link")
}
ledger <- data.frame(source_row = seq_len(nrow(edges)) + 1L, source = edges$from, target = edges$to,
                     weight = input[[args[4]]], weight_field = args[4], mode = direction,
                     drawn = edges$value > 0)
edges <- edges[edges$value > 0, , drop = FALSE]
nodes <- union(edges$from, edges$to)
colors <- figure_colors(nodes)

draw <- function() {
  par(mai = c(.12, .22 * width_mm / 25.4, .12, .22 * width_mm / 25.4), family = fonts[1])
  circos.clear()
  on.exit(circos.clear(), add = TRUE)
  circos.par(start.degree = 90, gap.after = rep(min(3, 35 / length(nodes)), length(nodes)))
  arc <- chordDiagram(edges, order = nodes, grid.col = colors, col = if (direction == "directed")
                        unname(colors[edges$from]) else "#8A98A4",
                      directional = as.integer(direction == "directed"), direction.type = "arrows",
                      link.arr.type = if (direction == "directed") "big.arrow" else "triangle", link.arr.length = .07, link.target.prop = FALSE,
                      transparency = .43, annotationTrack = "grid", reduce = 0, self.link = 2)
  # Check that the widths emitted by circlize match the two endpoints and
  # original weight of every positive edge, including parallel edges.
  if (!identical(as.character(arc$rn), edges$from) || !identical(as.character(arc$cn), edges$to) ||
      !isTRUE(all.equal(arc$value1, edges$value)) || !isTRUE(all.equal(arc$value2, edges$value))) {
    stop("Chord endpoint or weight verification failed")
  }

  angle <- vapply(nodes, function(node) {
    mean(c(get.cell.meta.data("cell.start.degree", node, 1), get.cell.meta.data("cell.end.degree", node, 1)))
  }, numeric(1)) * pi / 180
  x <- grconvertX(cos(angle), "user", "ndc")
  y <- grconvertY(sin(angle), "user", "ndc")
  for (side in c(-1, 1)) {
    ids <- which(if (side == 1) cos(angle) >= 0 else cos(angle) < 0)
    if (!length(ids)) next
    ids <- ids[order(y[ids])]
    gap <- 4.4 / height_mm
    yy <- y[ids]
    for (j in seq_along(yy)) yy[j] <- max(yy[j], if (j == 1) gap else yy[j-1] + gap)
    for (j in rev(seq_along(yy))) yy[j] <- min(yy[j], if (j == length(yy)) 1 - gap else yy[j+1] - gap)
    if (yy[1] < gap - 1e-6) stop("Increase output height to fit all node labels")
    near <- grconvertX(side * 1.07, "user", "ndc")
    for (j in seq_along(ids)) {
      i <- ids[j]
      label <- mixed_label(nodes[i], pts = 8.5)
      width <- attr(label, "width_mm") / width_mm
      centre <- near + side * (.9 / width_mm + width / 2)
      if (centre - width / 2 < 0 || centre + width / 2 > 1) stop("Increase output width to fit node: ", nodes[i])
      grid.lines(c(x[i], near), c(y[i], yy[j]), gp = gpar(col = colors[i], lwd = .7))
      grid.draw(mixed_label(nodes[i], x = centre, y = yy[j], pts = 8.5))
    }
  }
}
render_figure(args[5], width_mm, height_mm, draw, ledger)
