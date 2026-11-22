if (.Platform$OS.type == "windows" && !l10n_info()[["UTF-8"]]) {
  invisible(Sys.setlocale("LC_CTYPE", ".UTF-8"))
}
library(grid)
fonts <- c("Times New Roman", "SimSun")
if (!capabilities("cairo")) stop("A Cairo-enabled R installation is required for text PDF output")
available <- systemfonts::system_fonts()$family
if (!all(fonts %in% available)) stop("Install the missing font: ", paste(setdiff(fonts, available), collapse = ", "))

figure_colors <- function(categories) {
  colors <- c("#427694", "#B76F52", "#669789", "#9B80AA", "#C6A24E", "#698CB5")
  custom <- Sys.getenv("PLOT_COLORS")
  if (nzchar(custom)) colors <- trimws(strsplit(custom, ",", fixed = TRUE)[[1]])
  if (length(categories) > length(colors) || !all(grepl("^#[0-9A-Fa-f]{6}$", colors))) {
    stop("Set PLOT_COLORS to sufficient comma-separated #RRGGBB colors in category order")
  }
  setNames(colors[seq_along(categories)], categories)
}

# Measure typed runs on the active device and center them as a group. This keeps
# Latin text and Chinese glyphs individually searchable in the vector PDF.
mixed_label <- function(label, x = .5, y = .5, angle = 0, pts = 9) {
  cjk <- "[\\p{Han}\\x{3000}-\\x{303F}\\x{FF01}-\\x{FF60}]"
  chars <- strsplit(enc2utf8(label), "", fixed = TRUE)[[1]]
  if (!length(chars)) return(nullGrob())
  flags <- grepl(cjk, chars, perl = TRUE)
  segments <- rle(flags)
  ends <- cumsum(segments$lengths)
  starts <- ends - segments$lengths + 1L
  pieces <- Map(function(lo, hi, cn) {
    textGrob(paste(chars[lo:hi], collapse = ""), just = "left",
             gp = gpar(fontfamily = fonts[if (cn) 2 else 1], fontsize = pts, col = "#252525"))
  }, starts, ends, segments$values)
  lengths <- vapply(pieces, function(g) convertWidth(grobWidth(g), "mm", valueOnly = TRUE), numeric(1))
  offsets <- c(0, head(cumsum(lengths), -1)) - sum(lengths) / 2
  for (i in seq_along(pieces)) pieces[[i]]$x <- unit(.5, "npc") + unit(offsets[i], "mm")
  result <- grobTree(children = do.call(gList, pieces), vp = viewport(x = x, y = y, angle = angle))
  attr(result, "width_mm") <- sum(lengths)
  result
}

render_figure <- function(prefix, width_mm, height_mm, draw, links = NULL) {
  if (any(!is.finite(c(width_mm, height_mm))) || min(width_mm, height_mm) <= 0) stop("Invalid dimensions")
  extensions <- c(".pdf", ".png", if (!is.null(links)) ".links.csv")
  out <- paste0(prefix, extensions)
  if (any(file.exists(out))) stop("Choose a fresh output prefix")
  dir.create(dirname(prefix), recursive = TRUE, showWarnings = FALSE)
  temps <- vapply(extensions, function(ext) tempfile(tmpdir = dirname(prefix), fileext = ext), character(1))
  on.exit(unlink(temps), add = TRUE)
  cairo_pdf(temps[1], width_mm / 25.4, height_mm / 25.4, family = fonts[1], bg = "white")
  tryCatch(draw(), finally = dev.off())
  ragg::agg_png(temps[2], width = width_mm, height = height_mm, units = "mm", res = 600, background = "white")
  tryCatch(draw(), finally = dev.off())
  if (!is.null(links)) write.csv(links, temps[3], row.names = FALSE, fileEncoding = "UTF-8")
  if (any(file.info(temps)$size <= 0)) stop("An export is empty")
  for (i in seq_along(out)) {
    if (!file.rename(temps[i], out[i])) {
      unlink(out[seq_len(i - 1L)])
      stop("Could not publish ", out[i])
    }
  }
}
