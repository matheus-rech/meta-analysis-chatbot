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

# Source modular implementations (relative to scripts root)
scripts_root <- normalizePath(file.path(script_dir, ".."), mustWork = FALSE)
source(file.path(scripts_root, "tools", "upload_data.R"))
source(file.path(scripts_root, "tools", "perform_analysis.R"))
source(file.path(scripts_root, "tools", "generate_forest_plot.R"))
source(file.path(scripts_root, "tools", "assess_publication_bias.R"))
source(file.path(scripts_root, "tools", "generate_report.R"))
source(file.path(scripts_root, "tools", "get_session_status.R"))
cochrane_path <- file.path(scripts_root, "adapters", "cochrane_guidance.R")
if (file.exists(cochrane_path)) {
  source(cochrane_path)
}

# Get CLI args
args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) {
  stop("Usage: mcp_tools.R <tool_name> <json_args> [session_path]")
}

tool_name <- args[1]
json_args <- fromJSON(args[2])
session_path <- if (length(args) >= 3) args[3] else getwd()

# Ensure session_path is present in args for downstream helpers
json_args$session_path <- session_path

# Helper to write JSON
respond <- function(data) {
  cat(toJSON(data, auto_unbox = TRUE, pretty = TRUE))
}

error_response <- function(message, details = NULL) {
  respond(list(status = "error", message = message, details = details))
}

# Dispatcher
result <- tryCatch({
  if (tool_name == "upload_study_data") {
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
  } else {
    list(status = "error", message = paste("Unknown tool:", tool_name))
  }
}, error = function(e) {
  list(status = "error", message = paste("R script error:", e$message))
})

respond(result)