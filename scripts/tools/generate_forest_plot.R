# generate_forest_plot.R
# Updated to use meta package through adapter

library(jsonlite)

# Declare sourced functions to avoid lintr warnings
generate_forest_plot_metafor_core <- NULL

# Get script directory for sourcing
script_dir <- dirname(sys.frame(1)$ofile)
if (is.null(script_dir)) {
  # Fallback for command line execution
  args_cmd <- commandArgs(trailingOnly = FALSE)
  script_file <- args_cmd[grep("--file=", args_cmd)]
  if (length(script_file) > 0) {
    script_dir <- dirname(gsub("--file=", "", script_file))
  } else {
    script_dir <- getwd()
  }
}

source(file.path(script_dir, "../adapters", "meta_adapter.R"))
# Declare adapter functions for lintr visibility
if (FALSE) {
  generate_forest_plot_meta_core <- function(...) {}
  generate_forest_plot_metafor_core <- function(...) {}
}

generate_forest_plot <- function(args) {
  session_path <- args$session_path

  # Load analysis results
  results_path <- file.path(session_path, "results", "analysis_results.rds")
  if (!file.exists(results_path)) {
    # Try loading from processing directory (backward compatibility)
    results_path <- file.path(
      session_path,
      "processing",
      "analysis_results.rds"
    )
    if (!file.exists(results_path)) {
      stop("Analysis results not found. Please perform meta-analysis first.")
    }
    results <- readRDS(results_path)
    # Extract meta object from old format
    meta_result <- if (is.list(results) && !is.null(results$model)) {
      results$model
    } else {
      results
    }
  } else {
    meta_result <- readRDS(results_path)
  }

  # Validate that we have a meta object
  if (!inherits(meta_result, c("meta", "metabin", "metacont", "metagen"))) {
    stop("Invalid meta-analysis object. Expected meta package object.")
  }

  # Create output directory if it doesn't exist
  output_dir <- file.path(session_path, "results")
  if (!dir.exists(output_dir)) {
    dir.create(output_dir, recursive = TRUE)
  }

  # Set output file path
  output_file <- file.path(output_dir, "forest_plot.png")

  # Get parameters
  plot_style <- if (!is.null(args$plot_style)) args$plot_style else "classic"
  confidence_level <- if (!is.null(args$confidence_level)) {
    args$confidence_level
  } else {
    0.95
  }
  custom_labels <- if (!is.null(args$custom_labels)) {
    args$custom_labels
  } else {
    NULL
  }
  engine <- if (!is.null(args$engine)) {
    args$engine
  } else if (!is.null(args$plot_engine)) {
    args$plot_engine
  } else {
    "metafor"
  }

  # Generate title if not provided
  title <- "Forest Plot"
  if (!is.null(custom_labels$title)) {
    title <- custom_labels$title
  } else {
    # Create informative title based on meta-analysis type
    effect_measure <- meta_result$sm
    model_type <- if (
      !is.null(meta_result$method.random) && meta_result$method.random != ""
    ) {
      "Random Effects"
    } else {
      "Fixed Effect"
    }
    title <- paste(model_type, "Meta-Analysis -", effect_measure)
  }

  tryCatch(
    {
      # Use the selected engine
      if (tolower(engine) == "metafor") {
        plot_path <- generate_forest_plot_metafor_core(
          meta_result = meta_result,
          output_file = output_file,
          title = title,
          plot_style = plot_style,
          confidence_level = confidence_level,
          custom_labels = custom_labels
        )
      } else {
        plot_path <- generate_forest_plot_meta_core(
          meta_result = meta_result,
          output_file = output_file,
          title = title,
          plot_style = plot_style,
          confidence_level = confidence_level,
          custom_labels = custom_labels
        )
      }

      # Return success response
      list(
        status = "success",
        forest_plot_path = plot_path,
        plot_details = list(
          n_studies = meta_result$k,
          effect_measure = meta_result$sm,
          plot_style = plot_style,
          confidence_level = confidence_level,
          engine = engine
        ),
        message = "Forest plot generated successfully"
      )
    },
    error = function(e) {
      list(
        status = "error",
        message = paste("Error generating forest plot:", e$message),
        details = list(
          plot_style = plot_style,
          n_studies = if (!is.null(meta_result$k)) meta_result$k else "unknown"
        )
      )
    }
  )
}
