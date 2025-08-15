#!/usr/bin/env Rscript

# Meta-Analysis MCP Tools - Adapter-based dispatcher

suppressPackageStartupMessages({
  library(jsonlite)
})

# Discover script directory for sourcing helpers
get_script_dir <- function() {
  d <- tryCatch(dirname(sys.frame(1)$ofile), error = function(e) NULL)
  if (is.null(d)) {
    args_cmd <- commandArgs(trailingOnly = FALSE)
    script_file <- args_cmd[grep("--file=", args_cmd)]
    if (length(script_file) > 0) {
      d <- dirname(gsub("--file=", "", script_file))
    } else {
      d <- getwd()
    }
  }
  return(d)
}

script_dir <- get_script_dir()

# Get CLI args
args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) {
  stop("Usage: mcp_tools.R <tool_name> <json_args_or_file> [session_path]")
}

tool_name <- args[1]
# Allow passing a file path for large JSON payloads
json_input <- args[2]
if (file.exists(json_input)) {
  json_text <- tryCatch(paste(readLines(json_input, warn = FALSE), collapse = "\n"), error = function(e) NULL)
  if (is.null(json_text)) stop("Failed to read JSON args file: ", json_input)
  json_args <- fromJSON(json_text)
} else {
  json_args <- fromJSON(json_input)
}
session_path <- if (length(args) >= 3) args[3] else getwd()

# Ensure session_path is present in args for downstream helpers
json_args$session_path <- session_path

# Source modular implementations (relative to scripts root)
scripts_root <- normalizePath(file.path(script_dir, ".."), mustWork = FALSE)

# Conditionally source scripts based on tool being called
# This prevents loading all packages when we just need health check
if (tool_name != "health_check") {
  source(file.path(scripts_root, "tools", "upload_data.R"))
  source(file.path(scripts_root, "tools", "perform_analysis.R"))
  source(file.path(scripts_root, "tools", "generate_forest_plot.R"))
  source(file.path(scripts_root, "tools", "assess_publication_bias.R"))
  source(file.path(scripts_root, "tools", "generate_report.R"))
  source(file.path(scripts_root, "tools", "get_session_status.R"))
  source(file.path(scripts_root, "tools", "execute_r_code.R"))
  cochrane_path <- file.path(scripts_root, "adapters", "cochrane_guidance.R")
  if (file.exists(cochrane_path)) {
    source(cochrane_path)
  }
}

# Always source health check (it's self-contained)
source(file.path(scripts_root, "tools", "health_check.R"))

# Helper to write JSON
respond <- function(data) {
  cat(toJSON(data, auto_unbox = TRUE, pretty = TRUE))
}

error_response <- function(message, details = NULL) {
  respond(list(status = "error", message = message, details = details))
}

# Initialization tool (creates session.json and folders)
initialize_meta_analysis <- function(args) {
  session_path <- args$session_path
  if (!dir.exists(session_path)) dir.create(session_path, recursive = TRUE)
  for (d in c("data", "processing", "results", "input", "tmp")) {
    dir.create(file.path(session_path, d), showWarnings = FALSE, recursive = TRUE)
  }
  sess_id <- if (!is.null(args$session_id)) args$session_id else basename(session_path)
  # Normalize fields from either snake_case or camelCase
  study_type <- if (!is.null(args$study_type)) args$study_type else if (!is.null(args$studyType)) args$studyType else "clinical_trial"
  effect_measure <- if (!is.null(args$effect_measure)) args$effect_measure else if (!is.null(args$effectMeasure)) args$effectMeasure else "OR"
  analysis_model <- if (!is.null(args$analysis_model)) args$analysis_model else if (!is.null(args$analysisModel)) args$analysisModel else "random"
  name <- if (!is.null(args$name)) args$name else "Meta-Analysis Project"
  cfg <- list(
    name = name,
    studyType = study_type,
    effectMeasure = effect_measure,
    analysisModel = analysis_model,
    createdAt = as.character(Sys.time())
  )
  writeLines(toJSON(cfg, auto_unbox = TRUE, pretty = TRUE), file.path(session_path, "session.json"))
  list(status = "success", session_id = sess_id, session_path = session_path, config = cfg)
}

# Health check implementation
# Now using the dedicated health_check.R script

# Dispatcher
result <- tryCatch({
  if (tool_name == "health_check") {
    health_check(json_args)
  } else if (tool_name == "initialize_meta_analysis") {
    initialize_meta_analysis(json_args)
  } else if (tool_name == "upload_study_data") {
    # Base64-aware, size-guarded upload + processing
    upload_study_data(json_args)
  } else if (tool_name == "perform_meta_analysis") {
    res <- perform_meta_analysis(json_args)
    # Optionally enhance with Cochrane recommendations
    if (exists("add_cochrane_recommendations") && is.list(res) && res$status == "success") {
      res <- add_cochrane_recommendations(res, analysis_type = "meta_analysis")
    }
    res
  } else if (tool_name == "generate_forest_plot") {
    res <- generate_forest_plot(json_args)
    if (exists("add_cochrane_recommendations") && is.list(res) && res$status == "success") {
      res <- add_cochrane_recommendations(res, analysis_type = "forest_plot")
    }
    res
  } else if (tool_name == "assess_publication_bias") {
    res <- assess_publication_bias(json_args)
    if (exists("add_cochrane_recommendations") && is.list(res) && res$status == "success") {
      res <- add_cochrane_recommendations(res, analysis_type = "publication_bias")
    }
    res
  } else if (tool_name == "generate_report") {
    # R Markdown report using template
    generate_report(json_args)
  } else if (tool_name == "get_session_status") {
    get_session_status(json_args)
  } else if (tool_name == "execute_r_code") {
    execute_r_code(json_args)
  } else {
    list(status = "error", message = paste("Unknown tool:", tool_name))
  }
}, error = function(e) {
  list(status = "error", message = paste("R script error:", e$message))
})

respond(result)