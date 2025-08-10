# perform_analysis.R
# Updated to use meta package through adapter

library(jsonlite)

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

# Helper function to normalize field names
normalize_field_names <- function(config) {
  # Normalize from camelCase to snake_case
  if (!is.null(config$effectMeasure) && is.null(config$effect_measure)) {
    config$effect_measure <- config$effectMeasure
  }
  if (!is.null(config$analysisModel) && is.null(config$analysis_model)) {
    config$analysis_model <- config$analysisModel
  }
  if (!is.null(config$studyType) && is.null(config$study_type)) {
    config$study_type <- config$studyType
  }
  config
}

perform_meta_analysis <- function(args) {
  session_path <- args$session_path
  
  # Load processed data
  processed_data_path <- file.path(session_path, "processing", "processed_data.rds")
  if (!file.exists(processed_data_path)) {
    # Try loading from data directory
    data_path <- file.path(session_path, "data", "uploaded_data.rds")
    if (!file.exists(data_path)) {
      stop("Processed data not found. Please upload data first.")
    }
    loaded_data <- readRDS(data_path)
  } else {
    loaded_data <- readRDS(processed_data_path)
  }
  
  # Load session config
  session_config_path <- file.path(session_path, "session.json")
  if (!file.exists(session_config_path)) {
    stop("Session configuration not found.")
  }
  session_config <- fromJSON(session_config_path)
  # Normalize field names (camelCase vs snake_case)
  session_config <- normalize_field_names(session_config)
  
  # Convert data format if needed
  analysis_data <- convert_metafor_to_meta_format(loaded_data, session_config)
  
  # Determine analysis method
  method <- switch(session_config$analysisModel,
    "fixed" = "fixed",
    "random" = "random",
    "auto" = "random"  # Default to random effects
  )
  
  # Get effect measure
  measure <- session_config$effectMeasure
  
  # Perform meta-analysis
  tryCatch({
    # Use the core function from adapter
    meta_result <- perform_meta_analysis_core(analysis_data, method, measure)
    
    # Save the meta result object for later use
    results_dir <- file.path(session_path, "results")
    if (!dir.exists(results_dir)) {
      dir.create(results_dir, recursive = TRUE)
    }
    saveRDS(meta_result, file.path(results_dir, "analysis_results.rds"))
    
    # Also save in processing directory for backward compatibility
    saveRDS(list(model = meta_result), file.path(session_path, "processing", "analysis_results.rds"))
    
    # Extract results based on model type (fixed or random)
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
    
    # Prepare summary for MCP response
    summary_info <- list(
      status = "success",
      overall_effect = as.numeric(pooled_effect),
      confidence_interval = list(
        lower = ci_lower,
        upper = ci_upper
      ),
      p_value = p_value,
      heterogeneity = list(
        i_squared = paste0(round(meta_result$I2, 1), "%"),
        tau_squared = meta_result$tau2,
        q_test = list(
          statistic = meta_result$Q,
          p_value = meta_result$pval.Q
        )
      ),
      study_count = meta_result$k,
      method_used = method,
      effect_measure = measure
    )
    
    # Add publication bias assessment if requested
    if (!is.null(args$publication_bias) && args$publication_bias) {
      bias_results <- assess_publication_bias_core(meta_result)
      summary_info$publication_bias <- bias_results
    }
    
    # Add sensitivity analysis if requested
    if (!is.null(args$sensitivity_analysis) && args$sensitivity_analysis && meta_result$k > 2) {
      # Leave-one-out analysis
      loo <- metainf(meta_result)
      summary_info$sensitivity_analysis <- list(
        leave_one_out = "Completed",
        interpretation = "Leave-one-out analysis performed to assess influence of individual studies"
      )
      # Save leave-one-out results
      saveRDS(loo, file.path(results_dir, "leave_one_out.rds"))
    }
    
    # Add interpretation based on heterogeneity
    i2_value <- meta_result$I2
    if (i2_value < 25) {
      summary_info$heterogeneity$interpretation <- "Low heterogeneity"
    } else if (i2_value < 50) {
      summary_info$heterogeneity$interpretation <- "Moderate heterogeneity"
    } else if (i2_value < 75) {
      summary_info$heterogeneity$interpretation <- "Substantial heterogeneity"
    } else {
      summary_info$heterogeneity$interpretation <- "Considerable heterogeneity"
    }
    
    # Return the summary
    summary_info
    
  }, error = function(e) {
    list(
      status = "error",
      message = paste("Error performing meta-analysis:", e$message),
      details = list(
        data_columns = names(analysis_data),
        n_studies = nrow(analysis_data),
        method = method,
        measure = measure
      )
    )
  })
}