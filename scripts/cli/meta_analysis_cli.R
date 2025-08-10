#!/usr/bin/env Rscript

# Meta-Analysis CLI Script
# This provides command-line interface for meta-analysis without MCP
# Based on the original meta_analysis.R but integrated with our adapter

# Set library path
.libPaths(c("~/R/library", .libPaths()))

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

# Source the adapter
source(file.path(script_dir, "meta_adapter.R"))

# CLI-specific wrapper functions
perform_meta_analysis_cli <- function(data_file, output_dir, method = "random", measure = "OR") {
  
  # Read data directly from CSV
  data <- read.csv(data_file)
  
  # Validate required columns
  required_cols <- c("study_id", "effect_size", "se")
  if (!all(required_cols %in% colnames(data))) {
    stop(paste("Missing required columns:", paste(setdiff(required_cols, colnames(data)), collapse = ", ")))
  }
  
  # Use the core function
  meta_result <- perform_meta_analysis_core(data, method, measure)
  
  # Extract results based on method
  if (method == "random") {
    pooled_effect <- meta_result$TE.random
    se_pooled <- meta_result$seTE.random
    ci_lower <- meta_result$lower.random
    ci_upper <- meta_result$upper.random
    p_value <- meta_result$pval.random
  } else {
    pooled_effect <- meta_result$TE.fixed
    se_pooled <- meta_result$seTE.fixed
    ci_lower <- meta_result$lower.fixed
    ci_upper <- meta_result$upper.fixed
    p_value <- meta_result$pval.fixed
  }
  
  # Create results list
  results <- list(
    pooled_effect = if(measure == "OR") exp(pooled_effect) else pooled_effect,
    pooled_effect_log = pooled_effect,
    se_pooled = se_pooled,
    confidence_interval = paste0("[", 
                                round(if(measure == "OR") exp(ci_lower) else ci_lower, 3), 
                                ", ", 
                                round(if(measure == "OR") exp(ci_upper) else ci_upper, 3), 
                                "]"),
    p_value = p_value,
    heterogeneity_tau2 = meta_result$tau2,
    heterogeneity_i2 = paste0(round(meta_result$I2 * 100, 1), "%"),
    heterogeneity_q = meta_result$Q,
    heterogeneity_p = meta_result$pval.Q,
    n_studies = meta_result$k
  )
  
  # Save results
  results_file <- file.path(output_dir, "meta_analysis_results.json")
  writeLines(jsonlite::toJSON(results, pretty = TRUE), results_file)
  
  # Save R object for plotting
  rds_file <- file.path(output_dir, "meta_analysis_object.rds")
  saveRDS(meta_result, rds_file)
  
  return(results)
}

# Forest plot wrapper
generate_forest_plot_cli <- function(meta_object_file, output_file, title = "Forest Plot") {
  
  # Load meta-analysis object
  meta_result <- readRDS(meta_object_file)
  
  # Use core function with classic style and predefined colors
  generate_forest_plot_core(
    meta_result = meta_result,
    output_file = output_file,
    title = title,
    plot_style = "classic"
  )
  
  return(output_file)
}

# Funnel plot wrapper
generate_funnel_plot_cli <- function(meta_object_file, output_file, title = "Funnel Plot") {
  
  # Load meta-analysis object
  meta_result <- readRDS(meta_object_file)
  
  # Use core function
  generate_funnel_plot_core(
    meta_result = meta_result,
    output_file = output_file,
    title = title
  )
  
  return(output_file)
}

# Publication bias wrapper
assess_publication_bias_cli <- function(meta_object_file, output_dir) {
  
  # Load meta-analysis object
  meta_result <- readRDS(meta_object_file)
  
  # Use core function
  bias_results <- assess_publication_bias_core(meta_result)
  
  # Save results
  bias_file <- file.path(output_dir, "publication_bias_results.json")
  writeLines(jsonlite::toJSON(bias_results, pretty = TRUE), bias_file)
  
  return(bias_results)
}

# Command line interface
if (!interactive()) {
  args <- commandArgs(trailingOnly = TRUE)
  
  if (length(args) < 3) {
    cat("Meta-Analysis Command Line Tool\n")
    cat("===============================\n\n")
    cat("Usage: Rscript meta_analysis_cli.R <command> <data_file> <output_dir> [additional_args]\n\n")
    cat("Commands:\n")
    cat("  analyze - Perform meta-analysis\n")
    cat("           Args: [method: fixed/random] [measure: OR/RR/MD/SMD/HR]\n")
    cat("  forest  - Generate forest plot\n")
    cat("           Args: [title]\n")
    cat("  funnel  - Generate funnel plot\n")
    cat("           Args: [title]\n")
    cat("  bias    - Assess publication bias\n\n")
    cat("Examples:\n")
    cat("  Rscript meta_analysis_cli.R analyze data.csv results/\n")
    cat("  Rscript meta_analysis_cli.R analyze data.csv results/ random OR\n")
    cat("  Rscript meta_analysis_cli.R forest data.csv results/ \"My Forest Plot\"\n")
    cat("  Rscript meta_analysis_cli.R bias data.csv results/\n")
    quit(status = 1)
  }
  
  command <- args[1]
  data_file <- args[2]
  output_dir <- args[3]
  
  # Create output directory if it doesn't exist
  dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
  
  tryCatch({
    if (command == "analyze") {
      method <- if (length(args) > 3) args[4] else "random"
      measure <- if (length(args) > 4) args[5] else "OR"
      
      cat("Performing meta-analysis...\n")
      cat("  Method:", method, "\n")
      cat("  Measure:", measure, "\n")
      
      results <- perform_meta_analysis_cli(data_file, output_dir, method, measure)
      
      cat("\nResults:\n")
      cat("  Pooled effect:", results$pooled_effect, "\n")
      cat("  95% CI:", results$confidence_interval, "\n")
      cat("  P-value:", format.pval(results$p_value), "\n")
      cat("  Heterogeneity I²:", results$heterogeneity_i2, "\n")
      cat("  Number of studies:", results$n_studies, "\n")
      cat("\nMeta-analysis completed successfully\n")
      cat("Results saved to:", file.path(output_dir, "meta_analysis_results.json"), "\n")
      
    } else if (command == "forest") {
      meta_object_file <- file.path(output_dir, "meta_analysis_object.rds")
      
      if (!file.exists(meta_object_file)) {
        stop("Meta-analysis object not found. Run 'analyze' command first.")
      }
      
      output_file <- file.path(output_dir, "forest_plot.png")
      title <- if (length(args) > 3) args[4] else "Forest Plot"
      
      cat("Generating forest plot...\n")
      generate_forest_plot_cli(meta_object_file, output_file, title)
      cat("Forest plot saved to:", output_file, "\n")
      
    } else if (command == "funnel") {
      meta_object_file <- file.path(output_dir, "meta_analysis_object.rds")
      
      if (!file.exists(meta_object_file)) {
        stop("Meta-analysis object not found. Run 'analyze' command first.")
      }
      
      output_file <- file.path(output_dir, "funnel_plot.png")
      title <- if (length(args) > 3) args[4] else "Funnel Plot"
      
      cat("Generating funnel plot...\n")
      generate_funnel_plot_cli(meta_object_file, output_file, title)
      cat("Funnel plot saved to:", output_file, "\n")
      
    } else if (command == "bias") {
      meta_object_file <- file.path(output_dir, "meta_analysis_object.rds")
      
      if (!file.exists(meta_object_file)) {
        stop("Meta-analysis object not found. Run 'analyze' command first.")
      }
      
      cat("Assessing publication bias...\n")
      results <- assess_publication_bias_cli(meta_object_file, output_dir)
      
      cat("\nPublication Bias Results:\n")
      cat("  Egger's test p-value:", format.pval(results$egger_test$p_value), "\n")
      cat("  ", results$egger_test$interpretation, "\n")
      cat("  Begg's test p-value:", format.pval(results$begg_test$p_value), "\n")
      cat("  ", results$begg_test$interpretation, "\n")
      
      if (!is.null(results$trim_fill)) {
        cat("  Trim-and-fill:", results$trim_fill$interpretation, "\n")
      }
      
      cat("\nBias assessment completed\n")
      cat("Results saved to:", file.path(output_dir, "publication_bias_results.json"), "\n")
      
    } else {
      stop(paste("Unknown command:", command))
    }
    
  }, error = function(e) {
    cat("\nError:", e$message, "\n")
    quit(status = 1)
  })
}